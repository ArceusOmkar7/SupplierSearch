"""Local setup refuses lost-ledger replacement over genuine retained case state."""

from pathlib import Path
from uuid import UUID

import pytest
from test_local_auth import auth_setup as auth_setup_fixture

from verisource.config import Settings
from verisource.operations.preflight import setup_local

auth_setup = auth_setup_fixture
pytestmark = [pytest.mark.integration, pytest.mark.real_records]


def test_existing_case_without_current_ledger_fails_closed(
    auth_setup: tuple[Settings, str, str, str, UUID],
    tmp_path: Path,
) -> None:
    settings, _first, _second, _password, _case_id = auth_setup
    isolated = Settings.model_validate(
        {
            "database_url": settings.database_url,
            "data_root": tmp_path / "data",
            "ledger_root": tmp_path / "ledger",
            "snapshot_root": tmp_path / "snapshots",
        }
    )
    with pytest.raises(ValueError, match="current deletion ledger"):
        setup_local(isolated)
    assert not isolated.ledger_root.exists()
