"""Create local database sessions explicitly; one session belongs to one unit of work."""

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from verisource.config import Settings


def create_database_engine(settings: Settings) -> Engine:
    return create_engine(
        settings.database_url.get_secret_value(),
        pool_pre_ping=True,
        hide_parameters=True,
        connect_args={"connect_timeout": 5},
    )


def session_factory(engine: Engine) -> sessionmaker[Session]:
    """Caller uses factory.begin() to atomically commit domain/event/work rows."""
    return sessionmaker(engine, expire_on_commit=False)
