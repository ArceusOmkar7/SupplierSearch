"""US1 collection, local import and document boundaries using actual captured records.

Real inputs: the BIS IS 9473 licence PDF (cutoff 27 Aug 2020), the BIS procurement PDF,
the BIS robots.txt and the recorded outcome of the BIS QCO catalog attempt whose response
body was truncated. No HTTP, provider or certificate content is generated. Destination and
state-transition controls are labeled below. Absent natural samples (a password-locked or
scanned certificate, a CAPTCHA response) are reported as skipped prerequisites, never
substituted.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from records import load_record
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from support import ORIGIN, RECORDS, Api, admitted_run, licence_rows

from verisource.api.app import create_app
from verisource.config import Settings
from verisource.db.models import CheckAttempt, CheckTask, EvidenceRecord, VerificationRun
from verisource.documents.certificates import inspect_pdf
from verisource.domain.attempts import record_attempt
from verisource.domain.runnable import runnable_tasks
from verisource.security.egress import EgressDenied, validate_destination
from verisource.sources.imports import import_source_dataset, lookup_exact
from verisource.sources.policy import robots_decision
from verisource.storage.filesystem import PrivateFileStore

pytestmark = [pytest.mark.integration, pytest.mark.real_records]


@pytest.fixture
def stack(buyer_pair: tuple[Settings, str, str, str]):  # type: ignore[no-untyped-def]
    settings, first, _second, password = buyer_pair
    engine = create_engine(settings.database_url.get_secret_value(), hide_parameters=True)
    with TestClient(create_app(settings), base_url=ORIGIN) as client:
        yield settings, engine, Api(client, first, password)
    engine.dispose()


def test_actual_licence_pdf_imports_with_original_cutoff_and_exact_lookup(
    stack: tuple[Settings, Any, Api],
) -> None:
    settings, engine, _api = stack
    expected = licence_rows()
    store = PrivateFileStore(settings.data_root / "corpus")
    with Session(engine) as db, db.begin():
        result = import_source_dataset(db, store, RECORDS / "bis-licences.manifest.json")
        assert result.imported == len(expected) and result.quarantined == 0
        row = expected[2]
        matches = lookup_exact(db, identifier_type="licence_number", value=row.licence_no)
        assert [m.fields["firm_name"] for m in matches] == [row.firm_name]
        match = matches[0]
        assert match.locator.startswith("page 1")
        # The historical cutoff governs the claim; importing today does not refresh it.
        assert match.publication_cutoff == datetime(2020, 8, 27, tzinfo=UTC)
        assert match.obtained_at > match.publication_cutoff
        assert match.historical is True
        # Absence of a record is no_record, never proof that a firm does not exist.
        assert lookup_exact(db, identifier_type="licence_number", value="0000000") == []


def test_import_rejects_bytes_that_do_not_match_the_capture_hash(
    stack: tuple[Settings, Any, Api], tmp_path: Path
) -> None:
    settings, engine, _api = stack
    manifest, content = load_record(RECORDS / "bis-licences.manifest.json")
    root = tmp_path / "records"
    root.mkdir()
    (root / "licences.manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    # Controlled corruption of genuine bytes to prove the integrity gate; not source data.
    (root / manifest["file"]).write_bytes(content[:-1] + b"\x00")
    store = PrivateFileStore(settings.data_root / "corpus")
    with Session(engine) as db, db.begin(), pytest.raises(ValueError, match="hash"):
        import_source_dataset(db, store, root / "licences.manifest.json", records_root=root)


def test_destination_guard_blocks_internal_and_credentialed_targets() -> None:
    public = lambda host: ["93.184.216.34"]
    validate_destination("https://www.bis.gov.in/copyright-policy/", resolver=public)
    # Attack/control conditions: none of these is a source fact.
    for url in (
        "http://127.0.0.1:11434/api/tags",
        "http://localhost/",
        "http://169.254.169.254/latest/meta-data/",
        "http://[::1]/",
        "http://10.0.0.7/admin",
        "file:///C:/Windows/win.ini",
        "https://user:secret@example.org/",
        "ftp://example.org/file",
    ):
        with pytest.raises(EgressDenied):
            validate_destination(url, resolver=public)
    with pytest.raises(EgressDenied):  # public name resolving to an internal address
        validate_destination("https://rebinding.example/", resolver=lambda host: ["10.1.2.3"])


def test_actual_bis_robots_policy_and_unavailable_policy_are_distinguished() -> None:
    robots = (RECORDS / "bis-robots.txt").read_text(encoding="utf-8")
    base = "https://bis.gov.in"
    allowed = robots_decision(robots, 200, f"{base}/copyright-policy/?lang=en")
    denied = robots_decision(robots, 200, f"{base}/wp-admin/options.php")
    assert allowed.allowed and not denied.allowed
    # The first actual robots attempt returned HTTP 302 without usable directives.
    unknown = robots_decision(None, 302, f"{base}/copyright-policy/")
    assert not unknown.allowed and unknown.reason_code == "permission_unverified"
    # Robots allowance is separate from reuse rights.
    assert allowed.reuse_rights_established is False


def test_pdf_inspection_enforces_actual_page_limit_and_reads_text() -> None:
    licence = inspect_pdf((RECORDS / "bis-licences.pdf").read_bytes())
    assert licence.failure_reason is None and licence.page_count == 1
    assert licence.text_pages == [1] and licence.scanned_pages == []
    tender = inspect_pdf((RECORDS / "bis-procurement.pdf").read_bytes())
    assert tender.page_count == 58 and tender.failure_reason == "too_large"
    assert inspect_pdf(b"%PDF-1.4 truncated").failure_reason == "malformed_document"


def test_natural_locked_and_scanned_certificates_are_missing_prerequisites() -> None:
    locked = list(RECORDS.glob("*locked*.manifest.json"))
    scanned = list(RECORDS.glob("*scanned*.manifest.json"))
    if not locked or not scanned:
        pytest.skip(
            "Missing genuine locked/scanned certificate captures; recorded as unmeasured, "
            "never replaced by generated files"
        )
    for manifest_path in locked:
        _manifest, content = load_record(manifest_path)
        assert inspect_pdf(content).failure_reason == "locked_document"


def _tasks(engine: Any, run_id: str) -> list[CheckTask]:
    with Session(engine) as db:
        return list(db.scalars(select(CheckTask).where(CheckTask.run_id == UUID(run_id))))


def test_attempts_preserve_actual_dispatch_and_never_become_evidence(
    stack: tuple[Settings, Any, Api],
) -> None:
    _settings, engine, api = stack
    run = admitted_run(api)
    attempts = [
        entry
        for path in RECORDS.glob("acquisition-*.json")
        for entry in json.loads(path.read_text(encoding="utf-8"))
        if "peer closed connection" in entry.get("reason", "")
    ]
    assert attempts, "The actual truncated QCO catalog attempt is a required record"
    actual = attempts[0]
    with Session(engine) as db, db.begin():
        task = db.scalars(select(CheckTask).where(CheckTask.run_id == UUID(run["run_id"]))).first()
        assert task is not None
        stored = record_attempt(
            db,
            task=task,
            kind="remote_request",
            target=actual["url"],
            requested_at=datetime.fromisoformat(actual["at"]),
            request_dispatched=True,
            outcome="unavailable",
            reason_code=None,
        )
        assert stored.http_status is None and stored.artifact_refs == []
        skipped = record_attempt(
            db,
            task=task,
            kind="capability_check",
            target="source:not-configured",
            requested_at=datetime.now(UTC),
            request_dispatched=False,
            outcome="skipped",
            reason_code="not_configured",
        )
        assert skipped.request_dispatched is False
        with pytest.raises(ValueError):  # a local skip cannot claim a network dispatch
            record_attempt(
                db,
                task=task,
                kind="capability_check",
                target="source:not-configured",
                requested_at=datetime.now(UTC),
                request_dispatched=True,
                outcome="skipped",
                reason_code="not_configured",
            )
        with pytest.raises(ValueError):  # blocked/skipped outcomes must state why
            record_attempt(
                db,
                task=task,
                kind="remote_request",
                target=actual["url"],
                requested_at=datetime.now(UTC),
                request_dispatched=True,
                outcome="blocked",
                reason_code=None,
            )
        assert db.scalars(select(EvidenceRecord)).first() is None


def test_waiting_document_task_blocks_only_its_dependents(
    stack: tuple[Settings, Any, Api],
) -> None:
    _settings, engine, api = stack
    run = admitted_run(api, count=2)
    with Session(engine) as db, db.begin():
        tasks = list(db.scalars(select(CheckTask).where(CheckTask.run_id == UUID(run["run_id"]))))
        by_supplier: dict[UUID, list[CheckTask]] = {}
        for task in tasks:
            by_supplier.setdefault(task.supplier_id, []).append(task)
        first, second = list(by_supplier.values())
        before = {t.id for t in runnable_tasks(db, UUID(run["run_id"]))}
        assert {t.id for t in tasks if not t.dependency_ids} <= before
        # Controlled state transition (disclosed): the first supplier's certificate document
        # is unreadable, so its dependent tasks wait while the other supplier progresses.
        document_task = next(t for t in first if t.check_type == "certificate_document")
        document_task.state = "waiting_input"
        db.flush()
        runnable = {t.id for t in runnable_tasks(db, UUID(run["run_id"]))}
        dependents = {t.id for t in first if document_task.id in t.dependency_ids}
        assert document_task.id not in runnable and not (dependents & runnable)
        assert {t.id for t in second if not t.dependency_ids} <= runnable
        run_row = db.get(VerificationRun, UUID(run["run_id"]))
        assert run_row is not None and run_row.state in {"queued", "running"}
    with Session(engine) as check:  # No CAPTCHA attempt or buyer scraping task was created.
        assert all(a.reason_code != "captcha" for a in check.scalars(select(CheckAttempt)))
