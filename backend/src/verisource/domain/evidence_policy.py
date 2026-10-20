"""Shared, conservative publication policy (core-v1). Only this module issues verdicts.

Sources, packs and models propose semantic mappings as evidence tags (`supports:<criterion>`
or `refutes:<criterion>`). Nothing is trusted because it is schema-valid: each reference is
checked for case/supplier scope, identity, site, authority, period, freshness, coverage and
independent origin. Ambiguity, staleness, missing dates and conflicts yield `unproven`; a
single qualifying direct refutation of a required criterion yields `contradicted`.
"""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from verisource.db.models import (
    Assessment,
    CheckAttempt,
    Claim,
    EvidenceRecord,
    EvidenceUse,
    IdentityResolution,
    VerificationRun,
)
from verisource.domain.claims import POLICY_VERSION

Verdict = Literal["proven", "unproven", "contradicted"]
Outcome = Literal["satisfied", "refuted", "insufficient"]

# Maximum age of a "current status" observation by criterion evidence class (days).
FRESHNESS_DAYS: dict[str, int] = {
    "official_registry_current": 30,
    "issuer_status": 90,
    "official_order": 365,
    "licence_record": 90,
    "accreditation_record": 365,
}
DEFAULT_FRESHNESS_DAYS = 180


@dataclass(frozen=True)
class CriterionResult:
    criterion_id: str
    outcome: Outcome
    reasoning: str
    supporting: list[UUID] = field(default_factory=list)
    refuting: list[UUID] = field(default_factory=list)
    rejected: list[tuple[UUID, str]] = field(default_factory=list)


@dataclass(frozen=True)
class Decision:
    verdict: Verdict
    reasoning: str
    criterion_results: list[dict[str, Any]]
    evidence_refs: list[UUID]
    attempt_refs: list[UUID]
    gaps: list[str]


def compound(outcomes: list[Verdict]) -> Verdict:
    """Compound claim: all required subclaims proven; any contradicted required -> contradicted."""
    if outcomes and all(o == "proven" for o in outcomes):
        return "proven"
    if any(o == "contradicted" for o in outcomes):
        return "contradicted"
    return "unproven"


def combine(outcomes: list[Outcome]) -> Verdict:
    if outcomes and all(o == "satisfied" for o in outcomes):
        return "proven"
    if any(o == "refuted" for o in outcomes):
        return "contradicted"
    return "unproven"


def _period_instant(period: dict[str, Any]) -> date | None:
    if period.get("kind") == "as_of" and period.get("as_of"):
        try:
            return date.fromisoformat(str(period["as_of"]))
        except ValueError:
            return None
    return None


def admissible(
    claim: Claim,
    criterion: dict[str, Any],
    evidence: EvidenceRecord,
    identity_state: str | None,
    now: datetime,
) -> str | None:
    """Return None when the record may count, else a plain reason it may not."""
    if evidence.case_id != claim.case_id or evidence.supplier_id != claim.supplier_id:
        return "reference does not belong to this case and supplier"
    if identity_state != "confirmed":
        return f"supplier identity is {identity_state or 'unresolved'}, not confirmed"
    constraints = criterion.get("constraints", {})
    if constraints.get("site") and claim.site_id is not None and evidence.site_id != claim.site_id:
        return "evidence is not tied to the claimed site"
    authority = criterion.get("authority") or []
    if authority and evidence.authority_role not in authority:
        return f"{evidence.authority_role} evidence is not an accepted authority here"
    if "coverage:partial" in evidence.assertion_tags:
        return "source coverage is partial (orders or scope not fully read)"
    period = claim.relevant_period or {"kind": "current"}
    instant = _period_instant(period)
    if instant is not None:
        covered = (evidence.issued_at is not None and evidence.issued_at.date() == instant) or (
            evidence.effective_at is not None
            and evidence.expires_at is not None
            and evidence.effective_at.date() <= instant <= evidence.expires_at.date()
        )
        return None if covered else "evidence does not cover the claimed date"
    # Current-period claim: a dated, recent observation from a current-status source.
    if evidence.expires_at is not None and evidence.expires_at < now:
        return "the record's own validity has ended"
    if criterion.get("evidence_class") in FRESHNESS_DAYS:
        if "current_status" not in evidence.assertion_tags:
            return "evidence is an historical export, not a current status check"
        # A current-status page is dated by when it was read, not by the validity it reports.
        stamp = (
            evidence.collected_at
            if "current_status" in evidence.assertion_tags
            else (evidence.issued_at or evidence.collected_at)
        )
        limit = FRESHNESS_DAYS.get(str(criterion.get("evidence_class")), DEFAULT_FRESHNESS_DAYS)
        if now - stamp > timedelta(days=limit):
            return f"evidence is older than the {limit}-day freshness window"
    return None


def evaluate_criterion(
    claim: Claim,
    criterion: dict[str, Any],
    evidence: list[EvidenceRecord],
    identity_states: dict[UUID, str],
    now: datetime,
) -> CriterionResult:
    key = criterion["criterion_id"]
    supports, refutes = f"supports:{key}", f"refutes:{key}"
    supporting: list[EvidenceRecord] = []
    refuting: list[EvidenceRecord] = []
    rejected: list[tuple[UUID, str]] = []
    for item in evidence:
        tags = set(item.assertion_tags)
        if supports not in tags and refutes not in tags:
            continue
        reason = admissible(
            claim, criterion, item, identity_states.get(item.identity_resolution_id), now
        )
        if reason is not None:
            rejected.append((item.id, reason))
        elif refutes in tags:
            refuting.append(item)
        else:
            supporting.append(item)
    if refuting and supporting:
        return CriterionResult(
            key,
            "insufficient",
            "admissible records conflict; both are preserved for review",
            [e.id for e in supporting],
            [e.id for e in refuting],
            rejected,
        )
    if refuting:
        return CriterionResult(
            key,
            "refuted",
            "a qualifying authoritative record directly contradicts this criterion",
            [],
            [e.id for e in refuting],
            rejected,
        )
    if supporting:
        if criterion.get("independent_corroboration"):
            lineages = {e.origin_lineage for e in supporting}
            independent = any(
                not e.self_reported and e.authority_role != "supplier" for e in supporting
            )
            if len(lineages) < 2 or not independent:
                return CriterionResult(
                    key,
                    "insufficient",
                    "needs corroboration from an independent origin; copies and supplier "
                    "statements do not count",
                    [e.id for e in supporting],
                    [],
                    rejected,
                )
        return CriterionResult(
            key,
            "satisfied",
            "admissible evidence satisfies this criterion",
            [e.id for e in supporting],
            [],
            rejected,
        )
    return CriterionResult(
        key,
        "insufficient",
        criterion.get("missing_evidence_condition") or "no admissible evidence",
        [],
        [],
        rejected,
    )


def decide_leaf(
    claim: Claim,
    evidence: list[EvidenceRecord],
    attempts: list[CheckAttempt],
    identity_states: dict[UUID, str],
    now: datetime,
) -> Decision:
    results = [
        evaluate_criterion(claim, c, evidence, identity_states, now)
        for c in claim.proof_criteria_json.get("criteria", [])
    ]
    verdict = combine([r.outcome for r in results])
    gaps: list[str] = []
    for result in results:
        if result.outcome != "satisfied":
            gaps.append(f"{result.criterion_id}: {result.reasoning}")
        gaps.extend(
            f"{result.criterion_id}: record not used — {why}" for _id, why in result.rejected
        )
    mine = [a for a in attempts if claim.id in a.claim_ids]
    if verdict == "unproven" and not any(r.supporting for r in results):
        for attempt in mine:
            if attempt.outcome != "success":
                gaps.append(
                    f"check {attempt.kind} {attempt.outcome}"
                    + (f" ({attempt.reason_code})" if attempt.reason_code else "")
                    + ("" if attempt.request_dispatched else "; no external request was sent")
                )
    used = [i for r in results for i in (*r.supporting, *r.refuting)]
    reasoning = "; ".join(f"{r.criterion_id}: {r.outcome} — {r.reasoning}" for r in results) or (
        "no criteria"
    )
    return Decision(
        verdict,
        reasoning,
        [
            {
                "criterion_id": r.criterion_id,
                "outcome": r.outcome,
                "reasoning": r.reasoning,
                "supporting": [str(i) for i in r.supporting],
                "refuting": [str(i) for i in r.refuting],
                "rejected": [{"evidence_id": str(i), "reason": why} for i, why in r.rejected],
            }
            for r in results
        ],
        list(dict.fromkeys(used)),
        [a.id for a in mine],
        gaps,
    )


def decide_parent(children: list[tuple[Claim, Decision]]) -> Decision:
    verdict = compound([d.verdict for _c, d in children])
    return Decision(
        verdict,
        "; ".join(f"{c.assertion}: {d.verdict}" for c, d in children) or "no subclaims",
        [
            {
                "criterion_id": f"subclaim:{c.id}",
                "label": c.assertion,
                "outcome": {"proven": "satisfied", "contradicted": "refuted"}.get(
                    d.verdict, "insufficient"
                ),
                "reasoning": d.reasoning,
                "supporting": [str(i) for i in d.evidence_refs],
                "refuting": [],
                "rejected": [],
            }
            for c, d in children
        ],
        list(dict.fromkeys(i for _c, d in children for i in d.evidence_refs)),
        list(dict.fromkeys(i for _c, d in children for i in d.attempt_refs)),
        [g for _c, d in children for g in d.gaps],
    )


def _same_decision(previous: Assessment, decision: Decision) -> bool:
    return (
        previous.verdict == decision.verdict
        and previous.reasoning == decision.reasoning
        and previous.criterion_results == decision.criterion_results
        and sorted(previous.evidence_refs) == sorted(str(i) for i in decision.evidence_refs)
        and sorted(previous.attempt_refs) == sorted(str(i) for i in decision.attempt_refs)
        and previous.gaps == decision.gaps
    )


def assess_checklist(
    db: Session,
    run: VerificationRun,
    claims: list[Claim],
    *,
    now: datetime | None = None,
) -> list[Assessment]:
    """Append one assessment per claim, from only this run's retrieved evidence and attempts."""
    now = now or datetime.now(UTC)
    evidence = list(
        db.scalars(
            select(EvidenceRecord).where(
                EvidenceRecord.run_id == run.id, EvidenceRecord.case_id == run.case_id
            )
        )
    )
    attempts = list(
        db.scalars(
            select(CheckAttempt).where(
                CheckAttempt.run_id == run.id, CheckAttempt.case_id == run.case_id
            )
        )
    )
    identity_states = {
        row.id: row.state
        for row in db.scalars(
            select(IdentityResolution).where(IdentityResolution.case_id == run.case_id)
        )
    }
    by_parent: dict[UUID | None, list[Claim]] = {}
    for claim in claims:
        by_parent.setdefault(claim.parent_claim_id, []).append(claim)
    decisions: dict[UUID, Decision] = {}
    for claim in claims:
        if claim.id not in by_parent:  # leaf
            decisions[claim.id] = decide_leaf(claim, evidence, attempts, identity_states, now)
    for claim in claims:
        if claim.id in by_parent:
            decisions[claim.id] = decide_parent(
                [(child, decisions[child.id]) for child in by_parent[claim.id]]
            )
    published: list[Assessment] = []
    for claim in claims:
        decision = decisions[claim.id]
        previous = db.scalar(
            select(Assessment)
            .where(
                Assessment.case_id == run.case_id,
                Assessment.claim_id == claim.id,
                Assessment.run_id == run.id,
            )
            .order_by(Assessment.sequence.desc())
            .limit(1)
        )
        if previous is not None and _same_decision(previous, decision):
            published.append(previous)  # Nothing changed: history is not padded.
            continue
        sequence = (
            int(
                db.scalar(
                    select(func.coalesce(func.max(Assessment.sequence), 0)).where(
                        Assessment.case_id == run.case_id,
                        Assessment.claim_id == claim.id,
                        Assessment.run_id == run.id,
                    )
                )
                or 0
            )
            + 1
        )
        assessment = Assessment(
            case_id=run.case_id,
            run_id=run.id,
            revision_id=run.revision_id,
            checklist_id=run.checklist_id,
            claim_id=claim.id,
            sequence=sequence,
            verdict=decision.verdict,
            reasoning=decision.reasoning,
            criterion_results=decision.criterion_results,
            evidence_refs=[str(i) for i in decision.evidence_refs],
            attempt_refs=[str(i) for i in decision.attempt_refs],
            gaps=decision.gaps,
            policy_version=POLICY_VERSION,
        )
        db.add(assessment)
        db.flush()
        for result in decision.criterion_results:
            if result["criterion_id"].startswith("subclaim:"):
                continue  # Compound parents reference their subclaim assessments, not records.
            for role, key in (("supporting", "supporting"), ("refuting", "refuting")):
                for evidence_id in result[key]:
                    db.add(
                        EvidenceUse(
                            case_id=run.case_id,
                            assessment_id=assessment.id,
                            evidence_id=UUID(evidence_id),
                            criterion_id=result["criterion_id"],
                            role=role,
                            period_fit=str((claim.relevant_period or {}).get("kind", "current")),
                            freshness_check_ref=f"{POLICY_VERSION}:{now.isoformat()}",
                        )
                    )
        published.append(assessment)
    db.flush()
    return published
