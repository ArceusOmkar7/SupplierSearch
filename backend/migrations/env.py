"""Alembic environment; local validated settings supply the private connection URL."""

from alembic import context

from verisource.config import Settings
from verisource.db import models  # noqa: F401 -- register the owned tables.
from verisource.db.base import Base
from verisource.db.session import create_database_engine


def run_migrations() -> None:
    settings = context.config.attributes.get("settings")
    if not isinstance(settings, Settings):
        settings = Settings()
    if context.is_offline_mode():
        context.configure(
            url=settings.database_url.get_secret_value(),
            target_metadata=Base.metadata,
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
        )
        with context.begin_transaction():
            context.run_migrations()
    else:
        engine = create_database_engine(settings)
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=Base.metadata)
            with context.begin_transaction():
                context.run_migrations()
        engine.dispose()


run_migrations()
