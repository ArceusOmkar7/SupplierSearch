"""Durable case-local event stream (SSE) with replay, reset and continuous authorization.

Events come from committed rows in sequence order. Internal command receipts are never sent.
The session, ownership and deletion state are re-checked before every batch and at least
every 15 seconds; an unauthorized stream is closed. Reconnecting never triggers a command.
"""

import asyncio
import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Header, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from verisource.api.dependencies import Database, SignedIn, owned_case
from verisource.db.models import BuyerAccount, Case, CaseEvent, LoginSession
from verisource.security.sessions import SESSION_COOKIE, digest

router = APIRouter(prefix="/api/v1")

PUBLIC_EVENTS = {
    "message.created",
    "revision.updated",
    "revision.confirmed",
    "checklist.ready",
    "checklist.confirmed",
    "run.queued",
    "run.progress",
    "check.completed",
    "action.required",
    "action.resolved",
    "snapshot.ready",
    "report.ready",
    "case.closed",
    "case.deleting",
}
POLL_SECONDS = 1.0
REAUTHORIZE_SECONDS = 15.0
BATCH = 100


def present_event(event: CaseEvent) -> dict[str, Any]:
    return {
        "sequence": event.sequence,
        "type": event.type,
        "case_id": str(event.case_id),
        "revision_id": str(event.revision_id) if event.revision_id else None,
        "run_id": str(event.run_id) if event.run_id else None,
        "created_at": event.created_at.isoformat(),
        "payload": event.public_payload,
    }


def frame(event: CaseEvent) -> str:
    return (
        f"id: {event.sequence}\nevent: {event.type}\ndata: {json.dumps(present_event(event))}\n\n"
    )


def still_authorized(engine: Any, raw_cookie: str, case_id: UUID) -> bool:
    now = datetime.now(UTC)
    with Session(engine) as db:
        session = db.scalar(
            select(LoginSession)
            .join(BuyerAccount)
            .where(LoginSession.id_hash == digest(raw_cookie), BuyerAccount.disabled_at.is_(None))
        )
        if (
            session is None
            or session.revoked_at is not None
            or now >= session.expires_at
            or now - session.last_seen_at >= timedelta(minutes=30)
        ):
            return False
        case = db.scalar(select(Case).where(Case.id == case_id, Case.owner_id == session.buyer_id))
        return case is not None and case.state != "deleting"


def fetch_events(engine: Any, case_id: UUID, after: int) -> tuple[list[CaseEvent], int, int]:
    with Session(engine) as db:
        rows = list(
            db.scalars(
                select(CaseEvent)
                .where(
                    CaseEvent.case_id == case_id,
                    CaseEvent.sequence > after,
                    CaseEvent.type.in_(PUBLIC_EVENTS),
                )
                .order_by(CaseEvent.sequence)
                .limit(BATCH)
            )
        )
        latest = int(
            db.scalar(
                select(func.coalesce(func.max(CaseEvent.sequence), 0)).where(
                    CaseEvent.case_id == case_id
                )
            )
            or 0
        )
        for row in rows:
            db.expunge(row)
    return rows, latest, after


@router.get("/cases/{case_id}/events")
async def stream_events(
    case_id: UUID,
    request: Request,
    session: SignedIn,
    db: Database,
    last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
) -> StreamingResponse:
    owned_case(db, case_id, session.buyer_id)
    raw_cookie = request.cookies.get(SESSION_COOKIE, "")
    engine = request.app.state.engine
    try:
        cursor = int(last_event_id) if last_event_id else 0
    except ValueError:
        cursor = -1  # Unparseable cursor: ask the client to refetch current state.

    async def generate() -> AsyncIterator[str]:
        position = cursor
        _first, latest, _ = await run_in_threadpool(fetch_events, engine, case_id, 0)
        if position < 0 or position > latest:
            yield 'event: reset\ndata: {"reason": "cursor_not_replayable"}\n\n'
            position = latest
        last_check = last_beat = asyncio.get_event_loop().time()
        yield ": connected\n\n"
        while not await request.is_disconnected():
            now = asyncio.get_event_loop().time()
            if now - last_check >= REAUTHORIZE_SECONDS or position == cursor:
                if not await run_in_threadpool(still_authorized, engine, raw_cookie, case_id):
                    yield 'event: close\ndata: {"reason": "unauthorized"}\n\n'
                    return
                last_check = now
            events, _latest, _ = await run_in_threadpool(fetch_events, engine, case_id, position)
            if not events:
                if now - last_beat >= REAUTHORIZE_SECONDS:
                    yield ": heartbeat\n\n"
                    last_beat = now
                await asyncio.sleep(POLL_SECONDS)
                continue
            if not await run_in_threadpool(still_authorized, engine, raw_cookie, case_id):
                yield 'event: close\ndata: {"reason": "unauthorized"}\n\n'
                return
            for event in events:
                position = event.sequence
                yield frame(event)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )
