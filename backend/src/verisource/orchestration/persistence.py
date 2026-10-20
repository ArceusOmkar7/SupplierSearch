"""Persist one check's results atomically in the work-acknowledgement transaction.

Attempts, artifacts, identity resolutions, evidence and the task state are committed together
and idempotently (stable operation keys), so a redelivered job never duplicates evidence.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from verisource.country_packs.contracts import CheckResult, IdentityClaim, Observation
from verisource.db.models import (
    CheckAttempt,
    CheckTask,
    DocumentArtifact,
    EvidenceRecord,
    Extraction,
    HumanAction,
    IdentityResolution,
    VerificationRun,
)
from verisource.domain.attempts import record_attempt
from verisource.domain.commands import append_event


@dataclass(frozen=True)
class PendingArtifact:
    """A file already written to private storage; the row is created with the result."""

    storage_key: str
    sha256: str
    byte_count: int
    media_type: str
    origin: str = "source_fetch"
    page_count: int | None = None
    source_url: str | None = None
    state: str = "ready"
    state_reason: str | None = None
    attempt_index: int | None = None
    supplier_id: UUID | None = None


@dataclass(frozen=True)
class PendingExtraction:
    artifact_sha256: str
    page_refs: list[int]
    method: str
    fields: dict[str, Any]
    missing_fields: list[str]
    uncertainties: list[str]
    model_id: str | None
    schema_version: str
    content_hash: str


@dataclass
class TaskOutcome:
    result: CheckResult
    artifacts: list[PendingArtifact] = field(default_factory=list)
    extractions: list[PendingExtraction] = field(default_factory=list)
    final_state: str = "succeeded"  # succeeded | no_evidence | failed | waiting_input


def _resolution(
    db: Session, task: CheckTask, revision_id: UUID, claim: IdentityClaim | None, fallback: str
) -> IdentityResolution:
    ref = claim.candidate_ref if claim else fallback
    existing = db.scalar(
        select(IdentityResolution).where(
            IdentityResolution.case_id == task.case_id,
            IdentityResolution.supplier_id == task.supplier_id,
            IdentityResolution.revision_id == revision_id,
            IdentityResolution.candidate_record_ref == ref,
        )
    )
    if existing is not None:
        return existing
    state = claim.state if claim else "proposed"
    row = IdentityResolution(
        case_id=task.case_id,
        revision_id=revision_id,
        supplier_id=task.supplier_id,
        candidate_record_ref=ref,
        identifier_matches=list(claim.matches) if claim else [],
        discrepancies=list(claim.discrepancies) if claim else [],
        proposed_score=claim.score if claim else None,
        state=state,
        resolution_basis=claim.basis if claim else "buyer_supplied_identifier",
        resolved_by=None,
        resolved_at=datetime.now(UTC) if state == "confirmed" else None,
    )
    db.add(row)
    db.flush()
    return row


def persist_observation(
    db: Session,
    task: CheckTask,
    run: VerificationRun,
    observation: Observation,
    artifact_ids: dict[str, UUID],
    *,
    site_id: UUID | None = None,
) -> EvidenceRecord:
    resolution = _resolution(
        db, task, run.revision_id, observation.identity, observation.source_ref
    )
    existing = db.scalar(
        select(EvidenceRecord).where(
            EvidenceRecord.case_id == task.case_id,
            EvidenceRecord.run_id == run.id,
            EvidenceRecord.supplier_id == task.supplier_id,
            EvidenceRecord.content_hash == observation.content_hash,
            EvidenceRecord.locator == observation.locator,
        )
    )
    if existing is not None:
        return existing
    record = EvidenceRecord(
        id=uuid4(),
        case_id=task.case_id,
        run_id=run.id,
        supplier_id=task.supplier_id,
        site_id=site_id,
        assertion_tags=list(observation.assertion_tags),
        source_version=f"{observation.source_id}@{observation.source_version}",
        source_ref=observation.source_ref,
        observation=observation.observation,
        locator=observation.locator,
        collected_at=observation.collected_at,
        issued_at=observation.issued_at,
        expires_at=observation.expires_at,
        effective_at=observation.effective_at,
        origin_lineage=observation.origin_lineage,
        self_reported=observation.self_reported,
        authority_role=observation.authority_role,
        identity_resolution_id=resolution.id,
        artifact_id=observation.artifact_id or artifact_ids.get(observation.source_ref),
        content_hash=observation.content_hash,
        replay=observation.replay,
    )
    db.add(record)
    db.flush()
    return record


def persist_outcome(db: Session, task: CheckTask, outcome: TaskOutcome) -> list[UUID]:
    """Write everything for one task. Returns ids of newly created human actions."""
    run = db.get(VerificationRun, task.run_id)
    assert run is not None
    result = outcome.result
    attempt_ids: list[UUID] = []
    for index, spec in enumerate(result.attempts):
        stored = record_attempt(
            db,
            task=task,
            kind=spec.kind,
            target=spec.target,
            requested_at=spec.requested_at,
            started_at=spec.started_at,
            finished_at=spec.finished_at,
            request_dispatched=spec.request_dispatched,
            outcome=spec.outcome,
            reason_code=spec.reason_code,
            http_status=spec.http_status,
            retry_of=attempt_ids[spec.retry_of] if spec.retry_of is not None else None,
            operation_key=f"attempt:{task.id}:{index}",
        )
        attempt_ids.append(stored.id)
    artifact_ids: dict[str, UUID] = {}
    by_hash: dict[str, UUID] = {}
    for pending in outcome.artifacts:
        existing = db.scalar(
            select(DocumentArtifact).where(
                DocumentArtifact.case_id == task.case_id,
                DocumentArtifact.supplier_id == (pending.supplier_id or task.supplier_id),
                DocumentArtifact.sha256 == pending.sha256,
            )
        )
        if existing is None:
            existing = DocumentArtifact(
                case_id=task.case_id,
                revision_id=run.revision_id,
                supplier_id=pending.supplier_id or task.supplier_id,
                origin=pending.origin,
                storage_key=pending.storage_key,
                sha256=pending.sha256,
                media_type=pending.media_type,
                byte_count=pending.byte_count,
                page_count=pending.page_count,
                collected_at=datetime.now(UTC),
                source_url=pending.source_url,
                source_attempt_id=attempt_ids[pending.attempt_index]
                if pending.attempt_index is not None
                else None,
                state=pending.state,
                state_reason=pending.state_reason,
            )
            db.add(existing)
            db.flush()
        by_hash[pending.sha256] = existing.id
        if pending.source_url:
            artifact_ids[pending.source_url] = existing.id
    for observation in result.observations:
        persist_observation(db, task, run, observation, artifact_ids, site_id=observation.site_id)
    for extraction in outcome.extractions:
        artifact_id = by_hash.get(extraction.artifact_sha256)
        if artifact_id is None:
            continue
        db.add(
            Extraction(
                case_id=task.case_id,
                artifact_id=artifact_id,
                page_refs=extraction.page_refs,
                method=extraction.method,
                fields=extraction.fields,
                missing_fields=extraction.missing_fields,
                uncertainties=extraction.uncertainties,
                model_id=extraction.model_id,
                schema_version=extraction.schema_version,
                content_hash=extraction.content_hash,
            )
        )
    db.flush()
    task.state = outcome.final_state
    created: list[UUID] = []
    if result.dependent_action is not None:
        if result.dependent_action.affects == "dependents":
            waiting = list(
                db.scalars(
                    select(CheckTask).where(
                        CheckTask.run_id == run.id,
                        CheckTask.state == "queued",
                        CheckTask.dependency_ids.contains([task.id]),
                    )
                )
            )
        else:
            waiting = [task]
        action = HumanAction(
            case_id=task.case_id,
            revision_id=run.revision_id,
            run_id=run.id,
            affected_task_ids=[t.id for t in waiting],
            type=result.dependent_action.type,
            requested_document_ref=result.dependent_action.requested_document_ref,
            state="pending",
        )
        db.add(action)
        db.flush()
        for waiting_task in waiting:
            waiting_task.wait_action_id = action.id
            waiting_task.state = "waiting_input"
        created.append(action.id)
        append_event(
            db,
            task.case_id,
            "action.required",
            f"action-required:{action.id}",
            {"action_id": str(action.id), "type": action.type},
            revision_id=run.revision_id,
            run_id=run.id,
        )
    append_event(
        db,
        task.case_id,
        "check.completed",
        f"task-complete:{task.id}:{task.state}",
        {"task_id": str(task.id), "check_type": task.check_type, "state": task.state},
        revision_id=run.revision_id,
        run_id=run.id,
    )
    return created


def attempts_for(db: Session, task_id: UUID) -> list[CheckAttempt]:
    return list(db.scalars(select(CheckAttempt).where(CheckAttempt.task_id == task_id)))
