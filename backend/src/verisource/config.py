"""Validate local-free settings; read environment without creating records or loading models."""

import os
from pathlib import Path
from typing import Literal, Self
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

REPO_ROOT = Path(__file__).resolve().parents[3]


def disable_external_tracing() -> None:
    """The local profile must not inherit a global cloud telemetry configuration."""
    os.environ["LANGSMITH_TRACING"] = "false"
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    os.environ["OTEL_SDK_DISABLED"] = "true"


class Settings(BaseSettings):
    """Local-only boundaries; credentials remain redacted in repr/validation errors."""

    model_config = SettingsConfigDict(
        env_prefix="VERISOURCE_",
        env_file=REPO_ROOT / ".env",
        extra="ignore",
        hide_input_in_errors=True,
    )

    profile: Literal["local-free"] = "local-free"
    database_url: SecretStr = Field(
        default=SecretStr("postgresql+psycopg://verisource@127.0.0.1:55432/verisource"),
        repr=False,
    )
    data_root: Path = REPO_ROOT / ".local/data"
    ledger_root: Path = REPO_ROOT / ".local/deletion-ledger"
    snapshot_root: Path = REPO_ROOT / ".local/snapshots"
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3.5:4b"
    ollama_digest: str = ""
    paid_spend_limit: Literal[0] = 0
    model_concurrency: Literal[1] = 1
    model_context_tokens: Literal[4096] = 4096
    automatic_model_download: Literal[False] = False
    automatic_cloud_fallback: Literal[False] = False
    # Optional eligible Gemini free tier. Nothing is enabled until the operator records the
    # project's actual free-tier eligibility and limits; no allowance is ever assumed.
    gemini_api_key: SecretStr | None = Field(default=None, repr=False)
    gemini_model: str = ""
    gemini_free_tier_verified: bool = False
    gemini_requests_per_minute: int | None = None
    gemini_requests_per_day: int | None = None

    @field_validator("paid_spend_limit", "model_concurrency", "model_context_tokens", mode="before")
    @classmethod
    def parse_fixed_integer(cls, value: object) -> object:
        """Dotenv values are strings; literal validation still enforces the fixed bounds."""
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                return value
        return value

    @field_validator("automatic_model_download", "automatic_cloud_fallback", mode="before")
    @classmethod
    def parse_disabled_flag(cls, value: object) -> object:
        if isinstance(value, str) and value.lower() == "false":
            return False
        return value

    @field_validator("database_url")
    @classmethod
    def local_database(cls, value: SecretStr) -> SecretStr:
        try:
            parsed = make_url(value.get_secret_value())
            if (
                parsed.drivername != "postgresql+psycopg"
                or parsed.host not in {"127.0.0.1", "::1", "localhost"}
                or not parsed.database
                or parsed.query
            ):
                raise ValueError
        except ValueError, TypeError, ArgumentError:
            raise ValueError(
                "Use a loopback PostgreSQL psycopg URL without query overrides"
            ) from None
        return value

    @field_validator("ollama_url")
    @classmethod
    def local_model(cls, value: str) -> str:
        parsed = urlsplit(value)
        if (
            parsed.scheme != "http"
            or parsed.hostname not in {"127.0.0.1", "::1", "localhost"}
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/"}
        ):
            raise ValueError("Ollama must use a loopback HTTP origin")
        return value.rstrip("/")

    @field_validator("data_root", "ledger_root", "snapshot_root", mode="after")
    @classmethod
    def resolve_private_root(cls, value: Path) -> Path:
        resolved = (REPO_ROOT / value).resolve()
        if resolved.is_relative_to(REPO_ROOT / "frontend"):
            raise ValueError("Private storage must be outside frontend assets")
        return resolved

    @model_validator(mode="after")
    def separate_roots(self) -> Self:
        roots = (self.data_root, self.ledger_root, self.snapshot_root)
        for i, first in enumerate(roots):
            for second in roots[i + 1 :]:
                if first.is_relative_to(second) or second.is_relative_to(first):
                    raise ValueError("Data, deletion ledger and snapshots need disjoint roots")
        return self
