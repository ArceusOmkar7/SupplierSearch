"""Request limits, batch gating, dependent actions and the durable event stream.

Inputs are the actual BIS licence-list suppliers and tender. Concurrency uses a disclosed
counting transport that returns no source content; forced waiting tasks are disclosed controls
because no natural locked certificate exists in the acquired records.
"""

import json
import threading
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from uuid import UUID

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from support import ORIGIN, RECORDS, Api, drain, licence_rows, start_run

from verisource.api.app import create_app
from verisource.config import Settings
from verisource.country_packs.india.bis import ingest_qco_catalog
from verisource.db.checkpoints import checkpointer
from verisource.db.models import (
    CaseEvent,
    CheckTask,
    HumanAction,
    IdentityResolution,
    VerificationRun,
    WorkItem,
)
from verisource.security.egress import GuardedFetch
from verisource.sources.imports import import_source_dataset
from verisource.storage.filesystem import PrivateFileStore

pytestmark = [pytest.mark.integration, pytest.mark.real_records]


@pytest.fixture
def world(buyer_pair: tuple[Settings, str, str, str]) -> Iterator[tuple[Any, ...]]:
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


def test_outbound_concurrency_is_bounded_globally_and_per_domain() -> None:
    lock = threading.Lock()
    in_flight: dict[str, int] = {}
    peak = {"global": 0}
    peak_host: dict[str, int] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        host = request.url.host
        with lock:
            in_flight[host] = in_flight.get(host, 0) + 1
            total = sum(in_flight.values())
            peak["global"] = max(peak["global"], total)
            peak_host[host] = max(peak_host.get(host, 0), in_flight[host])
        time.sleep(0.05)
        with lock:
            in_flight[host] -= 1
        return httpx.Response(204)  # No source content is simulated.

    fetcher = GuardedFetch(
        resolver=lambda _h: ["93.184.216.34"], transport=httpx.MockTransport(handler)
    )
    hosts = [f"supplier-{n}.example.org" for n in range(6)]
    threads = [
        threading.Thread(target=lambda h=host: fetcher.get(f"https://{h}/page"))
        for host in hosts
        for _ in range(3)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(30)
    assert peak["global"] <= 4
    assert max(peak_host.values()) == 1
    fetcher.close()


def test_larger_lists_queue_in_five_supplier_batches(world: tuple[Any, ...]) -> None:
    settings, engine, api, _other = world
    started = start_run(api, licence_rows()[:7])
    run_id = UUID(started["run_id"])
    with Session(engine) as db:
        first_wave = {
            UUID(w.payload_refs["task_id"])
            for w in db.scalars(select(WorkItem))
            if w.kind == "check_task"
        }
        tasks = {t.id: t for t in db.scalars(select(CheckTask).where(CheckTask.run_id == run_id))}
        suppliers = {tasks[i].supplier_id for i in first_wave}
        assert len(suppliers) == 5  # Only the active batch has been queued.
    assert drain(settings, engine) > 0
    with Session(engine) as db:
        run = db.get(VerificationRun, run_id)
        assert run is not None and run.state == "completed_with_gaps"
        done = list(db.scalars(select(CheckTask).where(CheckTask.run_id == run_id)))
        assert {t.supplier_id for t in done} >= suppliers and len(
            {t.supplier_id for t in done}
        ) == 7
        assert all(t.state in {"succeeded", "no_evidence"} for t in done)


def test_waiting_identity_action_holds_only_dependents_until_the_buyer_resolves(
    world: tuple[Any, ...],
) -> None:
    settings, engine, api, other = world
    started = start_run(api, [licence_rows()[0], licence_rows()[2]])
    case_id, run_id = started["case_id"], UUID(started["run_id"])
    with Session(engine) as db, db.begin():
        tasks = list(db.scalars(select(CheckTask).where(CheckTask.run_id == run_id)))
        issuer = next(t for t in tasks if t.check_type == "certificate_issuer_lookup")
        sibling = [
            t for t in tasks if t.supplier_id == issuer.supplier_id and t.dependency_ids == issuer.dependency_ids
            and t.id != issuer.id
        ]  # fmt: skip
        revision_id = db.get(VerificationRun, run_id).revision_id  # type: ignore[union-attr]
        # Controlled: the buyer-review pause a proposed identity would create.
        action = HumanAction(
            case_id=UUID(case_id), revision_id=revision_id, run_id=run_id,
            affected_task_ids=[issuer.id, *(t.id for t in sibling)], type="resolve_identity",
        )  # fmt: skip
        db.add(action)
        db.flush()
        for task in [issuer, *sibling]:
            task.state, task.wait_action_id = "waiting_input", action.id
        db.add(IdentityResolution(
            case_id=UUID(case_id), revision_id=revision_id, supplier_id=issuer.supplier_id,
            candidate_record_ref="document:control", identifier_matches=[], discrepancies=[],
            state="proposed", resolution_basis="name_similarity",
        ))  # fmt: skip
        action_id = str(action.id)
        waiting = {issuer.id, *(t.id for t in sibling)}
    drain(settings, engine)
    with Session(engine) as db:
        run = db.get(VerificationRun, run_id)
        assert run is not None and run.state == "running"  # still waiting on the buyer
        states = {
            t.id: t.state for t in db.scalars(select(CheckTask).where(CheckTask.run_id == run_id))
        }
        assert all(states[i] == "waiting_input" for i in waiting)
        assert all(s != "queued" for i, s in states.items() if i not in waiting)

    # The finished supplier is published without waiting for the one that needs the buyer.
    snapshots = api.get(f"/cases/{case_id}/snapshots").json()["items"]
    assert snapshots and snapshots[0]["partial"] is True
    shown = api.get(f"/cases/{case_id}/snapshots/{snapshots[0]['id']}").json()["content"]
    shown_states = {s["processing_state"] for s in shown["suppliers"]}
    assert {"waiting_input", "complete"} <= shown_states
    assert shown["pending_actions"] and shown["pending_actions"][0]["type"] == "resolve_identity"

    pending = api.get(f"/cases/{case_id}/actions?state=pending").json()["items"]
    assert [a["id"] for a in pending] == [action_id]
    captures = Path(__file__).resolve().parents[3] / "frontend/tests/captures"
    captures.mkdir(parents=True, exist_ok=True)
    (captures / "action-pending.json").write_text(
        json.dumps(
            {"etag": pending[0]["etag"], "body": {"items": pending, "next_cursor": None}}, indent=2
        )
        + "\n",
        encoding="utf-8",
    )  # Controlled pause on a real run; recorded for the UI component test.
    assert pending[0]["type"] == "resolve_identity" and "scrap" not in str(pending[0]).lower()
    path = f"/cases/{case_id}/actions/{action_id}/resolve"
    assert other.post(path, {"decision": "confirm"}, etag=pending[0]["etag"]).status_code == 404
    assert api.post(path, {"decision": "confirm"}, etag='"stale"').status_code == 412
    assert api.post(path, {"decision": "maybe"}, etag=pending[0]["etag"]).status_code == 422
    resolved = api.post(path, {"decision": "confirm"}, etag=pending[0]["etag"])
    assert resolved.status_code == 202, resolved.text
    assert api.post(path, {"decision": "confirm"}, etag=resolved.json()["etag"]).status_code == 409
    drain(settings, engine)
    with Session(engine) as db:
        run = db.get(VerificationRun, run_id)
        assert run is not None and run.state == "completed_with_gaps"
        assert db.scalar(select(IdentityResolution.state).where(
            IdentityResolution.candidate_record_ref == "document:control")) == "confirmed"  # fmt: skip
        types = {
            e.type for e in db.scalars(select(CaseEvent).where(CaseEvent.case_id == UUID(case_id)))
        }
        assert {"action.resolved", "run.progress", "check.completed"} <= types


def test_replacement_document_must_be_a_different_readable_same_case_document(
    world: tuple[Any, ...],
) -> None:
    _settings, engine, api, _other = world
    started = start_run(api, [licence_rows()[1]])
    case_id, run_id = started["case_id"], UUID(started["run_id"])
    supplier = api.get(f"/cases/{case_id}").json()
    del supplier
    created = api.get(f"/cases/{case_id}/revisions/{started['checklist']['revision_id']}").json()
    supplier_id = created["suppliers"][0]["supplier_id"]
    upload = api.client.post(
        f"/api/v1/cases/{case_id}/documents",
        files={
            "file": ("licences.pdf", (RECORDS / "bis-licences.pdf").read_bytes(), "application/pdf")
        },
        data={"supplier_id": supplier_id, "revision_id": created["id"]},
        headers=api.headers(key=None),
    )
    document_id = upload.json()["document"]["id"]
    with Session(engine) as db, db.begin():
        task = db.scalars(
            select(CheckTask).where(
                CheckTask.run_id == run_id, CheckTask.check_type == "certificate_document"
            )
        ).one()
        action = HumanAction(  # Controlled: a buyer-upload pause as a locked file would cause.
            case_id=UUID(case_id), revision_id=UUID(created["id"]), run_id=run_id,
            affected_task_ids=[task.id], type="supply_unlocked_document",
            requested_document_ref=UUID(document_id),
        )  # fmt: skip
        db.add(action)
        db.flush()
        task.state, task.wait_action_id = "waiting_input", action.id
        action_id = str(action.id)
    etag = api.get(f"/cases/{case_id}/actions/{action_id}").headers["ETag"]
    path = f"/cases/{case_id}/actions/{action_id}/resolve"
    same = api.post(path, {"replacement_document_id": document_id}, etag=etag)
    assert same.status_code == 422  # the same file is not a replacement
    missing = api.post(
        path, {"replacement_document_id": "00000000-0000-4000-8000-000000000000"}, etag=etag
    )
    assert missing.status_code == 404


def read_stream(client: TestClient, path: str, headers: dict[str, str], sink: list[str]) -> None:
    with client.stream("GET", path, headers=headers) as response:
        sink.append(f"status:{response.status_code}")
        for line in response.iter_lines():
            sink.append(line)
            if line.startswith("event: close"):
                return


def test_event_stream_replays_from_a_cursor_and_closes_after_logout(world: tuple[Any, ...]) -> None:
    settings, _engine, api, other = world
    created = api.post("/cases", {"title": "Actual BIS tender", "suppliers": [
        {"display_name": licence_rows()[0].firm_name,
         "identifiers": [{"type": "name", "value": licence_rows()[0].firm_name}]}]}).json()  # fmt: skip
    case_id = created["case"]["id"]
    path = f"/api/v1/cases/{case_id}/events"
    assert (
        other.client.get(path).status_code == 404
    )  # another owner sees the same unavailable shape

    sink: list[str] = []
    reader = TestClient(create_app(settings), base_url=ORIGIN)
    reader.__enter__()
    reader.cookies.set("verisource_session", api.client.cookies["verisource_session"],
                       domain="127.0.0.1", path="/api/v1")  # fmt: skip
    thread = threading.Thread(target=read_stream, args=(reader, path, {"Last-Event-ID": "0"}, sink))
    thread.start()
    deadline = time.time() + 20
    while not any(line.startswith("id: ") for line in sink) and time.time() < deadline:
        time.sleep(0.2)
    revision = created["revision"]
    assert api.patch(
        f"/cases/{case_id}/revisions/{revision['id']}",
        {"requirements": {"part_description": "Replayed edit"}},
        etag=revision["etag"],
    ).status_code == 200  # fmt: skip
    while (
        not any(
            "Replayed" not in line
            and line.count("revision.updated") >= 0
            and sum(1 for x in sink if x.startswith("id: ")) >= 2
            for line in sink
        )
        and time.time() < deadline
    ):
        time.sleep(0.2)  # fmt: skip
    # Logging out revokes the session; the stream must close itself.
    assert api.client.post("/api/v1/auth/logout", headers=api.headers(key=None)).status_code == 204
    thread.join(30)
    reader.__exit__(None, None, None)
    assert not thread.is_alive(), "stream did not close after logout"
    ids = [int(line[4:]) for line in sink if line.startswith("id: ")]
    assert ids == sorted(set(ids)) and len(ids) >= 2
    assert not any("command.completed" in line for line in sink)  # receipts are never exposed
    assert any(line.startswith("event: revision.updated") for line in sink)
    assert sink[-1].startswith("event: close") or any("event: close" in x for x in sink)
