"""Serialize case commands and retain idempotent outcomes in case-scoped durable events."""

import hashlib
import json
from collections.abc import Callable
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from verisource.api.dependencies import owned_case
from verisource.db.models import Case, CaseEvent


def case_etag(case: Case) -> str:
    return f'"{case.id}:{case.version}"'


def append_event(
    db: Session,
    case_id: UUID,
    event_type: str,
    operation_key: str,
    payload: dict[str, Any],
    *,
    revision_id: UUID | None = None,
    run_id: UUID | None = None,
) -> CaseEvent:
    case = db.scalar(select(Case).where(Case.id == case_id).with_for_update())
    if case is None or case.state == "deleting":
        raise HTTPException(404)
    existing = db.scalar(
        select(CaseEvent).where(
            CaseEvent.case_id == case_id, CaseEvent.operation_key == operation_key
        )
    )
    if existing is not None:
        return existing
    previous = db.scalar(select(func.max(CaseEvent.sequence)).where(CaseEvent.case_id == case_id))
    event = CaseEvent(
        case_id=case_id,
        sequence=int(previous or 0) + 1,
        type=event_type,
        operation_key=operation_key,
        public_payload=payload,
        object_refs={},
        revision_id=revision_id,
        run_id=run_id,
    )
    db.add(event)
    db.flush()
    return event


def execute_command(
    db: Session,
    *,
    case_id: UUID,
    buyer_id: UUID,
    operation: str,
    key: str | None,
    if_match: str | None,
    body: dict[str, Any],
    apply: Callable[[Case], dict[str, Any]],
    current_etag: Callable[[Case], str] | None = None,
    response_etag: Callable[[Case], str] | None = None,
    require_if_match: bool = True,
) -> tuple[dict[str, Any], str]:
    """`current_etag` selects the resource precondition (default: the case ETag);
    `response_etag` selects the ETag returned and replayed (default: the case ETag)."""
    case = owned_case(db, case_id, buyer_id, lock=True)
    if not key or not key.strip():
        raise HTTPException(400)
    operation_key = f"command:{buyer_id}:{operation}:{key}"
    body_hash = hashlib.sha256(
        json.dumps(
            body, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode("utf-8")
    ).hexdigest()
    previous = db.scalar(
        select(CaseEvent).where(
            CaseEvent.case_id == case_id, CaseEvent.operation_key == operation_key
        )
    )
    if previous is not None:
        if previous.public_payload.get("body_hash") != body_hash:
            raise HTTPException(409)
        payload = previous.public_payload
        response, etag = payload.get("response"), payload.get("etag")
        if not isinstance(response, dict) or not isinstance(etag, str):
            raise HTTPException(503)
        return response, etag
    if require_if_match and (if_match is None or if_match != (current_etag or case_etag)(case)):
        raise HTTPException(412)
    result = apply(case)
    case.version += 1
    db.flush()
    etag = (response_etag or case_etag)(case)
    append_event(
        db,
        case_id,
        "command.completed",
        operation_key,
        {"body_hash": body_hash, "response": result, "etag": etag},
    )
    return result, etag
