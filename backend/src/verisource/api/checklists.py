"""Claim proposal, editable checklist and immutable confirmation routes."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Header, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from verisource.api.cases import IdempotencyKey, IfMatch, command_response
from verisource.api.dependencies import Database, MutationSession, SignedIn, owned_child
from verisource.db.models import Case, ChecklistVersion, RequirementRevision
from verisource.domain import claims as claim_domain
from verisource.domain.commands import append_event, execute_command

router = APIRouter(prefix="/api/v1")
_ = Annotated, Header  # Header aliases are declared in verisource.api.cases.


class PatchChecklist(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claims: list[dict[str, Any]] | None = None
    add: list[dict[str, Any]] | None = None
    remove: list[str] | None = None


class NewChecklist(BaseModel):
    model_config = ConfigDict(extra="forbid")
    based_on_checklist_id: UUID
    revision_id: UUID


@router.post("/cases/{case_id}/revisions/{revision_id}/claims")
def propose_claims(
    case_id: UUID,
    revision_id: UUID,
    session: MutationSession,
    db: Database,
    key: IdempotencyKey = None,
) -> JSONResponse:
    def apply(case: Case) -> dict[str, Any]:
        revision = owned_child(
            db, RequirementRevision, revision_id, case_id=case.id, buyer_id=case.owner_id
        )
        checklist = claim_domain.create_draft_checklist(db, case, revision)
        append_event(
            db,
            case.id,
            "checklist.ready",
            f"checklist-ready:{checklist.id}",
            {"checklist_id": str(checklist.id)},
            revision_id=revision.id,
        )
        return {"checklist": claim_domain.present_checklist(db, checklist)}

    result, _etag = execute_command(
        db,
        case_id=case_id,
        buyer_id=session.buyer_id,
        operation=f"propose_claims:{revision_id}",
        key=key,
        if_match=None,
        body={"revision_id": str(revision_id)},
        apply=apply,
        require_if_match=False,
    )
    return command_response(result, result["checklist"]["etag"], 202)


@router.get("/cases/{case_id}/checklists/{checklist_id}")
def read_checklist(
    case_id: UUID, checklist_id: UUID, response: Response, session: SignedIn, db: Database
) -> dict[str, Any]:
    checklist = owned_child(
        db, ChecklistVersion, checklist_id, case_id=case_id, buyer_id=session.buyer_id
    )
    body = claim_domain.present_checklist(db, checklist)
    response.headers["ETag"] = body["etag"]
    return body


def _checklist_command(
    case_id: UUID,
    checklist_id: UUID,
    session: Any,
    db: Any,
    key: str | None,
    if_match: str | None,
    operation: str,
    body: dict[str, Any],
    mutate: Any,
) -> tuple[dict[str, Any], str]:
    def load(case: Case) -> ChecklistVersion:
        return owned_child(
            db, ChecklistVersion, checklist_id, case_id=case.id, buyer_id=case.owner_id
        )

    def current(case: Case) -> str:
        return str(claim_domain.present_checklist(db, load(case))["etag"])

    def apply(case: Case) -> dict[str, Any]:
        checklist = load(case)
        mutate(case, checklist)
        db.flush()
        return claim_domain.present_checklist(db, checklist)

    result, _ = execute_command(
        db,
        case_id=case_id,
        buyer_id=session.buyer_id,
        operation=f"{operation}:{checklist_id}",
        key=key,
        if_match=if_match,
        body=body,
        apply=apply,
        current_etag=current,
    )
    return result, result["etag"]


@router.patch("/cases/{case_id}/checklists/{checklist_id}")
def patch_checklist(
    case_id: UUID,
    checklist_id: UUID,
    body: PatchChecklist,
    session: MutationSession,
    db: Database,
    key: IdempotencyKey = None,
    if_match: IfMatch = None,
) -> JSONResponse:
    payload = body.model_dump(exclude_unset=True)

    def mutate(case: Case, checklist: ChecklistVersion) -> None:
        claim_domain.apply_checklist_patch(db, case, checklist, payload)

    result, etag = _checklist_command(
        case_id, checklist_id, session, db, key, if_match, "patch_checklist", payload, mutate
    )
    return command_response(result, etag, 200)


@router.post("/cases/{case_id}/checklists/{checklist_id}/confirm")
def confirm_checklist(
    case_id: UUID,
    checklist_id: UUID,
    session: MutationSession,
    db: Database,
    key: IdempotencyKey = None,
    if_match: IfMatch = None,
) -> JSONResponse:
    def mutate(case: Case, checklist: ChecklistVersion) -> None:
        claim_domain.confirm_checklist(db, case, checklist, session.buyer_id)
        append_event(
            db,
            case.id,
            "checklist.confirmed",
            f"checklist-confirmed:{checklist.id}",
            {"checklist_id": str(checklist.id)},
            revision_id=checklist.revision_id,
        )

    result, etag = _checklist_command(
        case_id, checklist_id, session, db, key, if_match, "confirm_checklist", {}, mutate
    )
    return command_response(result, etag, 200)


@router.post("/cases/{case_id}/checklists")
def new_checklist_version(
    case_id: UUID,
    body: NewChecklist,
    session: MutationSession,
    db: Database,
    key: IdempotencyKey = None,
) -> JSONResponse:
    def apply(case: Case) -> dict[str, Any]:
        source = owned_child(
            db,
            ChecklistVersion,
            body.based_on_checklist_id,
            case_id=case.id,
            buyer_id=case.owner_id,
        )
        owned_child(
            db, RequirementRevision, body.revision_id, case_id=case.id, buyer_id=case.owner_id
        )
        draft = claim_domain.clone_checklist(db, case, source)
        return claim_domain.present_checklist(db, draft)

    result, _ = execute_command(
        db,
        case_id=case_id,
        buyer_id=session.buyer_id,
        operation="new_checklist",
        key=key,
        if_match=None,
        body=body.model_dump(mode="json"),
        apply=apply,
        require_if_match=False,
    )
    return command_response(result, result["etag"], 201)
