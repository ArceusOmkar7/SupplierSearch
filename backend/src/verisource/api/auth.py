"""Local CSRF bootstrap, sign-in, session inspection and immediate logout revocation."""

from datetime import UTC, datetime

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, SecretStr

from verisource.api.dependencies import Database, MutationSession, SignedIn, check_origin
from verisource.db.models import BuyerAccount
from verisource.security.sessions import (
    BOOTSTRAP_COOKIE,
    SESSION_COOKIE,
    AuthenticationState,
    create_login,
    normalize_username,
    verify_credentials,
)

router = APIRouter(prefix="/api/v1")


class Credentials(BaseModel):
    username: str
    password: SecretStr


@router.get("/auth/csrf")
def csrf(request: Request, response: Response) -> dict[str, str]:
    check_origin(request, required=False)
    state: AuthenticationState = request.app.state.authentication
    cookie, token = state.bootstrap()
    response.set_cookie(
        BOOTSTRAP_COOKIE,
        cookie,
        max_age=600,
        httponly=True,
        samesite="lax",
        secure=False,
        path="/api/v1/auth",
    )
    return {"csrf_token": token}


@router.post("/auth/login")
def login(
    credentials: Credentials, request: Request, response: Response, db: Database
) -> dict[str, str]:
    check_origin(request)
    state: AuthenticationState = request.app.state.authentication
    state.consume(
        request.cookies.get(BOOTSTRAP_COOKIE, ""), request.headers.get("X-CSRF-Token", "")
    )
    state.throttle(
        normalize_username(credentials.username),
        request.client.host if request.client else "unknown",
    )
    buyer = verify_credentials(
        db, state, credentials.username, credentials.password.get_secret_value()
    )
    raw, session = create_login(db, buyer.id)
    response.set_cookie(
        SESSION_COOKIE,
        raw,
        max_age=28800,
        httponly=True,
        samesite="lax",
        secure=False,
        path="/api/v1",
    )
    response.delete_cookie(BOOTSTRAP_COOKIE, path="/api/v1/auth")
    return {
        "buyer_id": str(buyer.id),
        "display_name": buyer.display_name,
        "csrf_token": session.csrf_secret,
        "expires_at": session.expires_at.isoformat(),
    }


@router.get("/session")
def inspect_session(session: SignedIn, db: Database) -> dict[str, str]:
    buyer = db.get(BuyerAccount, session.buyer_id)
    assert buyer is not None
    return {
        "buyer_id": str(buyer.id),
        "display_name": buyer.display_name,
        "csrf_token": session.csrf_secret,
        "expires_at": session.expires_at.isoformat(),
    }


@router.post("/auth/logout", status_code=204)
def logout(session: MutationSession, response: Response) -> None:
    session.revoked_at = datetime.now(UTC)
    response.delete_cookie(SESSION_COOKIE, path="/api/v1")
