"""US2 contracts on a real run over actual BIS records: snapshots, evidence, decisions."""

from typing import Any
from uuid import UUID

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from support import drain, licence_rows, start_run

from verisource.db.models import (
    AssessmentSnapshot,
    Case,
    CheckAttempt,
    EvidenceRecord,
    VerificationRun,
)
from verisource.domain.snapshots import publish_snapshot

pytestmark = [pytest.mark.integration, pytest.mark.real_records]


def finished_run(world: tuple[Any, ...]) -> dict[str, Any]:
    settings, engine, api, _other = world
    started = start_run(api, [licence_rows()[0], licence_rows()[2]])
    drain(settings, engine)
    listing = api.get(f"/cases/{started['case_id']}/snapshots").json()
    assert listing["items"], "completion publishes a snapshot"
    started["snapshot_id"] = listing["items"][0]["id"]
    return started


def test_snapshot_reads_are_owner_scoped_and_show_truthful_coverage(
    us1_world: tuple[Any, ...],
) -> None:
    _settings, _engine, api, other = us1_world
    run = finished_run(us1_world)
    case_id, snapshot_id = run["case_id"], run["snapshot_id"]
    detail = api.get(f"/cases/{case_id}/snapshots/{snapshot_id}")
    assert detail.status_code == 200 and detail.headers["Cache-Control"] == "no-store"
    body = detail.json()
    content = body["content"]
    suppliers = content["suppliers"]
    assert len(suppliers) == 2
    claims = [c for s in suppliers for c in s["claims"]]
    assert claims and {c["verdict"] for c in claims} <= {"proven", "unproven", "contradicted"}
    assert all(c["reasoning"] and c["gaps"] is not None for c in claims)
    # The actual export is historical: nothing is qualified, and the empty list is explicit.
    assert content["lists"]["qualified"] == []
    assert len(content["lists"]["follow_up"]) == 2
    assert content["coverage"]["requests_not_sent"] > 0  # skipped checks never claim a dispatch
    assert content["run"]["mode"] == "live" and body["partial"] is False
    assert other.get(f"/cases/{case_id}/snapshots").status_code == 404
    assert other.get(f"/cases/{case_id}/snapshots/{snapshot_id}").status_code == 404
    assert api.get(f"/cases/{case_id}/snapshots/{UUID(int=0)}").status_code == 404


def test_evidence_and_attempt_detail_keep_originals_dates_and_lineage(
    us1_world: tuple[Any, ...],
) -> None:
    _settings, engine, api, other = us1_world
    run = finished_run(us1_world)
    case_id = run["case_id"]
    with Session(engine) as db:
        evidence = db.scalars(
            select(EvidenceRecord).where(EvidenceRecord.case_id == UUID(case_id))
        ).first()
        attempt = db.scalars(
            select(CheckAttempt).where(CheckAttempt.case_id == UUID(case_id))
        ).first()
        assert evidence is not None and attempt is not None
        evidence_id, attempt_id = str(evidence.id), str(attempt.id)
    item = api.get(f"/cases/{case_id}/evidence/{evidence_id}").json()
    assert item["observation"] and item["issued_at"].startswith("2020-08-27")
    assert item["identity"]["state"] == "confirmed"
    assert item["origin_lineage"].startswith("dataset:")
    shown = api.get(f"/cases/{case_id}/attempts/{attempt_id}").json()
    assert shown["outcome"] and "request_dispatched" in shown
    for path in (
        f"/cases/{case_id}/evidence/{evidence_id}",
        f"/cases/{case_id}/attempts/{attempt_id}",
    ):
        assert other.get(path).status_code == 404


def test_decisions_are_explicit_snapshot_bound_and_leave_verdicts_unchanged(
    us1_world: tuple[Any, ...],
) -> None:
    _settings, engine, api, other = us1_world
    run = finished_run(us1_world)
    case_id, snapshot_id = run["case_id"], run["snapshot_id"]
    content = api.get(f"/cases/{case_id}/snapshots/{snapshot_id}").json()["content"]
    follow_up = content["lists"]["follow_up"][0]
    etag = api.get(f"/cases/{case_id}").headers["ETag"]
    body = {"snapshot_id": snapshot_id, "decision": "select", "supplier_id": follow_up}

    # Selecting a supplier whose required claims are unproven needs an explicit reason.
    assert api.post(f"/cases/{case_id}/decisions", body, etag=etag).status_code == 422
    chosen = api.post(
        f"/cases/{case_id}/decisions", {**body, "reason": "Will request documents"}, etag=etag
    )
    assert chosen.status_code == 201, chosen.text
    assert chosen.json()["decision"]["supplier_id"] == follow_up
    assert (
        api.post(f"/cases/{case_id}/decisions", {**body, "reason": "again"}, etag=etag).status_code
        == 412
    )
    new_etag = api.get(f"/cases/{case_id}").headers["ETag"]
    assert other.post(f"/cases/{case_id}/decisions", body, etag=new_etag).status_code == 404
    bad = {"snapshot_id": snapshot_id, "decision": "no_selection", "supplier_id": follow_up}
    assert api.post(f"/cases/{case_id}/decisions", bad, etag=new_etag).status_code == 422
    nobody = api.post(
        f"/cases/{case_id}/decisions",
        {"snapshot_id": snapshot_id, "decision": "no_selection"},
        etag=new_etag,
    )
    assert nobody.status_code == 201

    detail = api.get(f"/cases/{case_id}/snapshots/{snapshot_id}").json()
    assert [d["decision"] for d in detail["decisions"]] == ["select", "no_selection"]
    assert detail["content"] == content  # decisions never rewrite verdicts or lists
    with Session(engine) as db, pytest.raises(DBAPIError):
        db.execute(
            text("UPDATE assessment_snapshots SET trigger = 'updated' WHERE id = :i"),
            {"i": snapshot_id},
        )
        db.flush()


def differences(a: Any, b: Any, path: str = "") -> list[str]:
    if isinstance(a, dict) and isinstance(b, dict):
        return [
            d
            for k in sorted(set(a) | set(b))
            for d in differences(a.get(k), b.get(k), f"{path}/{k}")
        ]
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        return [
            d
            for i, (x, y) in enumerate(zip(a, b, strict=True))
            for d in differences(x, y, f"{path}[{i}]")
        ]
    return [] if a == b else [f"{path}: {str(a)[:100]} != {str(b)[:100]}"]


def test_republishing_unchanged_state_creates_no_duplicate_snapshot(
    us1_world: tuple[Any, ...],
) -> None:
    _settings, engine, api, _other = us1_world
    run = finished_run(us1_world)
    case_id = run["case_id"]
    with Session(engine) as db:
        first = db.scalars(
            select(AssessmentSnapshot)
            .where(AssessmentSnapshot.case_id == UUID(case_id))
            .order_by(AssessmentSnapshot.sequence.desc())
        ).first()
        assert first is not None
        digest, stored = first.content_hash, first.content_json
        before = db.scalar(
            select(func.count())
            .select_from(AssessmentSnapshot)
            .where(AssessmentSnapshot.case_id == UUID(case_id))
        )
    with Session(engine) as db, db.begin():
        case = db.get(Case, UUID(case_id))
        run_row = db.scalars(
            select(VerificationRun).where(VerificationRun.case_id == UUID(case_id))
        ).one()
        assert case is not None
        again = publish_snapshot(db, case, run_row, "updated")
        assert again is not None
        changed = differences(stored, again.content_json)
        assert again.content_hash == digest, changed
    items = api.get(f"/cases/{case_id}/snapshots").json()["items"]
    assert len(items) == before and items[0]["content_hash"] == digest
