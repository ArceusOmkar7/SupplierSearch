"""Real known-supplier journey: API, worker and browser against actual sources.

Suppliers are actual rows of the historical BIS IS 9473 licence list. A supplier's website is
the company domain of the contact email printed in that official record; it is an unverified
buyer-supplied identifier, so website evidence stays supplier self-report with proposed
identity. Live retrieval of third-party sites is performed (robots respected); nothing is
simulated. Results, including code failures versus source gaps, go to
.local/acceptance/core002/us1/. The requirement text is operator-written for this licence list
(the acquired public tender concerns unrelated test equipment); it is not a genuine buyer
request, which remains an outstanding prerequisite for SC-002.
"""

import json
import os
import subprocess
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from support import RECORDS, licence_rows

from verisource.config import REPO_ROOT, Settings
from verisource.country_packs.india.bis import ingest_qco_catalog
from verisource.db.checkpoints import checkpointer
from verisource.db.models import (
    Assessment,
    CheckAttempt,
    CheckTask,
    EvidenceRecord,
    IdentityResolution,
    VerificationRun,
)
from verisource.sources.imports import import_source_dataset
from verisource.storage.filesystem import PrivateFileStore

pytestmark = [pytest.mark.integration, pytest.mark.real_records, pytest.mark.live]
OUT = REPO_ROOT / ".local/acceptance/core002/us1"
CANDIDATE_LICENCES = ["8300137209", "6500040196", "9100142099", "7800062417"]  # listed in the PDF


def wait_for(url: str, seconds: int = 60) -> None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            if httpx.get(url, timeout=2).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.5)
    raise AssertionError(f"{url} did not start")


def test_known_supplier_journey_in_a_real_browser(
    buyer_pair: tuple[Settings, str, str, str], tmp_path: Path
) -> None:
    settings, username, _other, password = buyer_pair
    for port in (8000, 5173):
        try:
            httpx.get(f"http://127.0.0.1:{port}/", timeout=1)
        except httpx.HTTPError:
            continue
        pytest.skip(f"Missing prerequisite: port {port} is in use; stop the local stack first")
    by_licence = {row.licence_no: row for row in licence_rows()}
    chosen = [by_licence[number] for number in CANDIDATE_LICENCES if number in by_licence]
    assert len(chosen) == 4 and all(row.contact_domain for row in chosen)
    suppliers = [
        {
            "name": row.firm_name,
            "website": f"https://www.{row.contact_domain}/",
            "licence": row.licence_no,
            "address": row.factory_address,
        }
        for row in chosen
    ]
    engine = create_engine(settings.database_url.get_secret_value(), hide_parameters=True)
    with checkpointer(settings, initialize=True):
        pass
    store = PrivateFileStore(settings.data_root / "corpus")
    with Session(engine) as db, db.begin():
        import_source_dataset(db, store, RECORDS / "bis-licences.manifest.json")
        ingest_qco_catalog(db, store, RECORDS / "bis-qco-scheme1.manifest.json")
    environment = {
        **os.environ,
        "VERISOURCE_DATABASE_URL": settings.database_url.get_secret_value(),
        "VERISOURCE_DATA_ROOT": str(settings.data_root),
        "PYTHONUTF8": "1",
    }
    OUT.mkdir(parents=True, exist_ok=True)
    api_log = (OUT / "api.log").open("w", encoding="utf-8")
    worker_log = (OUT / "worker.log").open("w", encoding="utf-8")
    api = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "verisource.api.app:app", "--host", "127.0.0.1", "--port", "8000"],
        env=environment, cwd=REPO_ROOT, stdout=api_log, stderr=subprocess.STDOUT,
    )  # fmt: skip
    worker = subprocess.Popen(
        [sys.executable, "-m", "verisource.orchestration.worker"],
        env=environment, cwd=REPO_ROOT, stdout=worker_log, stderr=subprocess.STDOUT,
    )  # fmt: skip
    started = datetime.now(UTC)
    try:
        wait_for("http://127.0.0.1:8000/health/live")
        npx = "npx.cmd" if os.name == "nt" else "npx"
        spec = subprocess.run(
            [npx, "playwright", "test", "verify_known_suppliers.spec.ts", "--reporter=line"],
            cwd=REPO_ROOT / "frontend",
            env={
                **environment,
                "NODE_PATH": str(REPO_ROOT / "frontend/node_modules"),
                "E2E_SUPPLIERS": json.dumps(suppliers),
                "E2E_USERNAME": username,
                "E2E_PASSWORD": password,
                "E2E_OUTPUT": str(OUT),
            },
            capture_output=True, text=True, timeout=30 * 60, check=False,
        )  # fmt: skip
    finally:
        for process in (worker, api):
            process.terminate()
        for process in (worker, api):
            try:
                process.wait(20)
            except subprocess.TimeoutExpired:
                process.kill()
        api_log.close()
        worker_log.close()
    (OUT / "playwright.out.txt").write_text(spec.stdout + "\n" + spec.stderr, encoding="utf-8")

    with Session(engine) as db:
        run = db.scalars(select(VerificationRun)).first()
        summary: dict[str, object] = {
            "executed_at": started.isoformat(),
            "mode": "live retrieval of third-party sites; official exports imported from actual captures",
            "suppliers": [
                {k: v for k, v in s.items() if k != "address"}
                | {
                    "website_origin": "contact-email domain in the official record; identity unverified"
                }
                for s in suppliers
            ],
            "ui_spec_exit_code": spec.returncode,
            "run_state": run.state if run else None,
        }
        if run:
            attempts = list(db.scalars(select(CheckAttempt).where(CheckAttempt.run_id == run.id)))
            summary |= {
                "task_states": dict(
                    Counter(db.scalars(select(CheckTask.state).where(CheckTask.run_id == run.id)))
                ),
                "attempt_outcomes": dict(Counter(f"{a.outcome}/{a.reason_code}" for a in attempts)),
                "dispatched_requests": sum(a.request_dispatched for a in attempts),
                "evidence_records": db.scalar(select(func.count()).select_from(EvidenceRecord)),
                "evidence_by_authority": dict(
                    Counter(db.scalars(select(EvidenceRecord.authority_role)))
                ),
                "identity_states": dict(Counter(db.scalars(select(IdentityResolution.state)))),
                "assessment_verdicts": dict(Counter(db.scalars(select(Assessment.verdict)))),
                "run_seconds": (run.completed_at - run.started_at).total_seconds()
                if run.completed_at and run.started_at
                else None,
            }
    engine.dispose()
    (OUT / "us1-real-run.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8"
    )
    assert spec.returncode == 0, spec.stdout[-3000:] + spec.stderr[-1500:]
    assert summary["run_state"] in {"completed", "completed_with_gaps"}
    assert summary["assessment_verdicts"]  # Verdicts are recorded as found, not expected.
