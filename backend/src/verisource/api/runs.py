"""Run admission, progress and cancellation; admission persists all work atomically."""

from collections import Counter
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, update

from verisource.api.cases import IdempotencyKey, IfMatch, command_response
from verisource.api.dependencies import Database, MutationSession, SignedIn, owned_child
from verisource.country_packs.registry import UnsupportedJurisdiction, pack_for
from verisource.db.models import (
    Case,
    CheckAttempt,
    ChecklistVersion,
    CheckTask,
    RequirementRevision,
    VerificationRun,
    WorkItem,
)
from verisource.domain.commands import append_event, execute_command
from verisource.orchestration.planning import admit_run

router = APIRouter(prefix="/api/v1")


class StartRun(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision_id: UUID
    checklist_id: UUID
    mode: str = "live"


def run_etag(run: VerificationRun) -> str:
    return f'"{run.id}:{run.state}:{run.completed_at.isoformat() if run.completed_at else ""}"'


def present_run(db: Any, run: VerificationRun) -> dict[str, Any]:
    states = Counter(db.scalars(select(CheckTask.state).where(CheckTask.run_id == run.id)).all())
    return {
        "id": str(run.id),
        "case_id": str(run.case_id),
        "revision_id": str(run.revision_id),
        "checklist_id": str(run.checklist_id),
        "policy_version": run.policy_version,
        "country_pack_version": run.country_pack_version,
        "mode": run.mode,
        "state": run.state,
        "requested_at": run.requested_at.isoformat(),
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "initial_deadline": run.initial_deadline.isoformat(),
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "budgets": run.budgets_json,
        "task_count": sum(states.values()),
        "task_states": dict(states),
        "etag": run_etag(run),
    }


def source_capabilities(revision: RequirementRevision) -> list[dict[str, Any]]:
    try:
        pack = pack_for(revision.location_json.get("country") or "IN")
    except UnsupportedJurisdiction:
        return [
            {
                "source_id": "unsupported_jurisdiction",
                "enabled": False,
                "disabled_reason": "No country pack covers this jurisdiction; claims stay unproven.",
            }
        ]
    return [
        {
            "source_id": c.source_id,
            "claim_types": list(c.claim_types),
            "enabled": c.enabled,
            "access_mode": c.access_mode,
            "disabled_reason": c.disabled_reason,
        }
        for c in pack.capabilities()
    ]


@router.post("/cases/{case_id}/runs")
def start_run(
    case_id: UUID,
    body: StartRun,
    session: MutationSession,
    db: Database,
    key: IdempotencyKey = None,
    if_match: IfMatch = None,
) -> JSONResponse:
    def apply(case: Case) -> dict[str, Any]:
        revision = owned_child(
            db, RequirementRevision, body.revision_id, case_id=case.id, buyer_id=case.owner_id
        )
        checklist = owned_child(
            db, ChecklistVersion, body.checklist_id, case_id=case.id, buyer_id=case.owner_id
        )
        run = admit_run(db, case, revision, checklist, mode=body.mode, idempotency_key=str(key))
        append_event(
            db,
            case.id,
            "run.queued",
            f"run-queued:{run.id}",
            {"run_id": str(run.id), "mode": run.mode},
            revision_id=revision.id,
            run_id=run.id,
        )
        return {
            "run": present_run(db, run),
            "source_capabilities": source_capabilities(revision),
        }

    result, etag = execute_command(
        db,
        case_id=case_id,
        buyer_id=session.buyer_id,
        operation="start_run",
        key=key,
        if_match=if_match,
        body=body.model_dump(mode="json"),
        apply=apply,
    )
    return command_response(result, etag, 202)


@router.get("/cases/{case_id}/runs/{run_id}")
def read_run(
    case_id: UUID, run_id: UUID, response: Response, session: SignedIn, db: Database
) -> dict[str, Any]:
    run = owned_child(db, VerificationRun, run_id, case_id=case_id, buyer_id=session.buyer_id)
    body = present_run(db, run)
    response.headers["ETag"] = body["etag"]
    tasks = db.scalars(select(CheckTask).where(CheckTask.run_id == run.id)).all()
    return {
        "run": body,
        "tasks": [
            {
                "id": str(t.id),
                "supplier_id": str(t.supplier_id),
                "check_type": t.check_type,
                "source_id": t.source_id,
                "state": t.state,
                "dependency_ids": [str(d) for d in t.dependency_ids],
                "wait_action_id": str(t.wait_action_id) if t.wait_action_id else None,
            }
            for t in tasks
        ],
    }


@router.get("/cases/{case_id}/runs/{run_id}/attempts")
def list_attempts(case_id: UUID, run_id: UUID, session: SignedIn, db: Database) -> dict[str, Any]:
    """Actual attempts for the run: what was tried, whether anything was sent, and the outcome."""
    run = owned_child(db, VerificationRun, run_id, case_id=case_id, buyer_id=session.buyer_id)
    attempts = db.scalars(
        select(CheckAttempt)
        .where(CheckAttempt.run_id == run.id, CheckAttempt.case_id == run.case_id)
        .order_by(CheckAttempt.requested_at)
    )
    return {
        "items": [
            {
                "id": str(a.id),
                "task_id": str(a.task_id),
                "supplier_id": str(a.supplier_id),
                "kind": a.kind,
                "target": a.target,
                "outcome": a.outcome,
                "reason_code": a.reason_code,
                "request_dispatched": a.request_dispatched,
                "http_status": a.http_status,
                "requested_at": a.requested_at.isoformat(),
                "finished_at": a.finished_at.isoformat(),
                "retry_of": str(a.retry_of) if a.retry_of else None,
            }
            for a in attempts
        ],
        "next_cursor": None,
    }


@router.post("/cases/{case_id}/runs/{run_id}/cancel")
def cancel_run(
    case_id: UUID,
    run_id: UUID,
    session: MutationSession,
    db: Database,
    key: IdempotencyKey = None,
    if_match: IfMatch = None,
) -> JSONResponse:
    def current(case: Case) -> str:
        return run_etag(
            owned_child(db, VerificationRun, run_id, case_id=case.id, buyer_id=case.owner_id)
        )

    def apply(case: Case) -> dict[str, Any]:
        run = owned_child(db, VerificationRun, run_id, case_id=case.id, buyer_id=case.owner_id)
        if run.state in {"queued", "running"}:
            run.state = "cancelled"
            run.completed_at = datetime.now(UTC)
            db.execute(
                update(CheckTask)
                .where(
                    CheckTask.run_id == run.id,
                    CheckTask.state.in_(("queued", "running", "waiting_input")),
                )
                .values(state="cancelled")
            )
            db.execute(
                update(WorkItem)
                .where(
                    WorkItem.run_id == run.id,
                    WorkItem.state.in_(("queued", "retry_wait", "leased")),
                )
                .values(state="cancelled", lease_owner=None, lease_expires_at=None)
            )
            append_event(
                db,
                case.id,
                "run.progress",
                f"run-cancelled:{run.id}",
                {"run_id": str(run.id), "state": "cancelled"},
                run_id=run.id,
            )
            if case.state == "active":
                case.state = "ready"
        elif run.state != "cancelled":
            raise_conflict()
        db.flush()
        return {"run": present_run(db, run)}

    result, _etag = execute_command(
        db,
        case_id=case_id,
        buyer_id=session.buyer_id,
        operation=f"cancel_run:{run_id}",
        key=key,
        if_match=if_match,
        body={},
        apply=apply,
        current_etag=current,
    )
    return command_response(result, result["run"]["etag"], 202)


def raise_conflict() -> None:
    from verisource.api.errors import reject

    raise reject(409, "run_finished", "This run has already finished.")
