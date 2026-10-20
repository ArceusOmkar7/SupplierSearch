"""Check actual local prerequisites without paid keys, downloads or source-truth claims."""

import json
import os
import shutil
from pathlib import Path
from uuid import UUID, uuid4

import httpx
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from verisource.config import REPO_ROOT, Settings
from verisource.db.checkpoints import checkpointer
from verisource.db.models import Case
from verisource.db.session import create_database_engine
from verisource.storage.deletion_ledger import DeletionLedger, LedgerUnavailable
from verisource.storage.filesystem import PrivateFileStore


def migration_config(settings: Settings) -> Config:
    config = Config(str(REPO_ROOT / "backend/alembic.ini"))
    config.attributes["settings"] = settings
    return config


def ledger_valid(path: Path) -> bool:
    try:
        DeletionLedger(path).verify()
        return True
    except LedgerUnavailable:
        return False


def _legacy_ledger_valid(path: Path) -> bool:
    try:
        with path.open(encoding="utf-8") as stream:
            header = json.loads(stream.readline())
        return bool(
            header["type"] == "ledger_initialized"
            and header["schema_version"] == 1
            and str(UUID(header["installation_id"])) == header["installation_id"]
        )
    except OSError, ValueError, KeyError, TypeError:
        return False


def setup_local(settings: Settings) -> None:
    engine = create_database_engine(settings)
    try:
        command.upgrade(migration_config(settings), "head")
        ledger = settings.ledger_root / "deletions.jsonl"
        with Session(engine) as db:
            count = int(db.scalar(select(func.count()).select_from(Case)) or 0)
        if not ledger.exists():
            if count or (settings.data_root.exists() and any(settings.data_root.iterdir())):
                raise ValueError("Existing case state requires its current deletion ledger")
            DeletionLedger.initialize(ledger, str(uuid4()))
        if not ledger_valid(ledger):
            raise ValueError("Deletion ledger is missing or inconsistent")
        PrivateFileStore(settings.data_root)
        settings.snapshot_root.mkdir(parents=True, exist_ok=True)
        with checkpointer(settings, initialize=True):
            pass
    finally:
        engine.dispose()


def preflight(settings: Settings) -> dict[str, object]:
    checks = {
        "zero_paid_spend": settings.paid_spend_limit == 0,
        "database": False,
        "checkpointer": False,
        "private_files": False,
        "deletion_ledger": ledger_valid(settings.ledger_root / "deletions.jsonl"),
        "model": False,
    }
    engine = create_database_engine(settings)
    try:
        with engine.connect() as connection:
            head = ScriptDirectory.from_config(migration_config(settings)).get_current_head()
            checks["database"] = (
                connection.scalar(text("SELECT version_num FROM alembic_version")) == head
            )
            checks["checkpointer"] = bool(
                connection.scalar(text("SELECT to_regclass('checkpoints.checkpoints') IS NOT NULL"))
            )
    except SQLAlchemyError:
        pass
    finally:
        engine.dispose()
    try:
        root = settings.data_root
        PrivateFileStore._reject_links(root)
        checks["private_files"] = root.is_dir() and os.access(root, os.R_OK | os.W_OK)
    except OSError, ValueError:
        pass
    try:
        expected = settings.ollama_digest.removeprefix("sha256:").lower()
        if len(expected) == 64 and all(c in "0123456789abcdef" for c in expected):
            with httpx.Client(timeout=3, follow_redirects=False, trust_env=False) as client:
                response = client.get(f"{settings.ollama_url}/api/tags")
                response.raise_for_status()
                models = response.json()["models"]
            checks["model"] = any(
                m.get("name") == settings.ollama_model
                and m.get("digest", "").removeprefix("sha256:").lower() == expected
                for m in models
            )
    except httpx.HTTPError, ValueError, KeyError, TypeError:
        pass
    from verisource.country_packs.registry import pack_for, supported_jurisdictions
    from verisource.models.gemini_free import GeminiFree

    pack = pack_for("IN")
    return {
        "profile": "local-free",
        "ready": all(checks.values()),
        "sources": [
            {
                "source_id": c.source_id,
                "enabled": c.enabled,
                "claims": list(c.claim_types),
                "disabled_reason": c.disabled_reason,
            }
            for c in pack.capabilities()
        ],
        "jurisdictions": supported_jurisdictions(),
        "gemini_free_tier": {
            "configured": GeminiFree(settings).configured,
            "note": "Optional; public business text only. No allowance is assumed.",
        },
        "checks": checks,
        "optional": {"tesseract_on_path": shutil.which("tesseract") is not None},
        "model_download_attempted": False,
        "paid_dispatch_enabled": False,
    }
