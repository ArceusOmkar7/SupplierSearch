"""Confirmed-run orchestration: parallel independent tasks, durable results, run completion.

Each task executes inside a small LangGraph graph whose synchronous Postgres checkpoint keeps
the external result, so a worker that dies before acknowledging resumes from the stored result
instead of repeating network reads. Canonical rows stay authoritative: a redelivered job first
checks the task's persisted state and never writes twice.
"""

import threading
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, TypedDict
from uuid import UUID

from langgraph.graph import END, START, StateGraph
from pydantic import TypeAdapter
from sqlalchemy import Engine, select, update
from sqlalchemy.orm import Session

from verisource.config import Settings
from verisource.db.checkpoints import checkpointer
from verisource.db.models import (
    Case,
    ChecklistVersion,
    CheckTask,
    Claim,
    GraphCheckpointReference,
    VerificationRun,
)
from verisource.domain.commands import append_event
from verisource.domain.evidence_policy import assess_checklist
from verisource.domain.snapshots import publish_snapshot
from verisource.orchestration.assessment_publication import publish_ready_suppliers
from verisource.orchestration.executors import Executor, TaskSpec, load_spec
from verisource.orchestration.jobs import Lease
from verisource.orchestration.persistence import TaskOutcome, persist_outcome
from verisource.orchestration.scheduling import queue_ready

Applier = Callable[[Session], None]
OUTCOME_ADAPTER: TypeAdapter[TaskOutcome] = TypeAdapter(TaskOutcome)


class GraphState(TypedDict, total=False):
    task_id: str
    outcome: dict[str, Any]


def thread_id(spec: TaskSpec) -> str:
    return f"{spec.case_id}:{spec.revision_id}:{spec.run_id}:{spec.task_id}"


def run_task_graph(
    settings: Settings, executor: Executor, spec: TaskSpec
) -> tuple[TaskOutcome, str | None]:
    """Execute (or resume) the task graph; returns the outcome and its checkpoint id."""

    def execute(state: GraphState) -> GraphState:
        outcome = executor.execute(spec)
        return {"outcome": OUTCOME_ADAPTER.dump_python(outcome, mode="json")}

    builder = StateGraph(GraphState)
    builder.add_node("execute", execute)
    builder.add_edge(START, "execute")
    builder.add_edge("execute", END)
    with checkpointer(settings) as saver:
        graph = builder.compile(checkpointer=saver)
        config: Any = {"configurable": {"thread_id": thread_id(spec)}}
        snapshot = graph.get_state(config)
        stored = snapshot.values.get("outcome") if snapshot and snapshot.values else None
        if stored is None:
            graph.invoke({"task_id": str(spec.task_id)}, config)
            snapshot = graph.get_state(config)
            stored = snapshot.values["outcome"]
        checkpoint_id = (snapshot.config or {}).get("configurable", {}).get("checkpoint_id")
    return OUTCOME_ADAPTER.validate_python(stored), checkpoint_id


# ---- run lifecycle ----------------------------------------------------------------------


def mark_started(db: Session, run: VerificationRun, checklist_id: UUID) -> None:
    if run.state == "queued":
        run.state = "running"
        run.started_at = datetime.now(UTC)
        db.execute(
            update(Claim)
            .where(Claim.case_id == run.case_id, Claim.checklist_id == checklist_id)
            .values(processing_state="checking")
        )


def advance_run(db: Session, case: Case, run: VerificationRun) -> None:
    """Queue tasks whose dependencies resolved; complete the run when nothing is pending."""
    if run.state not in {"queued", "running"}:
        return
    queue_ready(db, case, run)
    tasks = list(db.scalars(select(CheckTask).where(CheckTask.run_id == run.id)))
    if any(t.state in {"queued", "running", "waiting_input"} for t in tasks):
        publish_ready_suppliers(db, case, run)  # Finished suppliers are not held by waiting ones.
        return
    finalize_run(db, case, run, tasks)


def finalize_run(
    db: Session, case: Case, run: VerificationRun, tasks: list[CheckTask] | None = None
) -> None:
    tasks = tasks or list(db.scalars(select(CheckTask).where(CheckTask.run_id == run.id)))
    claims = list(
        db.scalars(
            select(Claim).where(
                Claim.case_id == run.case_id, Claim.checklist_id == run.checklist_id
            )
        )
    )
    assess_checklist(db, run, claims)
    gaps = any(t.state != "succeeded" for t in tasks)
    run.state = "completed_with_gaps" if gaps else "completed"
    run.completed_at = datetime.now(UTC)
    publish_snapshot(db, case, run, "completed")
    db.execute(
        update(Claim)
        .where(Claim.case_id == run.case_id, Claim.checklist_id == run.checklist_id)
        .values(processing_state="evaluated")
    )
    if case.state == "active":
        case.state = "assessed"
    append_event(
        db,
        case.id,
        "run.progress",
        f"run-complete:{run.id}",
        {"run_id": str(run.id), "state": run.state},
        revision_id=run.revision_id,
        run_id=run.id,
    )


# ---- worker handlers --------------------------------------------------------------------


def _live(
    db: Session, lease: Lease, task_id: UUID
) -> tuple[Case, VerificationRun, CheckTask] | None:
    case = db.get(Case, lease.case_id)
    task = db.scalar(select(CheckTask).where(CheckTask.id == task_id).with_for_update())
    run = db.get(VerificationRun, task.run_id) if task else None
    if (
        case is None
        or task is None
        or run is None
        or case.write_generation != run.generation
        or run.state not in {"queued", "running"}
    ):
        return None
    return case, run, task


def make_handlers(
    settings: Settings, engine: Engine, executor: Executor
) -> dict[str, Callable[[Lease, threading.Event], Applier]]:
    def check_task(lease: Lease, lost: threading.Event) -> Applier:
        task_id = UUID(str(lease.references["task_id"]))
        with Session(engine) as db, db.begin():
            guarded = _live(db, lease, task_id)
            if guarded is None or guarded[2].state not in {"queued", "running"}:
                return lambda _db: None
            _case, run, task = guarded
            mark_started(db, run, run.checklist_id)
            task.state = "running"
        with Session(engine) as db:
            spec = load_spec(db, task_id)
        if spec is None:
            return lambda _db: None
        outcome, checkpoint_id = run_task_graph(settings, executor, spec)

        def apply(db: Session) -> None:
            guarded = _live(db, lease, task_id)
            if guarded is None or guarded[2].state != "running":
                return  # Cancelled, deleted or already persisted; keep canonical state.
            case, run, task = guarded
            persist_outcome(db, task, outcome)
            if checkpoint_id:
                db.merge(
                    GraphCheckpointReference(
                        thread_id=thread_id(spec),
                        checkpoint_namespace="",
                        checkpoint_id=checkpoint_id,
                        case_id=case.id,
                        run_id=run.id,
                        state_refs={"task_id": str(task.id)},
                    )
                )
            advance_run(db, case, run)

        return apply

    def run_deadline(lease: Lease, lost: threading.Event) -> Applier:
        run_id = UUID(str(lease.references["run_id"]))

        def apply(db: Session) -> None:
            case = db.get(Case, lease.case_id)
            run = db.get(VerificationRun, run_id)
            if (
                case is None
                or run is None
                or run.state not in {"queued", "running"}
                or case.write_generation != run.generation
            ):
                return
            claims = list(
                db.scalars(
                    select(Claim).where(
                        Claim.case_id == run.case_id, Claim.checklist_id == run.checklist_id
                    )
                )
            )
            assess_checklist(db, run, claims)
            publish_snapshot(db, case, run, "deadline")
            append_event(
                db,
                case.id,
                "run.progress",
                f"run-deadline:{run.id}",
                {"run_id": str(run.id), "state": run.state, "deadline_reached": True},
                revision_id=run.revision_id,
                run_id=run.id,
            )

        return apply

    return {"check_task": check_task, "run_deadline": run_deadline}


def checklist_for(db: Session, run: VerificationRun) -> ChecklistVersion | None:
    return db.get(ChecklistVersion, run.checklist_id)
