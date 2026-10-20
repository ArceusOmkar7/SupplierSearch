"""Real DB leases and disclosed fault controls; no simulated source/provider responses."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from test_local_auth import auth_setup as auth_setup_fixture

from verisource.config import Settings
from verisource.db.models import Case, WorkItem
from verisource.orchestration.jobs import claim, complete, enqueue

auth_setup = auth_setup_fixture
pytestmark = [pytest.mark.integration, pytest.mark.real_records]


def test_expired_worker_cannot_ack_reclaimed_work(
    auth_setup: tuple[Settings, str, str, str, UUID],
) -> None:
    settings, _first, _second, _password, case_id = auth_setup
    engine = create_engine(settings.database_url.get_secret_value(), hide_parameters=True)
    with Session(engine) as db, db.begin():
        case = db.get(Case, case_id)
        assert case is not None
        work = enqueue(
            db, case, kind="disclosed-control", operation_key="lease-control", references={}
        )
        work_id = work.id
    first = claim(engine, "first-control-worker")
    assert first is not None
    with Session(engine) as db, db.begin():
        row = db.get(WorkItem, work_id)
        assert row is not None
        row.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    replacement = claim(engine, "replacement-control-worker")
    assert replacement is not None and replacement.fence > first.fence
    assert not complete(
        engine, first, lambda _db: pytest.fail("Stale worker executed a domain commit")
    )
    assert complete(engine, replacement, lambda _db: None)
    with Session(engine) as db:
        row = db.get(WorkItem, work_id)
        assert row is not None and row.state == "succeeded"
    engine.dispose()


def test_generation_fence_and_failed_domain_commit_prevent_ack(
    auth_setup: tuple[Settings, str, str, str, UUID],
) -> None:
    settings, _first, _second, _password, case_id = auth_setup
    engine = create_engine(settings.database_url.get_secret_value(), hide_parameters=True)
    with Session(engine) as db, db.begin():
        case = db.get(Case, case_id)
        assert case is not None
        enqueue(
            db, case, kind="disclosed-control", operation_key="generation-control", references={}
        )
    lease = claim(engine, "control-worker")
    assert lease is not None

    def fault(_db: Session) -> None:
        raise RuntimeError("Disclosed domain-commit fault; no external request occurred")

    with pytest.raises(RuntimeError):
        complete(engine, lease, fault)
    with Session(engine) as db, db.begin():
        work = db.get(WorkItem, lease.work_id)
        case = db.get(Case, case_id)
        assert work is not None and work.state == "leased" and case is not None
        case.write_generation += 1
    assert not complete(engine, lease, lambda _db: pytest.fail("Superseded generation committed"))
    engine.dispose()


def test_locked_work_is_skipped(auth_setup: tuple[Settings, str, str, str, UUID]) -> None:
    settings, _first, _second, _password, case_id = auth_setup
    engine = create_engine(settings.database_url.get_secret_value(), hide_parameters=True)
    with Session(engine) as db, db.begin():
        case = db.get(Case, case_id)
        assert case is not None
        first = enqueue(
            db, case, kind="disclosed-control", operation_key="locked-first", references={}
        )
        first_id = first.id
        second = enqueue(
            db, case, kind="disclosed-control", operation_key="unlocked-second", references={}
        )
        second_id = second.id
    with Session(engine) as locked, locked.begin():
        locked.scalar(select(WorkItem).where(WorkItem.id == first_id).with_for_update())
        selected = claim(engine, "independent-worker")
        assert selected is not None and selected.work_id == second_id
    engine.dispose()
