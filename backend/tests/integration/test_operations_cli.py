"""Operator CLI (import-source, capture-source, preflight) and free-quota reservations."""

import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from support import RECORDS, licence_rows
from test_verification_schema import build

from verisource.config import REPO_ROOT, Settings
from verisource.sources.quotas import reserve, settle

pytestmark = [pytest.mark.integration, pytest.mark.real_records]


def run_cli(settings: Settings, tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "VERISOURCE_DATABASE_URL": settings.database_url.get_secret_value(),
        "VERISOURCE_DATA_ROOT": str(tmp_path / "cli-data"),
        "PYTHONUTF8": "1",
    }
    return subprocess.run(
        [sys.executable, "-m", "verisource.operations.cli", *args],
        capture_output=True, text=True, cwd=REPO_ROOT, env=env, timeout=240, check=False,
    )  # fmt: skip


def test_import_source_cli_reports_actual_counts_and_refuses_bad_input(
    buyer_pair: tuple[Settings, str, str, str], tmp_path: Path
) -> None:
    settings, *_ = buyer_pair
    done = run_cli(settings, tmp_path, "import-source", str(RECORDS / "bis-licences.manifest.json"))
    assert done.returncode == 0, done.stderr
    summary = json.loads(done.stdout)
    assert summary["imported"] == len(licence_rows()) and summary["quarantined"] == 0
    assert summary["publication_cutoff"].startswith("2020-08-27")
    # A missing capture is an error, never a seeded replacement.
    missing = run_cli(settings, tmp_path, "import-source", str(RECORDS / "absent.manifest.json"))
    assert missing.returncode != 0 or "imported" not in missing.stdout


def test_capture_source_cli_refuses_internal_targets(
    buyer_pair: tuple[Settings, str, str, str], tmp_path: Path
) -> None:
    settings, *_ = buyer_pair
    refused = run_cli(
        settings, tmp_path, "capture-source", "http://127.0.0.1:11434/api/tags",
        "--name", "cli-refusal-control", "--kind", "supplier", "--publisher", "control",
        "--rights", "control", "--attribution", "control", "--coverage", "IN",
    )  # fmt: skip
    assert refused.returncode == 1 and "Capture refused" in refused.stdout
    assert not list((REPO_ROOT / ".local/records").glob("cli-refusal-control*"))


def test_free_quota_reservations_are_atomic_idempotent_and_limit_aware(
    test_database_url: str,
) -> None:
    engine = create_engine(test_database_url, hide_parameters=True)
    with Session(engine) as db, db.begin():
        _a, case, _rev, _s, _cl, _c, run, _t = build(db)
        one = reserve(db, case_id=case.id, run_id=run.id, consumer="verification", unit="requests",
                      amount=3, operation_key=f"k:{uuid4()}", cycle="day", limit=5)  # fmt: skip
        assert one is not None
        key = f"k:{uuid4()}"
        two = reserve(db, case_id=case.id, run_id=run.id, consumer="verification", unit="requests",
                      amount=2, operation_key=key, cycle="day", limit=5)  # fmt: skip
        assert two is not None
        # The project allowance is exhausted: no further reservation and no invented headroom.
        assert reserve(db, case_id=case.id, run_id=run.id, consumer="verification", unit="requests",
                       amount=1, operation_key=f"k:{uuid4()}", cycle="day", limit=5) is None  # fmt: skip
        assert reserve(db, case_id=case.id, run_id=run.id, consumer="verification", unit="requests",
                       amount=2, operation_key=key, cycle="day", limit=5) is two  # idempotent  # fmt: skip
        settle(two, 1)
        assert two.state == "settled" and two.settled_amount == 1
    engine.dispose()


def test_evaluate_cli_persists_a_dated_unmeasured_result_for_missing_real_inputs(
    buyer_pair: tuple[Settings, str, str, str], tmp_path: Path
) -> None:
    from datetime import UTC, datetime
    from uuid import uuid4

    settings, *_ = buyer_pair
    rows = licence_rows()[:5]
    manifest = {
        "schema_version": 1,
        "dataset": {
            "name": "actual licence-list suppliers; no labels or timings exist yet",
            "created_at": datetime.now(UTC).isoformat(),
            "suppliers_expected": 30,
            "cases_expected": 6,
            "suppliers_per_case": 5,
        },
        "auditors": [],
        "suppliers": [
            {"supplier_ref": r.licence_no, "case_ref": "case-1", "case_id": str(uuid4()),
             "supplier_id": str(uuid4()), "source_records": ["bis-licences.manifest.json"]}
            for r in rows
        ],
        "labels": [],
        "timings": [],
    }  # fmt: skip
    path = tmp_path / "audit.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    out = tmp_path / "results"
    done = run_cli(
        settings, tmp_path, "evaluate", "--manifest", str(path), "--profile", "local-free",
        "--output", str(out),
    )  # fmt: skip
    assert done.returncode == 2  # not all criteria passed
    assert "SC-002: unmeasured" in done.stdout and "SC-003: unmeasured" in done.stdout
    written = list(out.glob("evaluation-*.json"))
    assert len(written) == 1
    result = json.loads(written[0].read_text(encoding="utf-8"))
    assert {r["status"] for r in result["results"]} == {"unmeasured"}
