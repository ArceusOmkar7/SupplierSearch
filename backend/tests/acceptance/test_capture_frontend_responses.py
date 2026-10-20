"""Record actual API responses of the US1 journey for the frontend component tests.

Inputs are the actual BIS licence-list suppliers and tender. Only responses are recorded
(never cookies or CSRF tokens). Running this test rewrites frontend/tests/captures/.
"""

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from support import ORIGIN, RECORDS, Api, drain, licence_rows, tender_description

from verisource.api.app import create_app
from verisource.config import REPO_ROOT, Settings
from verisource.country_packs.india.bis import ingest_qco_catalog
from verisource.db.checkpoints import checkpointer
from verisource.sources.imports import import_source_dataset
from verisource.storage.filesystem import PrivateFileStore

pytestmark = [pytest.mark.integration, pytest.mark.real_records]
OUT = REPO_ROOT / "frontend/tests/captures"


def save(name: str, body: Any, etag: str | None = None) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.json").write_text(
        json.dumps({"etag": etag, "body": body}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def test_record_us1_journey(buyer_pair: tuple[Settings, str, str, str]) -> None:
    settings, first, _second, password = buyer_pair
    engine = create_engine(settings.database_url.get_secret_value(), hide_parameters=True)
    with checkpointer(settings, initialize=True):
        pass
    store = PrivateFileStore(settings.data_root / "corpus")
    with Session(engine) as db, db.begin():
        import_source_dataset(db, store, RECORDS / "bis-licences.manifest.json")
        ingest_qco_catalog(db, store, RECORDS / "bis-qco-scheme1.manifest.json")
    rows = [licence_rows()[0], licence_rows()[2]]
    with TestClient(create_app(settings), base_url=ORIGIN) as client:
        api = Api(client, first, password)
        created = api.post(
            "/cases",
            {
                "title": "Actual BIS tender, licence-list suppliers",
                "initial_text": tender_description(),
                "suppliers": [
                    {
                        "display_name": row.firm_name,
                        "identifiers": [
                            {"type": "name", "value": row.firm_name},
                            {"type": "licence_number", "value": row.licence_no},
                        ],
                        "address": row.factory_address,
                        "address_role": "production_site",
                    }
                    for row in rows
                ],
            },
        )
        draft = created.json()
        save("case-created", draft, created.headers.get("ETag"))
        case_id, revision = draft["case"]["id"], draft["revision"]
        patched = api.patch(
            f"/cases/{case_id}/revisions/{revision['id']}",
            {
                "requirements": {
                    "part_description": tender_description(),
                    "certifications": ["IS 9473"],
                    "standards": ["IS 9473"],
                },
                "location": {"country": "IN"},
            },
            etag=revision["etag"],
        )
        save("revision-edited", patched.json(), patched.headers.get("ETag"))
        confirmed = api.post(
            f"/cases/{case_id}/revisions/{revision['id']}/confirm", etag=patched.json()["etag"]
        )
        save("revision-confirmed", confirmed.json(), confirmed.headers.get("ETag"))
        proposed = api.post(f"/cases/{case_id}/revisions/{revision['id']}/claims")
        checklist = proposed.json()["checklist"]
        save("checklist-proposed", checklist, proposed.headers.get("ETag"))
        required = [
            c["id"] for c in checklist["claims"] if c["type"] in {"legal_existence", "regulatory"}
        ]
        edited = api.patch(
            f"/cases/{case_id}/checklists/{checklist['id']}",
            {"claims": [{"id": i, "required_for_shortlist": True} for i in required]},
            etag=checklist["etag"],
        )
        done = api.post(
            f"/cases/{case_id}/checklists/{checklist['id']}/confirm", etag=edited.json()["etag"]
        )
        save("checklist-confirmed", done.json(), done.headers.get("ETag"))
        case_etag = api.get(f"/cases/{case_id}").headers["ETag"]
        run = api.post(
            f"/cases/{case_id}/runs",
            {
                "revision_id": confirmed.json()["id"],
                "checklist_id": checklist["id"],
                "mode": "live",
            },
            etag=case_etag,
        )
        save("run-queued", run.json(), run.headers.get("ETag"))
        run_id = run.json()["run"]["id"]
        drain(settings, engine)
        finished = api.get(f"/cases/{case_id}/runs/{run_id}")
        save("run-finished", finished.json(), finished.headers.get("ETag"))
        save("run-attempts", api.get(f"/cases/{case_id}/runs/{run_id}/attempts").json())
        detail = api.get(f"/cases/{case_id}")
        save("case-detail", detail.json(), detail.headers.get("ETag"))
        save("cases-list", api.get("/cases").json())
        listing = api.get(f"/cases/{case_id}/snapshots")
        save("snapshots-list", listing.json())
        snapshot_id = listing.json()["items"][0]["id"]
        snapshot = api.get(f"/cases/{case_id}/snapshots/{snapshot_id}")
        save("snapshot-detail", snapshot.json(), snapshot.headers.get("ETag"))
        content = snapshot.json()["content"]
        first_claim = next(
            c for s in content["suppliers"] for c in s["claims"] if c["evidence"] or c["considered"]
        )
        shown = first_claim["evidence"] or first_claim["considered"]
        evidence_id = shown[0].get("id") or shown[0]["evidence_id"]
        save("evidence-detail", api.get(f"/cases/{case_id}/evidence/{evidence_id}").json())
        attempt_id = first_claim["attempts"][0]["id"] if first_claim["attempts"] else None
        if attempt_id:
            save("attempt-detail", api.get(f"/cases/{case_id}/attempts/{attempt_id}").json())
        follow_up = content["lists"]["follow_up"][0]
        decision = api.post(
            f"/cases/{case_id}/decisions",
            {
                "snapshot_id": snapshot_id,
                "decision": "select",
                "supplier_id": follow_up,
                "reason": "Request the missing certificate before ordering",
            },
            etag=api.get(f"/cases/{case_id}").headers["ETag"],
        )
        save("decision-created", decision.json(), decision.headers.get("ETag"))
        save("actions-empty", api.get(f"/cases/{case_id}/actions?state=pending").json())
    engine.dispose()
    assert (OUT / "run-finished.json").exists()
