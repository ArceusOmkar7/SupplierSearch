"""Current session, CSRF, ownership and same-case authorization for all private routes."""

import secrets
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from verisource.db.base import Base
from verisource.db.models import BuyerAccount, Case, LoginSession
from verisource.security.sessions import SESSION_COOKIE, digest


def database(request: Request) -> Iterator[Session]:
    with Session(request.app.state.engine, expire_on_commit=False) as db, db.begin():
        yield db


Database = Annotated[Session, Depends(database, scope="function")]


def check_origin(request: Request, *, required: bool = True) -> None:
    origin = request.headers.get("Origin")
    expected = str(request.base_url).rstrip("/")
    api_origins = {f"http://{host}:8000" for host in ("127.0.0.1", "localhost", "[::1]")}
    if origin is None and not required:
        return
    # Vite forwards the API Host (:8000), while the browser's Origin remains :5173.
    frontend_origin = expected.removesuffix(":8000") + ":5173"
    if expected not in api_origins or origin not in (expected, frontend_origin):
        raise HTTPException(403)


def current_session(request: Request, db: Database) -> LoginSession:
    raw = request.cookies.get(SESSION_COOKIE, "")
    if not raw:
        raise HTTPException(401)
    session = db.scalar(
        select(LoginSession)
        .join(BuyerAccount)
        .where(LoginSession.id_hash == digest(raw), BuyerAccount.disabled_at.is_(None))
        .with_for_update(of=LoginSession)
    )
    now = datetime.now(UTC)
    if (
        session is None
        or session.revoked_at is not None
        or now >= session.expires_at
        or now - session.last_seen_at >= timedelta(minutes=30)
    ):
        raise HTTPException(401)
    session.last_seen_at = now
    return session


SignedIn = Annotated[LoginSession, Depends(current_session)]


def require_csrf(request: Request, session: SignedIn) -> LoginSession:
    check_origin(request)
    token = request.headers.get("X-CSRF-Token", "")
    if not token or not secrets.compare_digest(digest(token), digest(session.csrf_secret)):
        raise HTTPException(403)
    return session


MutationSession = Annotated[LoginSession, Depends(require_csrf)]


def owned_case(db: Session, case_id: UUID, buyer_id: UUID, *, lock: bool = False) -> Case:
    query = select(Case).where(
        Case.id == case_id, Case.owner_id == buyer_id, Case.state != "deleting"
    )
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    case = db.scalar(query)
    if case is None:
        raise HTTPException(404)
    return case


def same_case(reference_case: UUID, expected_case: UUID) -> None:
    if reference_case != expected_case:
        raise HTTPException(404)


def owned_child[Child: Base](
    db: Session, model: type[Child], child_id: UUID, *, case_id: UUID, buyer_id: UUID
) -> Child:
    owned_case(db, case_id, buyer_id)
    child = db.get(model, child_id)
    if child is None or getattr(child, "case_id", None) != case_id:
        raise HTTPException(404)
    return child
