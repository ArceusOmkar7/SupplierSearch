"""A confirmed run driven through the durable worker over actual BIS records.

Suppliers are actual rows of the historical BIS IS 9473 licence list, identified by the licence
number printed in that record; the tender text is the actual BIS procurement request. No
website is supplied, so website checks must record a local skip rather than a fetch. The
tests assert what the system recorded and concluded, not that suppliers are qualified.
"""

from collections import Counter
from collections.abc import Iterator
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select, update
from sqlalchemy.orm import Session
from support import ORIGIN, RECORDS, Api, drain, licence_rows, start_run

from verisource.api.app import create_app
from verisource.config import Settings
from verisource.country_packs.india.bis import ingest_qco_catalog
from verisource.db.checkpoints import checkpointer
from verisource.db.models import (
    Assessment,
    CheckAttempt,
    CheckTask,
    EvidenceRecord,
    GraphCheckpointReference,
    IdentityResolution,
    VerificationRun,
    WorkItem,
)
from verisource.sources.imports import import_source_dataset
from verisource.storage.filesystem import PrivateFileStore

pytestmark = [pytest.mark.integration, pytest.mark.real_records]


@pytest.fixture
def world(buyer_pair: tuple[Settings, str, str, str]) -> Iterator[tuple[Settings, Any, Api]]:
    settings, first, _second, password = buyer_pair
    engine = create_engine(settings.database_url.get_secret_value(), hide_parameters=True)
    with checkpointer(settings, initialize=True):
        pass
    store = PrivateFileStore(settings.data_root / "corpus")
    with Session(engine) as db, db.begin():
        import_source_dataset(db, store, RECORDS / "bis-licences.manifest.json")
        ingest_qco_catalog(db, store, RECORDS / "bis-qco-scheme1.manifest.json")
    with TestClient(create_app(settings), base_url=ORIGIN) as client:
        yield settings, engine, Api(client, first, password)
    engine.dispose()


def test_run_records_actual_attempts_evidence_and_conservative_assessments(
    world: tuple[Settings, Any, Api],
) -> None:
    settings, engine, api = world
    rows = [licence_rows()[0], licence_rows()[2]]
    started = start_run(api, rows)
    run_id = UUID(started["run_id"])
    assert drain(settings, engine) > 0

    with Session(engine) as db:
        run = db.get(VerificationRun, run_id)
        assert run is not None and run.state == "completed_with_gaps"
        assert run.started_at is not None and run.completed_at is not None
        tasks = list(db.scalars(select(CheckTask).where(CheckTask.run_id == run_id)))
        assert all(t.state in {"succeeded", "no_evidence"} for t in tasks)
        # No website was supplied: a local skip, never a fetch.
        website = [
            a for a in db.scalars(select(CheckAttempt)) if a.reason_code == "missing_identifier"
        ]
        assert website and all(not a.request_dispatched for a in website)
        # Exact licence-number lookups in the actual export produced attributed evidence.
        evidence = list(db.scalars(select(EvidenceRecord).where(EvidenceRecord.run_id == run_id)))
        export = [e for e in evidence if e.origin_lineage.startswith("dataset:")]
        assert len(export) == 2 and all(e.authority_role == "official_publication" for e in export)
        assert all("cutoff 2020-08-27" in e.observation for e in export)
        states = {
            db.get(IdentityResolution, e.identity_resolution_id).state  # type: ignore[union-attr]
            for e in export
        }
        assert states == {"confirmed"}
        # The BIS current-licence search is never automated; recorded, not dispatched.
        manak = [
            a
            for a in db.scalars(select(CheckAttempt))
            if a.target == "manak-current-licence-search"
        ]
        assert manak and all(a.outcome == "skipped" and not a.request_dispatched for a in manak)

        assessments = list(db.scalars(select(Assessment).where(Assessment.run_id == run_id)))
        claims = {c["id"] for c in started["checklist"]["claims"]}
        assert {str(a.claim_id) for a in assessments} == claims
        assert {a.verdict for a in assessments} <= {"proven", "unproven", "contradicted"}
        # An historical export and partial order list cannot prove current requirements.
        assert Counter(a.verdict for a in assessments)["proven"] == 0
        licence = [
            a
            for a in assessments
            if any(r["criterion_id"] == "regulatory.licence" for r in a.criterion_results)
        ]
        assert licence, "regulatory claims are expected for the IS 9473 standard"
        for a in licence:
            joined = " | ".join(a.gaps)
            # The listed validity ended long ago and the export is not a current status check;
            # another supplier's record is rejected as out of scope.
            assert "validity has ended" in joined or "historical export" in joined, joined
            assert "does not belong to this case and supplier" in joined, joined
        assert db.scalar(select(func.count()).select_from(GraphCheckpointReference)) == len(tasks)


def test_redelivery_does_not_duplicate_persisted_results(world: tuple[Settings, Any, Api]) -> None:
    settings, engine, api = world
    started = start_run(api, [licence_rows()[1]])
    run_id = UUID(started["run_id"])
    drain(settings, engine)

    def counts() -> tuple[int, int, int]:
        with Session(engine) as db:
            return (
                db.scalar(select(func.count()).select_from(CheckAttempt)) or 0,
                db.scalar(select(func.count()).select_from(EvidenceRecord)) or 0,
                db.scalar(select(func.count()).select_from(Assessment)) or 0,
            )

    before = counts()
    # Controlled at-least-once redelivery: acknowledged check jobs are queued again.
    with Session(engine) as db, db.begin():
        db.execute(
            update(WorkItem)
            .where(WorkItem.run_id == run_id, WorkItem.kind == "check_task")
            .values(state="queued")
        )
    drain(settings, engine, owner="second-worker")
    assert counts() == before


def test_cancelled_run_stops_pending_work_and_keeps_history(
    world: tuple[Settings, Any, Api],
) -> None:
    settings, engine, api = world
    started = start_run(api, [licence_rows()[3]])
    case_id, run_id = started["case_id"], started["run_id"]
    run_etag = api.get(f"/cases/{case_id}/runs/{run_id}").headers["ETag"]
    cancel = api.post(f"/cases/{case_id}/runs/{run_id}/cancel", etag=run_etag)
    assert cancel.status_code == 202, cancel.text
    assert cancel.json()["run"]["state"] == "cancelled"
    drain(settings, engine)
    with Session(engine) as db:
        tasks = list(db.scalars(select(CheckTask).where(CheckTask.run_id == UUID(run_id))))
        assert tasks and all(t.state == "cancelled" for t in tasks)
        for model in (EvidenceRecord, Assessment):
            scoped = select(func.count()).select_from(model).where(model.run_id == UUID(run_id))
            assert db.scalar(scoped) == 0


def test_exhausted_job_fails_its_task_and_the_run_still_finishes(
    world: tuple[Settings, Any, Api],
) -> None:
    """Controlled fault: every check job raises. The task must not stay 'running' forever."""
    from sqlalchemy import func, update

    from verisource.db.models import CaseEvent
    from verisource.orchestration.worker import run_once

    _settings, engine, api = world
    started = start_run(api, [licence_rows()[1]])
    run_id = UUID(started["run_id"])

    def boom(lease: Any, lost: Any) -> Any:
        raise RuntimeError("controlled handler failure")

    for _ in range(80):
        with Session(engine) as db, db.begin():  # Disclosed clock control: retries are due now.
            db.execute(
                update(WorkItem).where(WorkItem.state == "retry_wait").values(due_at=func.now())
            )
        run_once(engine, {"check_task": boom}, owner="faulty")
        with Session(engine) as db:
            run = db.get(VerificationRun, run_id)
            if run is not None and run.state not in {"queued", "running"}:
                break
    with Session(engine) as db:
        run = db.get(VerificationRun, run_id)
        assert run is not None and run.state == "completed_with_gaps"
        tasks = list(db.scalars(select(CheckTask).where(CheckTask.run_id == run_id)))
        assert tasks and all(t.state == "failed" for t in tasks)
        internal = [a for a in db.scalars(select(CheckAttempt)) if a.target.startswith("internal:")]
        assert internal and all(not a.request_dispatched for a in internal)
        events = list(db.scalars(select(CaseEvent).where(CaseEvent.type == "work.failed")))
        assert events and events[0].public_payload["reason"] == "RuntimeError"
