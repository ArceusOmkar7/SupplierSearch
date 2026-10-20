"""Idempotency and stale-write contracts using genuine request provenance in a test DB."""

from uuid import UUID

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from test_local_auth import auth_setup as auth_setup_fixture

auth_setup = auth_setup_fixture

from verisource.api.dependencies import owned_child
from verisource.config import Settings
from verisource.db.models import Case, CaseEvent, RequirementRevision
from verisource.domain.commands import case_etag, execute_command

pytestmark = [pytest.mark.integration, pytest.mark.real_records]


def test_command_replay_collision_and_stale_etag(
    auth_setup: tuple[Settings, str, str, str, UUID],
) -> None:
    settings, _first, _second, _password, case_id = auth_setup
    engine = create_engine(settings.database_url.get_secret_value(), hide_parameters=True)
    with Session(engine) as db, db.begin():
        case = db.get(Case, case_id)
        assert case is not None
        owner_id, original_etag = case.owner_id, case_etag(case)
        calls = []

        def apply(current: Case) -> dict[str, str]:
            calls.append(current.id)
            return {"case_id": str(current.id)}

        def invoke(
            *, key: str = "stable-control-key", changed: bool = False
        ) -> tuple[dict[str, object], str]:
            return execute_command(
                db,
                case_id=case_id,
                buyer_id=owner_id,
                operation="control",
                key=key,
                if_match=original_etag,
                body={"changed_control": True} if changed else {"source_case": str(case_id)},
                apply=apply,
            )

        first = invoke()
        assert invoke() == first
        assert len(calls) == 1
        assert len(db.scalars(select(CaseEvent).where(CaseEvent.case_id == case_id)).all()) == 1
        with pytest.raises(HTTPException) as collision:
            invoke(changed=True)
        assert collision.value.status_code == 409
        with pytest.raises(HTTPException) as stale:
            invoke(key="different-key")
        assert stale.value.status_code == 412
    engine.dispose()


def test_child_reference_cannot_escape_its_authorized_case(
    auth_setup: tuple[Settings, str, str, str, UUID],
) -> None:
    settings, _first, _second, _password, case_id = auth_setup
    engine = create_engine(settings.database_url.get_secret_value(), hide_parameters=True)
    with Session(engine) as db, db.begin():
        case = db.get(Case, case_id)
        revision = db.scalar(
            select(RequirementRevision).where(RequirementRevision.case_id == case_id)
        )
        assert case is not None and revision is not None
        other_case = Case(owner_id=case.owner_id, title=case.title)
        db.add(other_case)
        db.flush()
        assert (
            owned_child(
                db, RequirementRevision, revision.id, case_id=case_id, buyer_id=case.owner_id
            ).id
            == revision.id
        )
        with pytest.raises(HTTPException) as mismatch:
            owned_child(
                db, RequirementRevision, revision.id, case_id=other_case.id, buyer_id=case.owner_id
            )
        assert mismatch.value.status_code == 404
    engine.dispose()
