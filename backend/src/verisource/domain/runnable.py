"""Which check tasks may run now; a waiting task blocks only its own dependents."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from verisource.db.models import CheckTask

RESOLVED = {"succeeded", "no_evidence", "failed", "cancelled"}


def runnable_tasks(db: Session, run_id: UUID) -> list[CheckTask]:
    tasks = list(db.scalars(select(CheckTask).where(CheckTask.run_id == run_id)))
    state = {task.id: task.state for task in tasks}
    return [
        task
        for task in tasks
        if task.state == "queued" and all(state.get(dep) in RESOLVED for dep in task.dependency_ids)
    ]
