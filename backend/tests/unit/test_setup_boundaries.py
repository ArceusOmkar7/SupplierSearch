"""Observable configuration/test safety boundaries; no fabricated supplier/source data."""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from conftest import validate_test_database_url
from pydantic import ValidationError

from verisource.config import Settings


@pytest.fixture(autouse=True)
def isolated_settings_environment(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Negative control inputs never load the operator's private .env settings."""
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    for name in tuple(os.environ):
        if name.startswith("VERISOURCE_"):
            monkeypatch.delenv(name)
    yield


@pytest.mark.parametrize(
    "overrides",
    [
        {"paid_spend_limit": 1},
        {"automatic_model_download": True},
        {"automatic_cloud_fallback": True},
        {"ollama_url": "http://192.168.1.1:11434"},
        {"ollama_url": "http://127.0.0.1:11434/?host=external"},
        {"database_url": "postgresql+psycopg://buyer@external/db"},
        {"database_url": "postgresql+psycopg://buyer@127.0.0.1/db?host=external"},
        {"data_root": Path("frontend/public/private")},
        {"ledger_root": Path(".local/data/ledger")},
        {"snapshot_root": Path(".local/data")},
    ],
)
def test_unsafe_local_configuration_rejected(overrides: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        Settings.model_validate(overrides)


def test_safe_local_defaults() -> None:
    settings = Settings.model_validate({})
    assert settings.paid_spend_limit == 0
    assert settings.model_concurrency == 1
    assert settings.automatic_cloud_fallback is False
    assert not settings.ledger_root.is_relative_to(settings.snapshot_root)


def test_documented_dotenv_settings_load(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text(
        "VERISOURCE_PAID_SPEND_LIMIT=0\n"
        "VERISOURCE_MODEL_CONCURRENCY=1\n"
        "VERISOURCE_MODEL_CONTEXT_TOKENS=4096\n"
        "VERISOURCE_AUTOMATIC_CLOUD_FALLBACK=false\n",
        encoding="utf-8",
    )
    monkeypatch.setitem(Settings.model_config, "env_file", dotenv)
    settings = Settings.model_validate({})
    assert settings.paid_spend_limit == 0
    assert settings.model_context_tokens == 4096
    assert settings.automatic_cloud_fallback is False


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+psycopg://local@127.0.0.1/verisource",
        "postgresql+psycopg://local@external/verisource_test_safe",
        "postgresql+psycopg://local@127.0.0.1/verisource_test_safe?host=external",
        "sqlite:///verisource_test_safe",
    ],
)
def test_database_guard_rejects_unsafe_targets(url: str) -> None:
    with pytest.raises(ValueError):
        validate_test_database_url(url)


def test_database_guard_rejects_live_even_if_test_named() -> None:
    url = "postgresql+psycopg://local@127.0.0.1/verisource_test_safe"
    with pytest.raises(ValueError):
        validate_test_database_url(url, url)
    assert validate_test_database_url(url) == url
