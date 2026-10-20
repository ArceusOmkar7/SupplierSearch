"""Transactional assembly of immutable assessment snapshots.

A snapshot freezes the revision, checklist, run, policy, event cutoff, the latest assessment
of every claim and the derived lists. Pending or skipped work is stated truthfully. Later
arrivals create later snapshots; an identical state never creates a duplicate.
"""

from collections import Counter
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from verisource.country_packs.india.warnings import detect
from verisource.db.models import (
    Assessment,
    AssessmentSnapshot,
    Case,
    CaseEvent,
    CheckAttempt,
    CheckTask,
    Claim,
    EvidenceRecord,
    HumanAction,
    IdentityResolution,
    RequirementRevision,
    VerificationRun,
)
from verisource.domain.claims import POLICY_VERSION
from verisource.domain.commands import append_event
from verisource.domain.intake import json_hash
from verisource.domain.shortlist import classify

PROCESSING = {
    "queued": "Waiting to start",
    "running": "Checking",
    "waiting_input": "Waiting for you",
}


def _latest_assessments(db: Session, run: VerificationRun) -> dict[UUID, Assessment]:
    rows = db.scalars(
        select(Assessment)
        .where(Assessment.run_id == run.id, Assessment.case_id == run.case_id)
        .order_by(Assessment.claim_id, Assessment.sequence)
    )
    latest: dict[UUID, Assessment] = {}
    for row in rows:
        latest[row.claim_id] = row
    return latest


def _considered(
    assessment: Assessment | None, evidence: dict[UUID, EvidenceRecord]
) -> list[dict[str, Any]]:
    """Records the policy looked at but could not use, with the plain reason for each."""
    if assessment is None:
        return []
    rows: list[dict[str, Any]] = []
    for result in assessment.criterion_results:
        for rejected in result.get("rejected", []):
            item = evidence.get(UUID(rejected["evidence_id"]))
            if item is None:
                continue
            rows.append(
                {
                    "evidence_id": rejected["evidence_id"],
                    "reason": rejected["reason"],
                    "criterion_id": result["criterion_id"],
                    "observation": item.observation,
                    "source_ref": item.source_ref,
                    "authority_role": item.authority_role,
                    "issued_at": item.issued_at.isoformat() if item.issued_at else None,
                }
            )
    return rows


def _evidence_view(item: EvidenceRecord, resolution: IdentityResolution | None) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "source_ref": item.source_ref,
        "locator": item.locator,
        "observation": item.observation,
        "authority_role": item.authority_role,
        "self_reported": item.self_reported,
        "origin_lineage": item.origin_lineage,
        "collected_at": item.collected_at.isoformat(),
        "issued_at": item.issued_at.isoformat() if item.issued_at else None,
        "expires_at": item.expires_at.isoformat() if item.expires_at else None,
        "replay": item.replay,
        "content_hash": item.content_hash,
        "identity_state": resolution.state if resolution else None,
        "identity_basis": resolution.resolution_basis if resolution else None,
    }


def build_content(
    db: Session, case: Case, run: VerificationRun, trigger: str
) -> tuple[dict[str, Any], list[Assessment], int]:
    revision = db.get(RequirementRevision, run.revision_id)
    assert revision is not None
    claims = list(
        db.scalars(
            select(Claim)
            .where(Claim.case_id == run.case_id, Claim.checklist_id == run.checklist_id)
            .order_by(Claim.type, Claim.assertion, Claim.id)
        )
    )
    latest = _latest_assessments(db, run)
    evidence = {
        e.id: e
        for e in db.scalars(
            select(EvidenceRecord)
            .where(EvidenceRecord.run_id == run.id)
            .order_by(EvidenceRecord.id)
        )
    }
    resolutions = {
        r.id: r
        for r in db.scalars(
            select(IdentityResolution).where(IdentityResolution.case_id == run.case_id)
        )
    }
    attempts = {
        a.id: a
        for a in db.scalars(
            select(CheckAttempt).where(CheckAttempt.run_id == run.id).order_by(CheckAttempt.id)
        )
    }
    tasks = list(
        db.scalars(select(CheckTask).where(CheckTask.run_id == run.id).order_by(CheckTask.id))
    )
    actions = list(
        db.scalars(
            select(HumanAction)
            .where(HumanAction.run_id == run.id, HumanAction.state == "pending")
            .order_by(HumanAction.id)
        )
    )
    verdicts = {claim_id: a.verdict for claim_id, a in latest.items()}
    supplier_ids = [UUID(s["supplier_id"]) for s in revision.supplier_set_json]
    outcomes = {o.supplier_id: o for o in classify(claims, verdicts, supplier_ids)}
    task_counts: dict[UUID, Counter[str]] = {}
    for task in tasks:
        task_counts.setdefault(task.supplier_id, Counter())[task.state] += 1
    discrepancies: dict[UUID, list[str]] = {}
    for resolution in resolutions.values():
        if resolution.state in {"proposed", "confirmed", "ambiguous"}:
            notes = [d for d in resolution.discrepancies if "addresses differ" in d]
            if notes:
                discrepancies.setdefault(resolution.supplier_id, []).extend(notes)
    indicators = detect(
        list(evidence.values()),
        {
            UUID(s["supplier_id"]): [(s.get("address_role") or "unknown", s["address"])]
            for s in revision.supplier_set_json
            if s.get("address")
        },
        discrepancies,
    )

    suppliers: list[dict[str, Any]] = []
    for entry in revision.supplier_set_json:
        supplier_id = UUID(entry["supplier_id"])
        counts = task_counts.get(supplier_id, Counter())
        pending = [s for s in ("waiting_input", "running", "queued") if counts.get(s)]
        outcome = outcomes[supplier_id]
        claim_views = []
        for claim in sorted(
            (c for c in claims if c.supplier_id == supplier_id),
            key=lambda c: (c.parent_claim_id is not None, str(c.id)),
        ):
            assessment = latest.get(claim.id)
            claim_views.append(
                {
                    "claim_id": str(claim.id),
                    "parent_claim_id": str(claim.parent_claim_id)
                    if claim.parent_claim_id
                    else None,
                    "type": claim.type,
                    "assertion": claim.assertion,
                    "required": claim.required_for_shortlist,
                    "relevant_period": claim.relevant_period,
                    "verdict": assessment.verdict if assessment else None,
                    "assessment_id": str(assessment.id) if assessment else None,
                    "reasoning": assessment.reasoning if assessment else None,
                    "criterion_results": assessment.criterion_results if assessment else [],
                    "gaps": assessment.gaps if assessment else [],
                    "considered": _considered(assessment, evidence),
                    "evidence": [
                        _evidence_view(
                            evidence[UUID(i)],
                            resolutions.get(evidence[UUID(i)].identity_resolution_id),
                        )
                        for i in (assessment.evidence_refs if assessment else [])
                        if UUID(i) in evidence
                    ],
                    "attempts": [
                        {
                            "id": str(a.id),
                            "kind": a.kind,
                            "target": a.target,
                            "outcome": a.outcome,
                            "reason_code": a.reason_code,
                            "request_dispatched": a.request_dispatched,
                            "http_status": a.http_status,
                        }
                        for a in (
                            attempts[UUID(i)]
                            for i in (assessment.attempt_refs if assessment else [])
                            if UUID(i) in attempts
                        )
                    ],
                }
            )
        suppliers.append(
            {
                "supplier_id": str(supplier_id),
                "display_name": entry["display_name"],
                "processing_state": "complete" if not pending else pending[0],
                "pending_states": pending,
                "status": outcome.status,
                "reasons": outcome.reasons,
                "claims": claim_views,
                "indicators": [
                    {
                        "family": i.family,
                        "message": i.message,
                        "evidence_ids": [str(x) for x in i.evidence_ids],
                        "validated": i.validated,
                    }
                    for i in indicators
                    if i.supplier_id == supplier_id
                ],
            }
        )
    outcome_counts = Counter(o.status for o in outcomes.values())
    attempt_counts = Counter(f"{a.outcome}" for a in attempts.values())
    event_cutoff = int(
        db.scalar(
            select(func.coalesce(func.max(CaseEvent.sequence), 0)).where(
                CaseEvent.case_id == case.id
            )
        )
        or 0
    )
    content: dict[str, Any] = {
        "schema_version": 1,
        "policy_version": POLICY_VERSION,
        "trigger": trigger,
        "run": {
            "id": str(run.id),
            "state": run.state,
            "mode": run.mode,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "initial_deadline": run.initial_deadline.isoformat(),
            "country_pack_version": run.country_pack_version,
        },
        "revision": {
            "id": str(revision.id),
            "sequence": revision.sequence,
            "requirements": revision.requirements_json,
            "location": revision.location_json,
        },
        "checklist_id": str(run.checklist_id),
        "suppliers": suppliers,
        "pending_actions": [
            {
                "id": str(a.id),
                "type": a.type,
                "affected_task_ids": [str(t) for t in a.affected_task_ids],
            }
            for a in actions
        ],
        "coverage": {
            "tasks": dict(Counter(t.state for t in tasks)),
            "attempt_outcomes": dict(attempt_counts),
            "requests_sent": sum(1 for a in attempts.values() if a.request_dispatched),
            "requests_not_sent": sum(1 for a in attempts.values() if not a.request_dispatched),
            "replay_evidence": sum(1 for e in evidence.values() if e.replay),
            "evaluated_claims": len(latest),
            "total_claims": len(claims),
        },
        "lists": {
            "qualified": [str(s) for s, o in outcomes.items() if o.status == "qualified"],
            "follow_up": [str(s) for s, o in outcomes.items() if o.status == "follow_up"],
            "excluded": {str(s): o.reasons for s, o in outcomes.items() if o.status == "excluded"},
            "counts": dict(outcome_counts),
        },
    }
    return content, list(latest.values()), event_cutoff


def publish_snapshot(
    db: Session, case: Case, run: VerificationRun, trigger: str
) -> AssessmentSnapshot | None:
    """Create the next snapshot, or return None when nothing was assessed or nothing changed."""
    if case.state in {"closed", "deleting"} or case.write_generation != run.generation:
        return None
    content, assessments, cutoff = build_content(db, case, run, trigger)
    if not assessments:
        return None
    stable = {k: v for k, v in content.items() if k != "trigger"}
    digest = json_hash(stable)
    existing = db.scalar(
        select(AssessmentSnapshot).where(
            AssessmentSnapshot.case_id == case.id,
            AssessmentSnapshot.run_id == run.id,
            AssessmentSnapshot.content_hash == digest,
        )
    )
    if existing is not None:
        return existing
    sequence = (
        int(
            db.scalar(
                select(func.coalesce(func.max(AssessmentSnapshot.sequence), 0)).where(
                    AssessmentSnapshot.case_id == case.id, AssessmentSnapshot.run_id == run.id
                )
            )
            or 0
        )
        + 1
    )
    lists = content["lists"]
    snapshot = AssessmentSnapshot(
        case_id=case.id,
        run_id=run.id,
        revision_id=run.revision_id,
        checklist_id=run.checklist_id,
        sequence=sequence,
        trigger=trigger if sequence > 1 or trigger != "updated" else "initial",
        event_cutoff=cutoff,
        assessment_ids=[str(a.id) for a in assessments],
        supplier_processing_states={
            s["supplier_id"]: s["processing_state"] for s in content["suppliers"]
        },
        pending_action_refs=[a["id"] for a in content["pending_actions"]],
        coverage_summary=content["coverage"],
        qualified_ids=lists["qualified"],
        follow_up_ids=lists["follow_up"],
        excluded_reasons=lists["excluded"],
        content_json=content,
        content_hash=digest,
    )
    db.add(snapshot)
    db.flush()
    if run.revision_id == case.active_revision_id:  # Late old-revision work stays historical.
        case.latest_snapshot_id = snapshot.id
    append_event(
        db,
        case.id,
        "snapshot.ready",
        f"snapshot:{snapshot.id}",
        {"snapshot_id": str(snapshot.id), "sequence": sequence, "trigger": snapshot.trigger},
        revision_id=run.revision_id,
        run_id=run.id,
    )
    return snapshot
