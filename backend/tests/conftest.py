"""Opt-in disposable DB and real-record fixtures; never touch the developer's live cases."""

import os

import pytest
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


def validate_test_database_url(value: str, live_value: str | None = None) -> str:
    """Fail closed unless a dedicated loopback verisource_test_* database is selected."""
    try:
        url = make_url(value)
        live = make_url(live_value) if live_value else None
        if (
            url.drivername != "postgresql+psycopg"
            or url.host not in {"127.0.0.1", "::1", "localhost"}
            or not url.database
            or not url.database.startswith("verisource_test_")
            or url.query
            or (live and url.database == live.database)
        ):
            raise ValueError
    except ValueError, TypeError, ArgumentError:
        raise ValueError("Refusing non-disposable, non-loopback or live test database") from None
    return value


@pytest.fixture
def test_database_url() -> str:
    value = os.environ.get("VERISOURCE_TEST_DATABASE_URL")
    if not value:
        pytest.fail("Missing prerequisite: set a dedicated VERISOURCE_TEST_DATABASE_URL")
    return validate_test_database_url(value, os.environ.get("VERISOURCE_DATABASE_URL"))


@pytest.fixture
def buyer_pair(test_database_url: str, tmp_path):  # type: ignore[no-untyped-def]
    """Two operator-provisioned test accounts; credentials are never source facts."""
    from uuid import uuid4

    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from verisource.config import Settings
    from verisource.security.sessions import provision_buyer

    engine = create_engine(test_database_url, hide_parameters=True)
    password = str(uuid4())
    first, second = f"owner-{uuid4()}", f"other-{uuid4()}"
    with Session(engine) as db, db.begin():
        provision_buyer(db, first, password, "Owner control")
        provision_buyer(db, second, password, "Other account control")
    settings = Settings.model_validate(
        {"database_url": test_database_url, "data_root": tmp_path / "data"}
    )
    yield settings, first, second, password
    engine.dispose()


@pytest.fixture(autouse=True)
def clean_disposable_database(request: pytest.FixtureRequest):  # type: ignore[no-untyped-def]
    """Tests that use the disposable DB start from empty tables (never the live DB).

    The guard in `test_database_url` has already refused any non-disposable database, so
    truncation can only ever touch a `verisource_test_*` database.
    """
    if "test_database_url" not in request.fixturenames:
        yield
        return
    from sqlalchemy import create_engine, text

    from verisource.db import models  # noqa: F401 -- register every table
    from verisource.db.base import Base

    url = request.getfixturevalue("test_database_url")
    engine = create_engine(url, hide_parameters=True)
    names = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE TABLE {names} RESTART IDENTITY CASCADE"))
    engine.dispose()
    yield


@pytest.fixture
def us1_world(buyer_pair):  # type: ignore[no-untyped-def]
    """Two signed-in owners, imported actual BIS sources and a worker-ready engine."""
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from support import ORIGIN, RECORDS, Api

    from verisource.api.app import create_app
    from verisource.country_packs.india.bis import ingest_qco_catalog
    from verisource.db.checkpoints import checkpointer
    from verisource.sources.imports import import_source_dataset
    from verisource.storage.filesystem import PrivateFileStore

    settings, first, second, password = buyer_pair
    engine = create_engine(settings.database_url.get_secret_value(), hide_parameters=True)
    with checkpointer(settings, initialize=True):
        pass
    store = PrivateFileStore(settings.data_root / "corpus")
    with Session(engine) as db, db.begin():
        import_source_dataset(db, store, RECORDS / "bis-licences.manifest.json")
        ingest_qco_catalog(db, store, RECORDS / "bis-qco-scheme1.manifest.json")
    with (
        TestClient(create_app(settings), base_url=ORIGIN) as one,
        TestClient(create_app(settings), base_url=ORIGIN) as two,
    ):
        yield settings, engine, Api(one, first, password), Api(two, second, password)
    engine.dispose()
