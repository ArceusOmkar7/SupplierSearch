"""Owner-scoped cases, conversation and requirement revisions (drafts need explicit confirm)."""

import base64
import json
import zlib
from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Header, Query, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, or_, select

from verisource.api.dependencies import (
    Database,
    MutationSession,
    SignedIn,
    owned_case,
    owned_child,
)
from verisource.api.errors import reject
from verisource.db.models import (
    Case,
    CaseCreationReceipt,
    ChecklistVersion,
    ConversationMessage,
    RequirementRevision,
    VerificationRun,
)
from verisource.domain import intake, lifecycle
from verisource.domain.commands import append_event, case_etag, execute_command
from verisource.orchestration.jobs import enqueue

router = APIRouter(prefix="/api/v1")

IdempotencyKey = Annotated[str | None, Header(alias="Idempotency-Key")]
IfMatch = Annotated[str | None, Header(alias="If-Match")]


class CreateCase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = None
    initial_text: str | None = None
    suppliers: list[dict[str, Any]] | None = None


class PatchCase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str


class PatchRevision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    requirements: dict[str, Any] | None = None
    location: dict[str, Any] | None = None
    suppliers: list[dict[str, Any]] | None = None


class PostMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str
    client_message_id: str | None = None
    revision_id: UUID | None = None


class NewRevision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    based_on_revision_id: UUID | None = None
    reason: str | None = None


def present_case(case: Case) -> dict[str, Any]:
    return {
        "id": str(case.id),
        "title": case.title,
        "state": case.state,
        "active_revision_id": str(case.active_revision_id) if case.active_revision_id else None,
        "latest_snapshot_id": str(case.latest_snapshot_id) if case.latest_snapshot_id else None,
        "version": case.version,
        "created_at": case.created_at.isoformat(),
        "closed_at": case.closed_at.isoformat() if case.closed_at else None,
        "etag": case_etag(case),
    }


def present_message(message: ConversationMessage) -> dict[str, Any]:
    return {
        "id": str(message.id),
        "case_id": str(message.case_id),
        "revision_id": str(message.revision_id) if message.revision_id else None,
        "actor": message.actor,
        "text": message.text,
        "component_refs": message.component_refs,
        "sequence": message.sequence,
        "created_at": message.created_at.isoformat(),
    }


def command_response(body: dict[str, Any], etag: str, status: int) -> JSONResponse:
    return JSONResponse(body, status_code=status, headers={"ETag": etag})


def page(items: list[Any], limit: int, cursor_of: Any) -> dict[str, Any]:
    more = len(items) > limit
    items = items[:limit]
    return {"items": items, "next_cursor": cursor_of(items[-1]) if more and items else None}


def encode_cursor(*parts: Any) -> str:
    raw = json.dumps([str(p) for p in parts]).encode()
    return base64.urlsafe_b64encode(raw).decode()


def decode_cursor(cursor: str | None) -> list[str] | None:
    if not cursor:
        return None
    try:
        parts = json.loads(base64.urlsafe_b64decode(cursor.encode()))
        if not isinstance(parts, list) or not all(isinstance(p, str) for p in parts):
            raise ValueError
        return parts
    except ValueError:
        raise reject(400, "bad_cursor", "The page cursor is not valid.") from None


# ---- cases ----------------------------------------------------------------------------


@router.get("/cases")
def list_cases(
    session: SignedIn,
    db: Database,
    cursor: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
) -> dict[str, Any]:
    query = (
        select(Case)
        .where(Case.owner_id == session.buyer_id, Case.state != "deleting")
        .order_by(Case.created_at.desc(), Case.id.desc())
        .limit(limit + 1)
    )
    parts = decode_cursor(cursor)
    if parts:
        try:
            created, identifier = datetime.fromisoformat(parts[0]), UUID(parts[1])
        except ValueError, IndexError:
            raise reject(400, "bad_cursor", "The page cursor is not valid.") from None
        query = query.where(
            or_(Case.created_at < created, (Case.created_at == created) & (Case.id < identifier))
        )
    cases = list(db.scalars(query))
    return page(
        [present_case(c) for c in cases],
        limit,
        lambda item: encode_cursor(item["created_at"], item["id"]),
    )


@router.post("/cases")
def create_case(
    body: CreateCase, session: MutationSession, db: Database, key: IdempotencyKey = None
) -> JSONResponse:
    if not key or not key.strip():
        raise reject(400, "missing_idempotency_key", "Send an Idempotency-Key header.")
    payload = body.model_dump()
    body_hash = intake.json_hash(payload)
    db.execute(select(func.pg_advisory_xact_lock(zlib.crc32(f"{session.buyer_id}:{key}".encode()))))
    receipt = db.get(CaseCreationReceipt, (session.buyer_id, key))
    if receipt is not None:
        if receipt.body_hash != body_hash:
            raise reject(409, "idempotency_collision", "This key was used with another body.")
        existing = db.scalar(
            select(Case).where(
                Case.id == receipt.case_id,
                Case.owner_id == session.buyer_id,
                Case.state != "deleting",
            )
        )
        if existing is None:  # Deleted-resource retries never re-create a case.
            raise reject(404, "not_found", "This resource is unavailable.")
        revision = db.scalar(
            select(RequirementRevision)
            .where(RequirementRevision.case_id == existing.id)
            .order_by(RequirementRevision.sequence)
            .limit(1)
        )
        assert revision is not None
        return command_response(
            {"case": present_case(existing), "revision": intake.present_revision(revision)},
            case_etag(existing),
            201,
        )
    case, revision, message = intake.create_case_draft(
        db,
        buyer_id=session.buyer_id,
        title=body.title or "Untitled case",
        initial_text=body.initial_text,
        suppliers=body.suppliers or [],
    )
    db.add(
        CaseCreationReceipt(
            buyer_id=session.buyer_id, idempotency_key=key, body_hash=body_hash, case_id=case.id
        )
    )
    if message is not None:
        append_event(
            db,
            case.id,
            "message.created",
            f"message:{message.id}",
            {"message_id": str(message.id)},
            revision_id=revision.id,
        )
    append_event(
        db,
        case.id,
        "revision.updated",
        f"revision-created:{revision.id}",
        {"revision_id": str(revision.id), "status": "draft"},
        revision_id=revision.id,
    )
    db.flush()
    return command_response(
        {"case": present_case(case), "revision": intake.present_revision(revision)},
        case_etag(case),
        201,
    )


@router.get("/cases/{case_id}")
def read_case(case_id: UUID, response: Response, session: SignedIn, db: Database) -> dict[str, Any]:
    case = owned_case(db, case_id, session.buyer_id)
    response.headers["ETag"] = case_etag(case)
    draft = db.scalar(
        select(RequirementRevision).where(
            RequirementRevision.case_id == case.id, RequirementRevision.status == "draft"
        )
    )
    run = db.scalar(
        select(VerificationRun)
        .where(VerificationRun.case_id == case.id)
        .order_by(VerificationRun.requested_at.desc())
        .limit(1)
    )
    checklist = (
        db.scalar(
            select(ChecklistVersion)
            .where(
                ChecklistVersion.case_id == case.id,
                ChecklistVersion.revision_id == case.active_revision_id,
            )
            .order_by(ChecklistVersion.sequence.desc())
            .limit(1)
        )
        if case.active_revision_id
        else None
    )
    return {
        **present_case(case),
        "active_checklist_id": str(checklist.id) if checklist else None,
        "active_checklist_status": checklist.status if checklist else None,
        "draft_revision_id": str(draft.id) if draft else None,
        "latest_run_id": str(run.id) if run else None,
        "latest_run_state": run.state if run else None,
    }


@router.patch("/cases/{case_id}")
def rename_case(
    case_id: UUID,
    body: PatchCase,
    session: MutationSession,
    db: Database,
    key: IdempotencyKey = None,
    if_match: IfMatch = None,
) -> JSONResponse:
    def apply(case: Case) -> dict[str, Any]:
        if not body.title.strip():
            raise reject(422, "invalid_field", "A title is required.")
        case.title = body.title.strip()
        return {"title": case.title}

    result, etag = execute_command(
        db,
        case_id=case_id,
        buyer_id=session.buyer_id,
        operation="rename_case",
        key=key,
        if_match=if_match,
        body=body.model_dump(),
        apply=apply,
    )
    return command_response({**result, "etag": etag}, etag, 200)


# ---- messages -------------------------------------------------------------------------


@router.get("/cases/{case_id}/messages")
def list_messages(
    case_id: UUID,
    session: SignedIn,
    db: Database,
    cursor: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
) -> dict[str, Any]:
    case = owned_case(db, case_id, session.buyer_id)
    query = (
        select(ConversationMessage)
        .where(ConversationMessage.case_id == case.id)
        .order_by(ConversationMessage.sequence)
        .limit(limit + 1)
    )
    parts = decode_cursor(cursor)
    if parts:
        query = query.where(ConversationMessage.sequence > int(parts[0]))
    items = [present_message(m) for m in db.scalars(query)]
    return page(items, limit, lambda item: encode_cursor(item["sequence"]))


@router.post("/cases/{case_id}/messages")
def post_message(
    case_id: UUID,
    body: PostMessage,
    session: MutationSession,
    db: Database,
    key: IdempotencyKey = None,
) -> JSONResponse:
    if not body.text.strip() or len(body.text) > 20000:
        raise reject(422, "invalid_field", "Enter message text.")

    def apply(case: Case) -> dict[str, Any]:
        if body.client_message_id:
            duplicate = db.scalar(
                select(ConversationMessage).where(
                    ConversationMessage.case_id == case.id,
                    ConversationMessage.client_message_id == body.client_message_id,
                )
            )
            if duplicate is not None:
                return {"message": present_message(duplicate), "interpretation": "queued"}
        if body.revision_id is not None:
            owned_child(
                db,
                RequirementRevision,
                body.revision_id,
                case_id=case.id,
                buyer_id=session.buyer_id,
            )
        message = ConversationMessage(
            case_id=case.id,
            revision_id=body.revision_id,
            actor="buyer",
            text=body.text.strip(),
            component_refs=[],
            sequence=intake.next_message_sequence(db, case.id),
            client_message_id=body.client_message_id,
        )
        db.add(message)
        db.flush()
        append_event(
            db,
            case.id,
            "message.created",
            f"message:{message.id}",
            {"message_id": str(message.id)},
            revision_id=body.revision_id,
        )
        # Interpretation is a draft-only proposal; it can never confirm, start or select.
        enqueue(
            db,
            case,
            kind="interpret_message",
            operation_key=f"interpret:{message.id}",
            references={"message_id": str(message.id)},
        )
        return {"message": present_message(message), "interpretation": "queued"}

    result, etag = execute_command(
        db,
        case_id=case_id,
        buyer_id=session.buyer_id,
        operation="post_message",
        key=key,
        if_match=None,
        body=body.model_dump(mode="json"),
        apply=apply,
        require_if_match=False,
    )
    return command_response(result, etag, 202)


# ---- revisions ------------------------------------------------------------------------


@router.get("/cases/{case_id}/revisions")
def list_revisions(
    case_id: UUID,
    session: SignedIn,
    db: Database,
    cursor: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
) -> dict[str, Any]:
    case = owned_case(db, case_id, session.buyer_id)
    query = (
        select(RequirementRevision)
        .where(RequirementRevision.case_id == case.id)
        .order_by(RequirementRevision.sequence)
        .limit(limit + 1)
    )
    parts = decode_cursor(cursor)
    if parts:
        query = query.where(RequirementRevision.sequence > int(parts[0]))
    items = [
        {
            "id": str(r.id),
            "sequence": r.sequence,
            "status": r.status,
            "confirmed_at": r.confirmed_at.isoformat() if r.confirmed_at else None,
            "created_at": r.created_at.isoformat(),
        }
        for r in db.scalars(query)
    ]
    return page(items, limit, lambda item: encode_cursor(item["sequence"]))


@router.get("/cases/{case_id}/revisions/{revision_id}")
def read_revision(
    case_id: UUID, revision_id: UUID, response: Response, session: SignedIn, db: Database
) -> dict[str, Any]:
    revision = owned_child(
        db, RequirementRevision, revision_id, case_id=case_id, buyer_id=session.buyer_id
    )
    body = intake.present_revision(revision)
    response.headers["ETag"] = body["etag"]
    return body


@router.post("/cases/{case_id}/revisions")
def new_revision(
    case_id: UUID,
    body: NewRevision,
    session: MutationSession,
    db: Database,
    key: IdempotencyKey = None,
    if_match: IfMatch = None,
) -> JSONResponse:
    def apply(case: Case) -> dict[str, Any]:
        draft = db.scalar(
            select(RequirementRevision).where(
                RequirementRevision.case_id == case.id, RequirementRevision.status == "draft"
            )
        )
        if draft is not None:
            raise reject(409, "draft_exists", "Finish or abandon the current draft first.")
        base_id = body.based_on_revision_id or case.active_revision_id
        base = (
            owned_child(db, RequirementRevision, base_id, case_id=case.id, buyer_id=case.owner_id)
            if base_id
            else None
        )
        latest = int(
            db.scalar(
                select(func.max(RequirementRevision.sequence)).where(
                    RequirementRevision.case_id == case.id
                )
            )
            or 0
        )
        revision = RequirementRevision(
            case_id=case.id,
            sequence=latest + 1,
            status="draft",
            requirements_json=dict(base.requirements_json) if base else {},
            location_json=dict(base.location_json) if base else {},
            supplier_set_json=list(base.supplier_set_json) if base else [],
            input_provenance={
                "schema_version": 1,
                "mode": "copied_from_revision",
                "based_on": str(base.id) if base else None,
                "reason": body.reason,
            },
        )
        db.add(revision)
        db.flush()
        append_event(
            db,
            case.id,
            "revision.updated",
            f"revision-created:{revision.id}",
            {"revision_id": str(revision.id), "status": "draft"},
            revision_id=revision.id,
        )
        return intake.present_revision(revision)

    result, _etag = execute_command(
        db,
        case_id=case_id,
        buyer_id=session.buyer_id,
        operation="new_revision",
        key=key,
        if_match=if_match,
        body=body.model_dump(mode="json"),
        apply=apply,
    )
    return command_response(result, result["etag"], 201)


def _revision_command(
    case_id: UUID,
    revision_id: UUID,
    session: Any,
    db: Any,
    key: str | None,
    if_match: str | None,
    operation: str,
    body: dict[str, Any],
    mutate: Any,
) -> tuple[dict[str, Any], str]:
    def current(case: Case) -> str:
        revision = owned_child(
            db, RequirementRevision, revision_id, case_id=case.id, buyer_id=case.owner_id
        )
        return intake.revision_etag(revision)

    def apply(case: Case) -> dict[str, Any]:
        revision = owned_child(
            db, RequirementRevision, revision_id, case_id=case.id, buyer_id=case.owner_id
        )
        mutate(case, revision)
        db.flush()
        return intake.present_revision(revision)

    result, _case_tag = execute_command(
        db,
        case_id=case_id,
        buyer_id=session.buyer_id,
        operation=f"{operation}:{revision_id}",
        key=key,
        if_match=if_match,
        body=body,
        apply=apply,
        current_etag=current,
    )
    return result, result["etag"]


@router.patch("/cases/{case_id}/revisions/{revision_id}")
def patch_revision(
    case_id: UUID,
    revision_id: UUID,
    body: PatchRevision,
    session: MutationSession,
    db: Database,
    key: IdempotencyKey = None,
    if_match: IfMatch = None,
) -> JSONResponse:
    payload = body.model_dump(exclude_unset=True)

    def mutate(case: Case, revision: RequirementRevision) -> None:
        intake.apply_revision_patch(db, case, revision, payload)
        append_event(
            db,
            case.id,
            "revision.updated",
            f"revision-edit:{revision.id}:{intake.revision_etag(revision)}",
            {"revision_id": str(revision.id), "status": revision.status},
            revision_id=revision.id,
        )

    result, etag = _revision_command(
        case_id, revision_id, session, db, key, if_match, "patch_revision", payload, mutate
    )
    return command_response(result, etag, 200)


@router.post("/cases/{case_id}/revisions/{revision_id}/confirm")
def confirm_revision(
    case_id: UUID,
    revision_id: UUID,
    session: MutationSession,
    db: Database,
    key: IdempotencyKey = None,
    if_match: IfMatch = None,
) -> JSONResponse:
    def mutate(case: Case, revision: RequirementRevision) -> None:
        intake.confirm_revision(db, case, revision, session.buyer_id)
        append_event(
            db,
            case.id,
            "revision.confirmed",
            f"revision-confirmed:{revision.id}",
            {"revision_id": str(revision.id)},
            revision_id=revision.id,
        )

    result, etag = _revision_command(
        case_id, revision_id, session, db, key, if_match, "confirm_revision", {}, mutate
    )
    return command_response(result, etag, 200)


class CloseCase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    snapshot_id: UUID
    reason: str | None = None


class ReopenCase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str | None = None


@router.post("/cases/{case_id}/close")
def close_case_route(
    case_id: UUID,
    body: CloseCase,
    session: MutationSession,
    db: Database,
    key: IdempotencyKey = None,
    if_match: IfMatch = None,
) -> JSONResponse:
    def apply(case: Case) -> dict[str, Any]:
        lifecycle.close_case(db, case, body.snapshot_id, body.reason)
        return {"case": present_case(case)}

    result, etag = execute_command(
        db, case_id=case_id, buyer_id=session.buyer_id, operation="close_case", key=key,
        if_match=if_match, body=body.model_dump(mode="json"), apply=apply,
    )  # fmt: skip
    return command_response(result, etag, 200)


@router.post("/cases/{case_id}/reopen")
def reopen_case_route(
    case_id: UUID,
    body: ReopenCase,
    session: MutationSession,
    db: Database,
    key: IdempotencyKey = None,
    if_match: IfMatch = None,
) -> JSONResponse:
    def apply(case: Case) -> dict[str, Any]:
        lifecycle.reopen_case(db, case, body.reason)
        return {"case": present_case(case)}

    result, etag = execute_command(
        db, case_id=case_id, buyer_id=session.buyer_id, operation="reopen_case", key=key,
        if_match=if_match, body=body.model_dump(mode="json"), apply=apply,
    )  # fmt: skip
    return command_response(result, etag, 200)
