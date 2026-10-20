"""Resolve dependent buyer actions: an unlocked replacement document or an identity decision.

Only the tasks that depend on the action wait; every other result stays intact. Neither action
asks the buyer to browse a portal, solve a CAPTCHA or scrape anything.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from verisource.api.errors import reject
from verisource.db.models import (
    Case,
    CheckTask,
    DocumentArtifact,
    HumanAction,
    IdentityResolution,
    VerificationRun,
)
from verisource.domain.commands import append_event
from verisource.domain.intake import json_hash
from verisource.orchestration.graph import advance_run


def action_etag(action: HumanAction) -> str:
    digest = json_hash(
        [action.state, action.resolution_ref, [str(t) for t in action.affected_task_ids]]
    )
    return f'"{action.id}:{digest[:16]}"'


def present_action(action: HumanAction) -> dict[str, Any]:
    return {
        "id": str(action.id),
        "type": action.type,
        "state": action.state,
        "run_id": str(action.run_id),
        "revision_id": str(action.revision_id),
        "affected_task_ids": [str(t) for t in action.affected_task_ids],
        "requested_document_id": str(action.requested_document_ref)
        if action.requested_document_ref
        else None,
        "created_at": action.created_at.isoformat(),
        "resolved_at": action.resolved_at.isoformat() if action.resolved_at else None,
        "etag": action_etag(action),
    }


def _release_tasks(db: Session, action: HumanAction, state: str) -> None:
    db.execute(
        update(CheckTask)
        .where(CheckTask.id.in_(action.affected_task_ids), CheckTask.state == "waiting_input")
        .values(state=state, wait_action_id=None)
    )


def resolve_action(
    db: Session,
    case: Case,
    action: HumanAction,
    buyer_id: UUID,
    body: dict[str, Any],
) -> dict[str, Any]:
    if action.state != "pending":
        raise reject(409, "action_resolved", "This action is already resolved.")
    run = db.get(VerificationRun, action.run_id)
    assert run is not None
    if run.state not in {"queued", "running"}:
        raise reject(409, "run_finished", "The run this action belongs to has finished.")
    now = datetime.now(UTC)
    if action.type == "supply_unlocked_document":
        replacement_id = body.get("replacement_document_id")
        try:
            document = db.get(DocumentArtifact, UUID(str(replacement_id)))
        except ValueError:
            document = None
        original = (
            db.get(DocumentArtifact, action.requested_document_ref)
            if action.requested_document_ref
            else None
        )
        if document is None or document.case_id != case.id:
            raise reject(404, "not_found", "This resource is unavailable.")
        if document.state == "quarantined" or document.id == action.requested_document_ref:
            raise reject(422, "unreadable_replacement", "Upload a readable, unlocked PDF.")
        if original is not None and document.supplier_id != original.supplier_id:
            raise reject(422, "wrong_supplier", "The replacement belongs to another supplier.")
        if original is not None:
            original.state = "failed"
            original.state_reason = f"superseded_by:{document.id}"
        action.resolution_ref = str(document.id)
        _release_tasks(db, action, "queued")
    elif action.type == "resolve_identity":
        decision = body.get("decision")
        if decision not in {"confirm", "reject"}:
            raise reject(422, "invalid_field", "Choose confirm or reject.")
        tasks = list(
            db.scalars(select(CheckTask).where(CheckTask.id.in_(action.affected_task_ids)))
        )
        suppliers = {t.supplier_id for t in tasks}
        pending = list(
            db.scalars(
                select(IdentityResolution).where(
                    IdentityResolution.case_id == case.id,
                    IdentityResolution.supplier_id.in_(suppliers),
                    IdentityResolution.revision_id == action.revision_id,
                    IdentityResolution.state.in_(("proposed", "ambiguous")),
                )
            )
        )
        for resolution in pending:
            resolution.state = "confirmed" if decision == "confirm" else "rejected"
            resolution.resolution_basis = "buyer_review"
            resolution.resolved_by = buyer_id
            resolution.resolved_at = now
        action.resolution_ref = f"identity:{decision}"
        _release_tasks(db, action, "queued" if decision == "confirm" else "cancelled")
    else:  # pragma: no cover -- the type column is constrained.
        raise reject(409, "invalid_state", "Unknown action type.")
    action.state = "resolved"
    action.resolved_at = now
    db.flush()
    append_event(
        db,
        case.id,
        "action.resolved",
        f"action-resolved:{action.id}",
        {"action_id": str(action.id), "type": action.type},
        revision_id=action.revision_id,
        run_id=action.run_id,
    )
    advance_run(db, case, run)  # Queues the unblocked tasks; unrelated work is untouched.
    return present_action(action)
