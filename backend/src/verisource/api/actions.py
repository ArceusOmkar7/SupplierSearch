"""Permitted buyer actions (replacement document, identity decision); never manual scraping."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Query, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from verisource.api.cases import IdempotencyKey, IfMatch, command_response
from verisource.api.dependencies import Database, MutationSession, SignedIn, owned_case, owned_child
from verisource.db.models import Case, HumanAction
from verisource.domain.actions import action_etag, present_action, resolve_action
from verisource.domain.commands import execute_command

router = APIRouter(prefix="/api/v1")


class ResolveAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    replacement_document_id: UUID | None = None
    decision: str | None = None


@router.get("/cases/{case_id}/actions")
def list_actions(
    case_id: UUID,
    session: SignedIn,
    db: Database,
    state: Annotated[str | None, Query(pattern="^(pending|resolved|cancelled)$")] = None,
) -> dict[str, Any]:
    case = owned_case(db, case_id, session.buyer_id)
    query = (
        select(HumanAction).where(HumanAction.case_id == case.id).order_by(HumanAction.created_at)
    )
    if state:
        query = query.where(HumanAction.state == state)
    return {"items": [present_action(a) for a in db.scalars(query)], "next_cursor": None}


@router.get("/cases/{case_id}/actions/{action_id}")
def read_action(
    case_id: UUID, action_id: UUID, response: Response, session: SignedIn, db: Database
) -> dict[str, Any]:
    action = owned_child(db, HumanAction, action_id, case_id=case_id, buyer_id=session.buyer_id)
    response.headers["ETag"] = action_etag(action)
    return present_action(action)


@router.post("/cases/{case_id}/actions/{action_id}/resolve")
def resolve(
    case_id: UUID,
    action_id: UUID,
    body: ResolveAction,
    session: MutationSession,
    db: Database,
    key: IdempotencyKey = None,
    if_match: IfMatch = None,
) -> JSONResponse:
    payload = body.model_dump(mode="json", exclude_none=True)

    def load(case: Case) -> HumanAction:
        return owned_child(db, HumanAction, action_id, case_id=case.id, buyer_id=case.owner_id)

    def apply(case: Case) -> dict[str, Any]:
        return resolve_action(db, case, load(case), session.buyer_id, payload)

    result, _ = execute_command(
        db,
        case_id=case_id,
        buyer_id=session.buyer_id,
        operation=f"resolve_action:{action_id}",
        key=key,
        if_match=if_match,
        body=payload,
        apply=apply,
        current_etag=lambda case: action_etag(load(case)),
    )
    return command_response(result, result["etag"], 202)
