"""Local account and owner boundaries using real public-request case provenance."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from records import load_record
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session

from verisource.api.app import create_app
from verisource.config import Settings
from verisource.db.models import Case, LoginSession, RequirementRevision
from verisource.security.sessions import change_buyer_password, provision_buyer

pytestmark = [pytest.mark.integration, pytest.mark.real_records]
ORIGIN = "http://127.0.0.1:8000"


@pytest.fixture
def auth_setup(test_database_url: str) -> Iterator[tuple[Settings, str, str, str, UUID]]:
    engine = create_engine(test_database_url, hide_parameters=True)
    password = str(uuid4())  # Operator-provisioned test credential, never a source fact.
    first, second = f"owner-{uuid4()}", f"other-{uuid4()}"
    manifest, _content = load_record(Path(".local/records/bis-procurement.manifest.json"))
    with Session(engine) as db, db.begin():
        owner = provision_buyer(db, first.upper(), password, "Owner control")
        provision_buyer(db, second, password, "Other account control")
        db.flush()
        case = Case(owner_id=owner.id, title="Controlled access to actual BIS public request")
        db.add(case)
        db.flush()
        case_id = case.id
        db.add(
            RequirementRevision(
                case_id=case_id,
                sequence=1,
                requirements_json={"schema_version": 1, "source_sha256": manifest["sha256"]},
                location_json={"schema_version": 1},
                supplier_set_json=[],
                input_provenance={
                    "schema_version": 1,
                    "mode": "real_record_replay",
                    "original_url": manifest["original_url"],
                },
            )
        )
    settings = Settings.model_validate({"database_url": test_database_url})
    yield settings, first, second, password, case_id
    engine.dispose()


def login(client: TestClient, username: str, password: str) -> None:
    bootstrap = client.get("/api/v1/auth/csrf")
    assert bootstrap.status_code == 200
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
        headers={"Origin": ORIGIN, "X-CSRF-Token": bootstrap.json()["csrf_token"]},
    )
    assert response.status_code == 200


def test_signed_out_and_two_owner_case_boundaries(
    auth_setup: tuple[Settings, str, str, str, UUID],
) -> None:
    settings, first, second, password, case_id = auth_setup
    with TestClient(create_app(settings), base_url=ORIGIN) as client:
        assert client.get("/api/v1/session").status_code == 401

        assert client.get(f"/api/v1/cases/{case_id}").status_code == 401
        login(client, second, password)
        response = client.get(f"/api/v1/cases/{case_id}")
        assert response.status_code == 404
        assert "BIS" not in response.text
        login(client, first, password)
        owned = client.get(f"/api/v1/cases/{case_id}")
        assert owned.status_code == 200
        assert owned.headers["Cache-Control"] == "no-store"


def test_login_throttling_and_bootstrap_restart(
    auth_setup: tuple[Settings, str, str, str, UUID],
) -> None:
    settings, first, _second, password, _case = auth_setup
    with TestClient(create_app(settings), base_url=ORIGIN) as client:
        for _ in range(5):
            token = client.get("/api/v1/auth/csrf").json()["csrf_token"]
            result = client.post(
                "/api/v1/auth/login",
                json={"username": first, "password": "incorrect-control-password"},
                headers={"Origin": ORIGIN, "X-CSRF-Token": token},
            )
            assert result.status_code == 401
        token = client.get("/api/v1/auth/csrf").json()["csrf_token"]
        assert (
            client.post(
                "/api/v1/auth/login",
                json={"username": first, "password": password},
                headers={"Origin": ORIGIN, "X-CSRF-Token": token},
            ).status_code
            == 429
        )
    with TestClient(create_app(settings), base_url=ORIGIN) as client:
        login(client, first, password)
        cookie = client.cookies.get("verisource_session")
        assert cookie is not None
        token = client.get("/api/v1/auth/csrf").json()["csrf_token"]
        bootstrap = client.cookies.get("verisource_bootstrap")
        assert bootstrap is not None
    with TestClient(create_app(settings), base_url=ORIGIN) as restarted:
        restarted.cookies.set("verisource_session", cookie, domain="127.0.0.1", path="/api/v1")
        assert restarted.get("/api/v1/session").status_code == 200
        restarted.cookies.set(
            "verisource_bootstrap", bootstrap, domain="127.0.0.1", path="/api/v1/auth"
        )
        assert (
            restarted.post(
                "/api/v1/auth/login",
                json={"username": first, "password": password},
                headers={"Origin": ORIGIN, "X-CSRF-Token": token},
            ).status_code
            == 403
        )


def test_login_csrf_origin_and_generic_failures(
    auth_setup: tuple[Settings, str, str, str, UUID],
) -> None:
    settings, first, _second, password, _case = auth_setup
    with TestClient(create_app(settings), base_url=ORIGIN) as client:
        assert (
            client.post(
                "/api/v1/auth/login",
                json={"username": first, "password": password},
                headers={"Origin": ORIGIN},
            ).status_code
            == 403
        )
        token = client.get("/api/v1/auth/csrf").json()["csrf_token"]
        bad_origin = client.post(
            "/api/v1/auth/login",
            json={"username": first, "password": password},
            headers={"Origin": "https://untrusted.invalid", "X-CSRF-Token": token},
        )
        assert bad_origin.status_code == 403
        failures = []
        for username in (first, "unknown-control-account"):
            token = client.get("/api/v1/auth/csrf").json()["csrf_token"]
            result = client.post(
                "/api/v1/auth/login",
                json={"username": username, "password": "incorrect-control-password"},
                headers={"Origin": ORIGIN, "X-CSRF-Token": token},
            )
            assert result.status_code == 401
            failures.append(result.json()["error"]["message"])
        assert failures[0] == failures[1]
        assert (
            client.get("/api/v1/auth/csrf", headers={"Host": "untrusted.invalid"}).status_code
            == 400
        )


def test_login_from_local_frontend_proxy(
    auth_setup: tuple[Settings, str, str, str, UUID],
) -> None:
    settings, first, _second, password, _case = auth_setup
    with TestClient(create_app(settings), base_url=ORIGIN) as client:
        token = client.get("/api/v1/auth/csrf").json()["csrf_token"]
        response = client.post(
            "/api/v1/auth/login",
            json={"username": first, "password": password},
            headers={
                "Origin": "http://127.0.0.1:5173",
                "X-CSRF-Token": token,
            },
        )
        assert response.status_code == 200
        assert client.get("/api/v1/session").status_code == 200

        token = client.get("/api/v1/auth/csrf").json()["csrf_token"]
        wrong_loopback_host = client.post(
            "/api/v1/auth/login",
            json={"username": first, "password": password},
            headers={
                "Origin": "http://localhost:5173",
                "X-CSRF-Token": token,
            },
        )
        assert wrong_loopback_host.status_code == 403


def test_local_password_rotation_revokes_existing_sessions(
    auth_setup: tuple[Settings, str, str, str, UUID],
) -> None:
    settings, first, _second, password, _case = auth_setup
    replacement = str(uuid4())
    with TestClient(create_app(settings), base_url=ORIGIN) as client:
        login(client, first, password)
        engine = create_engine(settings.database_url.get_secret_value(), hide_parameters=True)
        try:
            with Session(engine) as db, db.begin():
                with pytest.raises(ValueError, match="at least 12"):
                    change_buyer_password(db, first, password, "short")
                with pytest.raises(ValueError, match="not accepted"):
                    change_buyer_password(db, first, "wrong-control", replacement)
                change_buyer_password(db, first, password, replacement)
        finally:
            engine.dispose()
        assert client.get("/api/v1/session").status_code == 401
        token = client.get("/api/v1/auth/csrf").json()["csrf_token"]
        assert (
            client.post(
                "/api/v1/auth/login",
                json={"username": first, "password": password},
                headers={"Origin": ORIGIN, "X-CSRF-Token": token},
            ).status_code
            == 401
        )
        login(client, first, replacement)


def test_logout_and_absolute_or_idle_expiry(
    auth_setup: tuple[Settings, str, str, str, UUID],
) -> None:
    settings, first, _second, password, _case = auth_setup
    with TestClient(create_app(settings), base_url=ORIGIN) as client:
        login(client, first, password)
        old_cookie = client.cookies.get("verisource_session")
        assert old_cookie is not None
        token = client.get("/api/v1/session").json()["csrf_token"]
        assert client.post("/api/v1/auth/logout", headers={"Origin": ORIGIN}).status_code == 403
        assert (
            client.post(
                "/api/v1/auth/logout", headers={"Origin": ORIGIN, "X-CSRF-Token": token}
            ).status_code
            == 204
        )
        client.cookies.set("verisource_session", old_cookie, domain="127.0.0.1", path="/api/v1")
        assert client.get("/api/v1/session").status_code == 401
        for expiry in ("idle", "absolute"):
            login(client, first, password)
            engine = create_engine(settings.database_url.get_secret_value(), hide_parameters=True)
            with Session(engine) as db, db.begin():
                session = db.scalars(
                    select(LoginSession)
                    .where(LoginSession.revoked_at.is_(None))
                    .order_by(LoginSession.created_at.desc())
                ).first()
                assert session is not None
                now = datetime.now(UTC)
                # Disclosed clock controls preserve valid timestamp ordering.
                session.created_at = now - timedelta(hours=9)
                session.last_seen_at = now - timedelta(minutes=31) if expiry == "idle" else now
                session.expires_at = (
                    now + timedelta(hours=1) if expiry == "idle" else now - timedelta(seconds=1)
                )
            engine.dispose()
            assert client.get("/api/v1/session").status_code == 401


def test_failed_commit_never_returns_success_cookie(
    auth_setup: tuple[Settings, str, str, str, UUID],
) -> None:
    settings, first, _second, password, _case = auth_setup
    app = create_app(settings)
    with TestClient(app, base_url=ORIGIN) as client:
        token = client.get("/api/v1/auth/csrf").json()["csrf_token"]

        def commit_fault(_connection: object) -> None:
            raise RuntimeError("Disclosed pre-commit failure control")

        event.listen(app.state.engine, "commit", commit_fault)
        try:
            result = client.post(
                "/api/v1/auth/login",
                json={"username": first, "password": password},
                headers={"Origin": ORIGIN, "X-CSRF-Token": token},
            )
        finally:
            event.remove(app.state.engine, "commit", commit_fault)
        assert result.status_code == 500
        assert "verisource_session=" not in result.headers.get("set-cookie", "")
