"""PostgreSQL leases, fencing and atomic result/ack transactions with per-call sessions."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import Engine, and_, or_, select
from sqlalchemy.orm import Session

from verisource.db.models import Case, WorkItem
from verisource.domain.commands import append_event


@dataclass(frozen=True)
class Lease:
    work_id: UUID
    case_id: UUID
    owner: str
    fence: int
    generation: int
    kind: str
    references: dict[str, Any]


def enqueue(
    db: Session,
    case: Case,
    *,
    kind: str,
    operation_key: str,
    references: dict[str, Any],
    run_id: UUID | None = None,
    task_id: UUID | None = None,
    due_at: datetime | None = None,
) -> WorkItem:
    db.scalar(select(Case).where(Case.id == case.id).with_for_update())
    if case.state in {"closed", "deleting"}:
        raise ValueError("Case cannot accept work")
    existing = db.scalar(
        select(WorkItem).where(WorkItem.case_id == case.id, WorkItem.operation_key == operation_key)
    )
    if existing is not None:
        return existing
    work = WorkItem(
        case_id=case.id,
        run_id=run_id,
        task_id=task_id,
        kind=kind,
        operation_key=operation_key,
        fence=1,
        due_at=due_at or datetime.now(UTC),
        payload_refs={**references, "write_generation": case.write_generation},
    )
    db.add(work)
    db.flush()
    return work


def claim(engine: Engine, owner: str) -> Lease | None:
    now = datetime.now(UTC)
    with Session(engine) as db, db.begin():
        candidate = db.scalar(
            select(WorkItem)
            .join(Case)
            .where(
                Case.state.not_in(("closed", "deleting")),
                or_(
                    and_(WorkItem.state.in_(("queued", "retry_wait")), WorkItem.due_at <= now),
                    and_(WorkItem.state == "leased", WorkItem.lease_expires_at <= now),
                ),
            )
            .order_by(WorkItem.due_at, WorkItem.id)
            .with_for_update(of=WorkItem, skip_locked=True)
            .limit(1)
        )
        if candidate is None:
            return None
        case = db.get(Case, candidate.case_id)
        if case is None or case.write_generation != int(candidate.payload_refs["write_generation"]):
            candidate.state = "cancelled"
            candidate.lease_owner = None
            candidate.lease_expires_at = None
            return None
        candidate.fence += 1
        candidate.attempts += 1
        candidate.state = "leased"
        candidate.lease_owner = owner
        candidate.heartbeat_at = now
        candidate.lease_expires_at = now + timedelta(seconds=60)
        return Lease(
            candidate.id,
            candidate.case_id,
            owner,
            candidate.fence,
            int(candidate.payload_refs["write_generation"]),
            candidate.kind,
            dict(candidate.payload_refs),
        )


def _current(db: Session, lease: Lease) -> tuple[Case, WorkItem] | None:
    case = db.scalar(select(Case).where(Case.id == lease.case_id).with_for_update())
    if (
        case is None
        or case.state in {"closed", "deleting"}
        or case.write_generation != lease.generation
    ):
        return None
    work = db.scalar(select(WorkItem).where(WorkItem.id == lease.work_id).with_for_update())
    if (
        work is None
        or work.state != "leased"
        or work.lease_owner != lease.owner
        or work.fence != lease.fence
        or work.lease_expires_at is None
        or work.lease_expires_at <= datetime.now(UTC)
    ):
        return None
    return case, work


def heartbeat(engine: Engine, lease: Lease) -> bool:
    with Session(engine) as db, db.begin():
        current = _current(db, lease)
        if current is None:
            return False
        current[1].heartbeat_at = datetime.now(UTC)
        current[1].lease_expires_at = current[1].heartbeat_at + timedelta(seconds=60)
        return True


def complete(engine: Engine, lease: Lease, apply: Callable[[Session], None]) -> bool:
    with Session(engine) as db, db.begin():
        current = _current(db, lease)
        if current is None:
            return False
        apply(db)
        db.flush()  # Domain result must succeed before work acknowledgement.
        current[1].state = "succeeded"
        current[1].lease_owner = None
        current[1].lease_expires_at = None
        return True


def fail(
    engine: Engine, lease: Lease, *, retryable: bool, error_type: str = "handler_error"
) -> None:
    with Session(engine) as db, db.begin():
        current = _current(db, lease)
        if current is None:
            return
        case, work = current
        retrying = retryable and work.attempts < 3
        work.state = "retry_wait" if retrying else "failed"
        work.due_at = datetime.now(UTC) + timedelta(seconds=30)
        work.lease_owner = None
        work.lease_expires_at = None
        append_event(
            db,
            case.id,
            "work.retrying" if retrying else "work.failed",
            f"work:{work.id}:{lease.fence}:failure",
            {"work_id": str(work.id), "reason": error_type, "retrying": retrying},
        )
        if not retrying and work.task_id is not None:
            _fail_task(db, case, work, error_type)


def _fail_task(db: Session, case: Case, work: WorkItem, error_type: str) -> None:
    """A task whose job cannot complete becomes `failed` so the run still finishes honestly."""
    from verisource.db.models import CheckTask, VerificationRun
    from verisource.domain.attempts import record_attempt
    from verisource.orchestration.graph import advance_run

    task = db.get(CheckTask, work.task_id)
    run = db.get(VerificationRun, work.run_id) if work.run_id else None
    if task is None or run is None or task.state not in {"queued", "running"}:
        return
    now = datetime.now(UTC)
    record_attempt(
        db,
        task=task,
        kind="capability_check",
        target=f"internal:{error_type}",
        requested_at=now,
        request_dispatched=False,
        outcome="transient_error",
        reason_code=None,
        operation_key=f"attempt:{task.id}:internal-failure",
    )
    task.state = "failed"
    advance_run(db, case, run)
