"""One durable local worker; run python -m verisource.orchestration.worker on loopback."""

import logging
import threading
import traceback
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from verisource.config import Settings, disable_external_tracing
from verisource.db.session import create_database_engine
from verisource.orchestration.jobs import Lease, claim, complete, fail, heartbeat

if TYPE_CHECKING:
    from verisource.orchestration.executors import Executor

Handler = Callable[[Lease, threading.Event], Callable[[Session], None]]


def run_once(engine: Engine, handlers: Mapping[str, Handler], *, owner: str) -> bool:
    lease = claim(engine, owner)
    if lease is None:
        return False
    stop = threading.Event()
    lost = threading.Event()

    def keep_alive() -> None:
        while not stop.wait(15):
            try:
                valid = heartbeat(engine, lease)
            except SQLAlchemyError:
                valid = False
            if not valid:
                lost.set()
                return

    renewer = threading.Thread(target=keep_alive, daemon=True)
    renewer.start()
    try:
        if not heartbeat(engine, lease):
            return True
        handler = handlers.get(lease.kind)
        if handler is None:
            fail(engine, lease, retryable=False)
            return True
        apply = handler(lease, lost)  # External calls happen outside the result transaction.
        if not lost.is_set():
            complete(engine, lease, apply)
    except Exception as exc:  # noqa: BLE001 -- retain durable work; never log source payloads/secrets.
        fail(engine, lease, retryable=True, error_type=type(exc).__name__)
        frames = " <- ".join(
            f"{Path(f.filename).name}:{f.lineno}:{f.name}"
            for f in reversed(traceback.extract_tb(exc.__traceback__)[-4:])
        )  # File, line and function only: never argument values or source payloads.
        logging.getLogger("verisource").warning(
            "Work %s failed (%s at %s); durable retry state recorded",
            lease.kind,
            type(exc).__name__,
            frames,
        )
    finally:
        stop.set()
        renewer.join(timeout=6)
    return True


def build_handlers(
    settings: Settings, engine: Engine, executor: Executor | None = None
) -> dict[str, Handler]:
    """Every job kind the local worker understands; unknown kinds fail without retry."""
    from verisource.models.router import ModelRouter
    from verisource.orchestration.executors import Executor
    from verisource.orchestration.graph import make_handlers
    from verisource.orchestration.interpretation import extract_document, interpret_message

    router = ModelRouter(settings)
    executor = executor or Executor(settings, engine, router=router)
    handlers = dict(make_handlers(settings, engine, executor))
    handlers["interpret_message"] = lambda lease, lost: interpret_message(
        engine, router, lease, lost
    )
    handlers["extract_document"] = lambda lease, lost: extract_document(
        engine, settings, router, lease, lost
    )
    return handlers


def main() -> None:
    disable_external_tracing()
    settings = Settings()
    engine = create_database_engine(settings)
    handlers = build_handlers(settings, engine)
    owner = str(uuid4())
    try:
        while True:
            try:
                worked = run_once(engine, handlers, owner=owner)
            except SQLAlchemyError:
                logging.getLogger("verisource").warning(
                    "Database unavailable; retaining pending work"
                )
                worked = False
            if not worked:
                threading.Event().wait(30)
    except KeyboardInterrupt:
        pass
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
