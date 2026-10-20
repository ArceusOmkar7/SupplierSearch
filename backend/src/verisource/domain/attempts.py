"""Record actual attempts. An attempt documents what happened; it is never evidence."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from verisource.db.models import CheckAttempt, CheckTask, SourceDefinition, VerificationRun
from verisource.db.models.artifacts import ATTEMPT_OUTCOMES, REASON_CODES

KINDS = ("capability_check", "remote_request", "document_read", "deadline_check")


def record_attempt(
    db: Session,
    *,
    task: CheckTask,
    kind: str,
    target: str,
    requested_at: datetime,
    request_dispatched: bool,
    outcome: str,
    reason_code: str | None,
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
    http_status: int | None = None,
    provider_request_id: str | None = None,
    artifact_refs: list[Any] | None = None,
    retry_of: UUID | None = None,
    operation_key: str | None = None,
) -> CheckAttempt:
    if kind not in KINDS or outcome not in ATTEMPT_OUTCOMES:
        raise ValueError("Unknown attempt kind or outcome")
    if reason_code is not None and reason_code not in REASON_CODES:
        raise ValueError("Unknown attempt reason")
    if request_dispatched and kind != "remote_request":
        raise ValueError("Only a remote request can claim a network dispatch")
    if outcome == "skipped" and request_dispatched:
        raise ValueError("A skipped check was not dispatched")
    if outcome in {"blocked", "skipped", "invalid_input"} and reason_code is None:
        raise ValueError("This outcome must state a reason")
    if http_status is not None and not request_dispatched:
        raise ValueError("An HTTP status requires an actual dispatch")
    if outcome not in {"success", "no_record", "uncertain_outcome"} and artifact_refs:
        raise ValueError("A no-content attempt cannot reference retrieved artifacts")
    run = db.get(VerificationRun, task.run_id)
    assert run is not None and run.case_id == task.case_id
    version = db.scalar(
        select(func.max(SourceDefinition.version)).where(SourceDefinition.id == task.source_id)
    )
    attempt = CheckAttempt(
        id=uuid4(),
        case_id=task.case_id,
        run_id=task.run_id,
        task_id=task.id,
        revision_id=run.revision_id,
        supplier_id=task.supplier_id,
        claim_ids=list(task.claim_ids),
        source_version=f"{task.source_id}@{version or 1}",
        kind=kind,
        target=target,
        requested_at=requested_at,
        started_at=started_at,
        finished_at=finished_at or max(datetime.now(UTC), requested_at),
        request_dispatched=request_dispatched,
        outcome=outcome,
        reason_code=reason_code,
        http_status=http_status,
        provider_request_id=provider_request_id,
        artifact_refs=list(artifact_refs or []),
        retry_of=retry_of,
        operation_key=operation_key or f"attempt:{task.id}:{uuid4()}",
    )
    db.add(attempt)
    db.flush()
    return attempt
