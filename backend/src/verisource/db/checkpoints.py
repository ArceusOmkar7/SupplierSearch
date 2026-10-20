"""Use the library-managed Postgres checkpointer in its own local schema."""

from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg.rows import dict_row
from sqlalchemy.engine import make_url

from verisource.config import Settings


@contextmanager
def checkpointer(settings: Settings, *, initialize: bool = False) -> Iterator[PostgresSaver]:
    url = make_url(settings.database_url.get_secret_value()).set(drivername="postgresql")
    with psycopg.connect(
        url.render_as_string(hide_password=False),
        autocommit=True,
        prepare_threshold=0,
        row_factory=dict_row,
        connect_timeout=5,
    ) as connection:
        if initialize:
            connection.execute("CREATE SCHEMA IF NOT EXISTS checkpoints")
        connection.execute("SET search_path TO checkpoints")
        saver = PostgresSaver(connection)
        if initialize:
            saver.setup()
        yield saver
