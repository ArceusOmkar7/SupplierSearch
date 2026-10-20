"""API metadata/error boundaries without fabricated case or source responses."""

from uuid import UUID

from fastapi.testclient import TestClient

from verisource.api.app import create_app
from verisource.config import Settings

app = create_app(Settings.model_validate({"ollama_digest": ""}))


def test_live_is_not_premature_readiness() -> None:
    with TestClient(app, base_url="http://127.0.0.1") as client:
        live = client.get("/health/live", headers={"X-Request-ID": "untrusted-control-input"})
        assert live.status_code == 200
        assert UUID(live.headers["X-Request-ID"])
        assert live.headers["Cache-Control"] == "no-store"
        assert client.get("/health/ready").status_code == 503


def test_unknown_reference_has_generic_error() -> None:
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.get("/unknown-control-reference")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"
        assert "unknown-control-reference" not in response.text
        assert "postgres" not in response.text


def test_internal_error_does_not_escape_the_redacted_boundary() -> None:
    control_app = create_app(Settings.model_validate({"ollama_digest": ""}))

    @control_app.get("/disclosed-fault-control")
    def fail() -> None:
        raise RuntimeError("confidential-control-string")

    with TestClient(control_app, base_url="http://127.0.0.1") as client:
        response = client.get("/disclosed-fault-control")
        assert response.status_code == 500
        assert "confidential-control-string" not in response.text
        assert response.json()["error"]["request_id"]
