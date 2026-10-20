"""Opaque hashed sessions and short-lived bootstrap challenges; no tokens in logs."""

import hashlib
import secrets
import threading
import time
import unicodedata
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from verisource.db.models.identity import BuyerAccount, LoginSession

SESSION_COOKIE = "verisource_session"
BOOTSTRAP_COOKIE = "verisource_bootstrap"
PASSWORD_HASH = PasswordHash.recommended()


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_username(value: str) -> str:
    return unicodedata.normalize("NFKC", value).strip().casefold()


class AuthenticationState:
    """Bounded process-local challenges/throttles are never part of a restored snapshot."""

    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.challenges: dict[str, tuple[str, float]] = {}
        self.failures: dict[str, tuple[int, float]] = {}
        self.dummy_hash = PASSWORD_HASH.hash(secrets.token_urlsafe(32))

    def bootstrap(self) -> tuple[str, str]:
        now = time.monotonic()
        cookie, token = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        with self.lock:
            self.challenges = {k: v for k, v in self.challenges.items() if v[1] > now}
            if len(self.challenges) >= 1024:
                raise HTTPException(429)
            self.challenges[digest(cookie)] = (digest(token), now + 600)
        return cookie, token

    def consume(self, cookie: str, token: str) -> None:
        with self.lock:
            challenge = self.challenges.pop(digest(cookie), None)
        if (
            not cookie
            or not token
            or challenge is None
            or challenge[1] <= time.monotonic()
            or not secrets.compare_digest(challenge[0], digest(token))
        ):
            raise HTTPException(403)

    def throttle(self, username: str, peer: str) -> None:
        now = time.monotonic()
        with self.lock:
            self.failures = {k: v for k, v in self.failures.items() if v[1] > now}
            if len(self.failures) > 4096:
                raise HTTPException(429)
            for key, limit in (("user:" + digest(username), 5), ("peer:" + digest(peer), 30)):
                count, expires = self.failures.get(key, (0, now + 300))
                if count >= limit:
                    raise HTTPException(429)
                self.failures[key] = (count + 1, expires)


def provision_buyer(db: Session, username: str, password: str, display_name: str) -> BuyerAccount:
    normalized = normalize_username(username)
    if not normalized or not password or not display_name.strip():
        raise ValueError("Username, password and display name are required")
    if len(password) < 12:
        raise ValueError("Password must be at least 12 characters")
    buyer = BuyerAccount(
        username_normalized=normalized,
        password_hash=PASSWORD_HASH.hash(password),
        display_name=display_name.strip(),
    )
    db.add(buyer)
    db.flush()
    return buyer


def change_buyer_password(
    db: Session, username: str, current_password: str, new_password: str
) -> None:
    """Rotate a locally provisioned password and revoke all of its login sessions."""
    if len(new_password) < 12:
        raise ValueError("New password must be at least 12 characters")
    buyer = db.scalar(
        select(BuyerAccount)
        .where(BuyerAccount.username_normalized == normalize_username(username))
        .with_for_update()
    )
    encoded = buyer.password_hash if buyer else PASSWORD_HASH.hash(secrets.token_urlsafe(32))
    try:
        valid = PASSWORD_HASH.verify(current_password, encoded)
    except ValueError, UnknownHashError:
        valid = False
    if not valid or buyer is None or buyer.disabled_at is not None:
        raise ValueError("Current credentials were not accepted")
    buyer.password_hash = PASSWORD_HASH.hash(new_password)
    db.execute(
        update(LoginSession)
        .where(LoginSession.buyer_id == buyer.id, LoginSession.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )


def create_login(db: Session, buyer_id: UUID) -> tuple[str, LoginSession]:
    raw = secrets.token_urlsafe(32)
    now = datetime.now(UTC)
    session = LoginSession(
        id_hash=digest(raw),
        buyer_id=buyer_id,
        created_at=now,
        last_seen_at=now,
        expires_at=now + timedelta(hours=8),
        csrf_secret=secrets.token_urlsafe(32),
    )
    db.add(session)
    db.flush()
    return raw, session


def verify_credentials(
    db: Session, state: AuthenticationState, username: str, password: str
) -> BuyerAccount:
    buyer = db.scalar(
        select(BuyerAccount).where(BuyerAccount.username_normalized == normalize_username(username))
    )
    encoded = buyer.password_hash if buyer else state.dummy_hash
    try:
        valid = PASSWORD_HASH.verify(password, encoded)
    except ValueError, UnknownHashError:
        valid = False
    if not valid or buyer is None or buyer.disabled_at is not None:
        raise HTTPException(401)
    return buyer
