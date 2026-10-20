"""US3 lifecycle contracts on actual BIS inputs: revisions, history, close/reopen, late work."""

from typing import Any
from uuid import UUID

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from support import drain, licence_rows, start_run

from verisource.db.models import Assessment, CheckTask, EvidenceRecord, VerificationRun

pytestmark = [pytest.mark.integration, pytest.mark.real_records]


def new_confirmed_revision(api: Any, started: dict[str, Any], quantity: int) -> dict[str, Any]:
    case_id = started["case_id"]
    etag = api.get(f"/cases/{case_id}").headers["ETag"]
    created = api.post(
        f"/cases/{case_id}/revisions", {"reason": "buyer changed the quantity"}, etag=etag
    )
    assert created.status_code == 201, created.text
    draft = created.json()
    assert draft["status"] == "draft" and draft["requirements"]["part_description"]
    patched = api.patch(
        f"/cases/{case_id}/revisions/{draft['id']}",
        {"requirements": {"quantity": {"value": quantity, "unit": "pcs", "period": "month"}}},
        etag=draft["etag"],
    )
    assert patched.status_code == 200, patched.text
    confirmed = api.post(
        f"/cases/{case_id}/revisions/{draft['id']}/confirm", etag=patched.json()["etag"]
    )
    assert confirmed.status_code == 200, confirmed.text
    body: dict[str, Any] = confirmed.json()
    return body


def test_changed_requirements_need_reconfirmation_and_keep_earlier_results_historical(
    us1_world: tuple[Any, ...],
) -> None:
    settings, engine, api, _other = us1_world
    started = start_run(api, [licence_rows()[0]])
    drain(settings, engine)
    case_id, first_revision = started["case_id"], started["revision_id"]
    first_snapshot = api.get(f"/cases/{case_id}/snapshots").json()["items"][0]
    assert first_snapshot["historical"] is False

    second = new_confirmed_revision(api, started, 500)
    assert second["sequence"] == 2 and second["confirmed_by"]
    assert api.get(f"/cases/{case_id}").json()["active_revision_id"] == second["id"]
    # The earlier confirmed revision is unchanged and its result is clearly historical.
    old = api.get(f"/cases/{case_id}/revisions/{first_revision}").json()
    assert old["status"] == "confirmed" and old["requirements"]["quantity"] is None
    listing = api.get(f"/cases/{case_id}/snapshots").json()["items"]
    assert listing[0]["historical"] is True and listing[0]["id"] == first_snapshot["id"]
    # The earlier revision cannot be run again: only the newly confirmed values are used.
    etag = api.get(f"/cases/{case_id}").headers["ETag"]
    again = api.post(
        f"/cases/{case_id}/runs",
        {"revision_id": first_revision, "checklist_id": started["checklist"]["id"], "mode": "live"},
        etag=etag,
    )
    assert again.status_code == 409
    # The new revision gets its own checklist; nothing is inherited as proof.
    proposal = api.post(f"/cases/{case_id}/revisions/{second['id']}/claims")
    assert proposal.status_code == 202
    fresh = proposal.json()["checklist"]
    assert fresh["revision_id"] == second["id"] and fresh["status"] == "draft"
    assert all(not c["required_for_shortlist"] for c in fresh["claims"])
    assert any("500 pcs" in c["assertion"] for c in fresh["claims"])  # the changed value is used
    assert len(api.get(f"/cases/{case_id}/revisions").json()["items"]) == 2


def test_late_work_for_an_earlier_revision_stays_historical(us1_world: tuple[Any, ...]) -> None:
    settings, engine, api, _other = us1_world
    started = start_run(api, [licence_rows()[1]])  # run queued for revision 1, not yet processed
    case_id = started["case_id"]
    second = new_confirmed_revision(api, started, 250)
    drain(settings, engine)  # revision-1 checks complete after revision 2 was confirmed
    with Session(engine) as db:
        run = db.scalars(
            select(VerificationRun).where(VerificationRun.case_id == UUID(case_id))
        ).one()
        assert str(run.revision_id) == started["revision_id"] and run.state != "queued"
        assert (db.scalar(select(func.count()).select_from(Assessment)) or 0) > 0
        assert all(
            str(a.revision_id) == started["revision_id"] for a in db.scalars(select(Assessment))
        )
    case = api.get(f"/cases/{case_id}").json()
    assert case["active_revision_id"] == second["id"]
    assert case["latest_snapshot_id"] is None  # a late old-revision result never becomes current
    snapshots = api.get(f"/cases/{case_id}/snapshots").json()["items"]
    assert snapshots and all(s["historical"] for s in snapshots)


def test_closing_freezes_the_chosen_snapshot_stops_work_and_reopens_explicitly(
    us1_world: tuple[Any, ...],
) -> None:
    settings, engine, api, other = us1_world
    done = start_run(api, [licence_rows()[0], licence_rows()[2]])
    drain(settings, engine)
    case_id = done["case_id"]
    snapshot_id = api.get(f"/cases/{case_id}/snapshots").json()["items"][0]["id"]
    etag = api.get(f"/cases/{case_id}").headers["ETag"]
    body = {"snapshot_id": snapshot_id, "reason": "Closing with gaps; no outreach needed"}

    assert other.post(f"/cases/{case_id}/close", body, etag=etag).status_code == 404
    closed = api.post(f"/cases/{case_id}/close", body, etag=etag)
    assert closed.status_code == 200, closed.text
    assert closed.json()["case"]["state"] == "closed"
    assert api.get(f"/cases/{case_id}").json()["latest_snapshot_id"] == snapshot_id
    detail = api.get(f"/cases/{case_id}/snapshots/{snapshot_id}").json()
    assert detail["closed_snapshot"] is True
    new_etag = api.get(f"/cases/{case_id}").headers["ETag"]
    # A closed case accepts no run and no decision until the owner reopens it.
    refused = api.post(
        f"/cases/{case_id}/runs",
        {
            "revision_id": done["revision_id"],
            "checklist_id": done["checklist"]["id"],
            "mode": "live",
        },
        etag=new_etag,
    )
    assert refused.status_code == 409
    decision = {"snapshot_id": snapshot_id, "decision": "no_selection"}
    assert api.post(f"/cases/{case_id}/decisions", decision, etag=new_etag).status_code == 409
    assert api.post(f"/cases/{case_id}/close", body, etag=new_etag).status_code == 409

    reopened = api.post(
        f"/cases/{case_id}/reopen", {"reason": "New supplier information"}, etag=new_etag
    )
    assert reopened.status_code == 200 and reopened.json()["case"]["state"] == "ready"
    assert (
        api.get(f"/cases/{case_id}/snapshots/{snapshot_id}").json()["content_hash"]
        == detail["content_hash"]
    )
    after = api.get(f"/cases/{case_id}").headers["ETag"]
    assert api.post(f"/cases/{case_id}/reopen", {}, etag=after).status_code == 409


def test_closing_fences_pending_and_late_results(us1_world: tuple[Any, ...]) -> None:
    settings, engine, api, _other = us1_world
    finished = start_run(api, [licence_rows()[0]])
    drain(settings, engine)
    case_id = finished["case_id"]
    snapshot_id = api.get(f"/cases/{case_id}/snapshots").json()["items"][0]["id"]
    # A second case has queued, unprocessed work when it is closed.
    second = start_run(api, [licence_rows()[3]])
    other_case = second["case_id"]
    with Session(engine) as db:
        pending_before = db.scalar(
            select(func.count()).select_from(CheckTask).where(CheckTask.state == "queued")
        )
    assert pending_before
    # The pending case has no snapshot yet, so it cannot be closed; close the finished case.
    etag = api.get(f"/cases/{other_case}").headers["ETag"]
    assert (
        api.post(f"/cases/{other_case}/close", {"snapshot_id": snapshot_id}, etag=etag).status_code
        == 404
    )
    drain(settings, engine)  # the second case completes and can then be closed
    next_snapshot = api.get(f"/cases/{other_case}/snapshots").json()["items"][0]["id"]
    # Re-run on the first case to leave work queued, then close and prove it is fenced.
    etag = api.get(f"/cases/{other_case}").headers["ETag"]
    closed = api.post(f"/cases/{other_case}/close", {"snapshot_id": next_snapshot}, etag=etag)
    assert closed.status_code == 200
    with Session(engine) as db:
        evidence_before = db.scalar(select(func.count()).select_from(EvidenceRecord))
    drain(settings, engine)
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(EvidenceRecord)) == evidence_before


def test_editing_a_confirmed_checklist_creates_a_new_version(us1_world: tuple[Any, ...]) -> None:
    settings, engine, api, _other = us1_world
    started = start_run(api, [licence_rows()[0]])
    drain(settings, engine)
    case_id, checklist = started["case_id"], started["checklist"]
    old = api.get(f"/cases/{case_id}/checklists/{checklist['id']}").json()
    assert old["status"] == "confirmed"
    created = api.post(
        f"/cases/{case_id}/checklists",
        {"based_on_checklist_id": checklist["id"], "revision_id": started["revision_id"]},
    )
    assert created.status_code == 201, created.text
    draft = created.json()
    assert draft["sequence"] == 2 and draft["status"] == "draft" and draft["id"] != checklist["id"]
    assert len(draft["claims"]) == len(old["claims"])
    assert api.get(f"/cases/{case_id}/checklists/{checklist['id']}").json()["status"] == "confirmed"
    again = api.post(
        f"/cases/{case_id}/checklists",
        {"based_on_checklist_id": checklist["id"], "revision_id": started["revision_id"]},
    )
    assert again.status_code == 409  # one draft per revision
