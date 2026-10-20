"""Which tasks may be queued now: dependencies resolved and the active five-supplier batch."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from verisource.db.models import Case, CheckTask, RequirementRevision, VerificationRun
from verisource.orchestration.jobs import enqueue
from verisource.sources.quotas import LIMITS

RESOLVED = {"succeeded", "no_evidence", "failed", "cancelled"}


def batch_of(revision: RequirementRevision) -> dict[UUID, int]:
    size = LIMITS.active_batch_suppliers
    return {
        UUID(entry["supplier_id"]): index // size
        for index, entry in enumerate(revision.supplier_set_json)
    }


def queue_ready(db: Session, case: Case, run: VerificationRun) -> int:
    """Enqueue ready tasks of the lowest batch with unfinished work; larger lists wait.

    Enqueueing is idempotent per task, so repeated calls never duplicate work.
    """
    revision = db.get(RequirementRevision, run.revision_id)
    assert revision is not None
    batches = batch_of(revision)
    tasks = list(db.scalars(select(CheckTask).where(CheckTask.run_id == run.id)))
    state = {task.id: task.state for task in tasks}
    active = [batches[t.supplier_id] for t in tasks if t.state in {"queued", "running"}]
    if not active:
        return 0
    allowed = min(active)
    queued = 0
    for task in tasks:
        if (
            task.state == "queued"
            and batches[task.supplier_id] <= allowed
            and all(state.get(dep) in RESOLVED for dep in task.dependency_ids)
        ):
            enqueue(
                db,
                case,
                kind="check_task",
                operation_key=f"task:{task.id}",
                references={"task_id": str(task.id), "run_id": str(run.id)},
                run_id=run.id,
                task_id=task.id,
            )
            queued += 1
    return queued
