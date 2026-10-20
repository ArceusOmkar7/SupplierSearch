"""Owner-controlled close with gaps and reopen.

Closing freezes the chosen immutable snapshot, stops pending work and fences late results; it
never contacts a supplier and does not start any expiry clock. Reopening is an explicit owner
action that returns the case to `ready`; later work is a new revision/checklist/run and never
alters earlier snapshots.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from verisource.api.errors import reject
from verisource.db.models import (
    AssessmentSnapshot,
    Case,
    CheckTask,
    HumanAction,
    VerificationRun,
    WorkItem,
)
from verisource.domain.commands import append_event

CLOSABLE = {"ready", "active", "assessed"}


def cancel_pending_work(db: Session, case_id: UUID) -> int:
    """Cancel every unfinished run, task, action and job of the case; history is kept."""
    now = datetime.now(UTC)
    runs = list(
        db.scalars(
            select(VerificationRun).where(
                VerificationRun.case_id == case_id,
                VerificationRun.state.in_(("queued", "running")),
            )
        )
    )
    for run in runs:
        run.state = "cancelled"
        run.completed_at = now
    run_ids = [r.id for r in runs]
    if run_ids:
        db.execute(
            update(CheckTask)
            .where(
                CheckTask.run_id.in_(run_ids),
                CheckTask.state.in_(("queued", "running", "waiting_input")),
            )
            .values(state="cancelled", wait_action_id=None)
        )
        db.execute(
            update(HumanAction)
            .where(HumanAction.run_id.in_(run_ids), HumanAction.state == "pending")
            .values(state="cancelled")
        )
    db.execute(
        update(WorkItem)
        .where(WorkItem.case_id == case_id, WorkItem.state.in_(("queued", "retry_wait", "leased")))
        .values(state="cancelled", lease_owner=None, lease_expires_at=None)
    )
    return len(runs)


def close_case(db: Session, case: Case, snapshot_id: UUID, reason: str | None) -> None:
    if case.state == "closed":
        raise reject(409, "already_closed", "This case is already closed.")
    if case.state not in CLOSABLE:
        raise reject(409, "not_closable", "Only a case with a published assessment can be closed.")
    snapshot = db.get(AssessmentSnapshot, snapshot_id)
    if snapshot is None or snapshot.case_id != case.id:
        raise reject(404, "not_found", "This resource is unavailable.")
    cancel_pending_work(db, case.id)
    case.state = "closed"
    case.closed_at = datetime.now(UTC)
    case.latest_snapshot_id = snapshot.id  # The closed result is the snapshot the buyer chose.
    append_event(
        db,
        case.id,
        "case.closed",
        f"case-closed:{case.id}:{case.version}",
        {"snapshot_id": str(snapshot.id), "reason": (reason or "")[:500] or None},
        revision_id=snapshot.revision_id,
    )


def reopen_case(db: Session, case: Case, reason: str | None) -> None:
    if case.state != "closed":
        raise reject(409, "not_closed", "Only a closed case can be reopened.")
    case.state = "ready"
    case.closed_at = None
    append_event(
        db,
        case.id,
        "revision.updated",
        f"case-reopened:{case.id}:{case.version}",
        {"case_state": "ready", "reopened": True, "reason": (reason or "")[:500] or None},
    )
