"""Real PostgreSQL constraints under disclosed control transitions using genuine source records."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from pwdlib import PasswordHash
from records import load_record
from sqlalchemy import create_engine, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from verisource.db.models import BuyerAccount, Case, LoginSession, RequirementRevision

pytestmark = [pytest.mark.integration, pytest.mark.real_records]


@pytest.fixture
def db(test_database_url: str) -> Iterator[Session]:
    engine = create_engine(test_database_url, hide_parameters=True)
    with engine.connect() as connection, connection.begin() as outer:
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
            yield session
        outer.rollback()
    engine.dispose()


def buyer(db: Session) -> BuyerAccount:
    account = BuyerAccount(
        username_normalized=f"schema-control-{uuid4()}",
        password_hash=PasswordHash.recommended().hash(str(uuid4())),
        display_name="Local schema control account",
    )
    db.add(account)
    db.flush()
    return account


def case_revision(db: Session) -> tuple[BuyerAccount, Case, RequirementRevision]:
    manifest, _content = load_record(Path(".local/records/bis-procurement.manifest.json"))
    account = buyer(db)
    case = Case(owner_id=account.id, title="Controlled replay of actual BIS public procurement")
    db.add(case)
    db.flush()
    revision = RequirementRevision(
        case_id=case.id,
        sequence=1,
        requirements_json={"schema_version": 1, "source_document_sha256": manifest["sha256"]},
        location_json={"schema_version": 1},
        supplier_set_json=[],
        input_provenance={
            "schema_version": 1,
            "mode": "real_record_replay",
            "original_url": manifest["original_url"],
        },
    )
    db.add(revision)
    db.flush()
    return account, case, revision


def test_null_draft_fields_round_trip(db: Session) -> None:
    _account, case, revision = case_revision(db)
    db.expire_all()
    assert case.active_revision_id is None and case.latest_snapshot_id is None
    assert case.closed_at is None and case.deleting_at is None
    assert revision.confirmed_at is None and revision.confirmed_by is None


def test_confirmation_pair_and_immutability(db: Session) -> None:
    account, _case, revision = case_revision(db)
    with pytest.raises(DBAPIError), db.begin_nested():
        revision.status = "confirmed"
        db.flush()
    revision.status = "confirmed"
    revision.confirmed_at = datetime.now(UTC)
    revision.confirmed_by = account.id
    db.flush()
    with pytest.raises(DBAPIError), db.begin_nested():
        revision.requirements_json = {"schema_version": 1, "invalid_control_change": True}
        db.flush()


def test_owner_cannot_change(db: Session) -> None:
    _account, case, _revision = case_revision(db)
    another = buyer(db)
    with pytest.raises(DBAPIError), db.begin_nested():
        db.execute(update(Case).where(Case.id == case.id).values(owner_id=another.id))


def test_active_revision_cannot_cross_cases(db: Session) -> None:
    account, _case, _revision = case_revision(db)
    other_case = Case(owner_id=account.id, title="Second control namespace")
    db.add(other_case)
    db.flush()
    with pytest.raises(DBAPIError), db.begin_nested():
        db.execute(
            update(Case).where(Case.id == other_case.id).values(active_revision_id=_revision.id)
        )


def test_single_draft_and_valid_session_null_revocation(db: Session) -> None:
    account, case, revision = case_revision(db)
    now = datetime.now(UTC)
    session = LoginSession(
        id_hash=uuid4().hex,
        buyer_id=account.id,
        created_at=now,
        last_seen_at=now,
        expires_at=now + timedelta(hours=8),
        csrf_secret=uuid4().hex,
    )
    db.add(session)
    db.flush()
    assert session.revoked_at is None
    with pytest.raises(DBAPIError), db.begin_nested():
        db.execute(
            update(LoginSession)
            .where(LoginSession.id_hash == session.id_hash)
            .values(last_seen_at=now - timedelta(microseconds=1))
        )
    with pytest.raises(DBAPIError), db.begin_nested():
        db.add(
            RequirementRevision(
                case_id=case.id,
                sequence=2,
                requirements_json=revision.requirements_json,
                location_json=revision.location_json,
                supplier_set_json=[],
                input_provenance=revision.input_provenance,
            )
        )
        db.flush()
