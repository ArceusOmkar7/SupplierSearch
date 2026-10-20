"""US1 HTTP contracts using actual BIS licence rows and the actual BIS procurement request.

Supplier names and addresses are genuine rows of the historical BIS IS 9473 licence list;
the part description is the verbatim English line of the actual public BIS tender. They
are workflow inputs, not claims that these firms supply the tender item. Credentials,
idempotency keys and oversize padding are disclosed controls, not source facts.
"""

from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from support import (
    ORIGIN,
    RECORDS,
    Api,
    confirm_revision,
    create_case,
    licence_rows,
    propose_checklist,
    supplier_entries,
    tender_description,
)

from verisource.api.app import create_app
from verisource.config import Settings

pytestmark = [pytest.mark.integration, pytest.mark.real_records]


@pytest.fixture
def owner(buyer_pair: tuple[Settings, str, str, str]):  # type: ignore[no-untyped-def]
    settings, first, second, password = buyer_pair
    with (
        TestClient(create_app(settings), base_url=ORIGIN) as one,
        TestClient(create_app(settings), base_url=ORIGIN) as two,
    ):
        yield Api(one, first, password), Api(two, second, password)


def test_intake_stays_an_editable_draft_and_creation_is_idempotent(
    owner: tuple[Api, Api],
) -> None:
    api, _other = owner
    body = {
        "title": "Actual BIS UTM tender",
        "initial_text": tender_description(),
        "suppliers": supplier_entries(),
    }
    key = str(uuid4())
    first = api.post("/cases", body, key=key)
    assert first.status_code == 201, first.text
    created = first.json()
    assert created["case"]["state"] == "draft"
    assert created["case"]["active_revision_id"] is None
    assert created["revision"]["status"] == "draft"
    assert created["revision"]["confirmed_at"] is None
    assert [s["display_name"] for s in created["revision"]["suppliers"]] == [
        row.firm_name for row in licence_rows()[:4]
    ]
    # Missing values remain unknown rather than being inferred.
    assert created["revision"]["requirements"]["quantity"] is None
    assert created["revision"]["location"].get("radius") is None

    replay = api.post("/cases", body, key=key)
    assert replay.status_code == 201
    assert replay.json()["case"]["id"] == created["case"]["id"]
    assert len(api.get("/cases").json()["items"]) == 1
    assert api.post("/cases", {**body, "title": "Changed body"}, key=key).status_code == 409
    assert api.post("/cases", body, key=None).status_code == 400
    assert api.post("/cases", body, csrf=False).status_code == 403


def test_revision_edits_need_current_etag_and_valid_fields(owner: tuple[Api, Api]) -> None:
    api, _other = owner
    created = create_case(api)
    case_id, revision = created["case"]["id"], created["revision"]
    path = f"/cases/{case_id}/revisions/{revision['id']}"

    patched = api.patch(
        path, {"requirements": {"part_description": "edited by buyer"}}, etag=revision["etag"]
    )
    assert patched.status_code == 200
    assert patched.json()["requirements"]["part_description"] == "edited by buyer"
    assert patched.json()["etag"] != revision["etag"]
    stale = api.patch(
        path, {"requirements": {"part_description": "stale edit"}}, etag=revision["etag"]
    )
    assert stale.status_code == 412
    assert api.get(path).json()["requirements"]["part_description"] == "edited by buyer"

    current = patched.json()["etag"]
    for invalid in (
        {"requirements": {"quantity": {"value": 0, "unit": "pcs", "period": "total"}}},
        {"requirements": {"quantity": {"value": -3, "unit": "pcs", "period": "total"}}},
        {"location": {"radius": {"value": 50}}},  # radius needs unit and reference location
        {"suppliers": [{"identifiers": [{"type": "gstin", "value": "not-a-gstin"}]}]},
    ):
        rejected = api.patch(path, invalid, etag=current)
        assert rejected.status_code == 422, invalid

    opaque = "https://www.indiamart.com/proddetail/actual-listing-reference.html"
    kept = api.patch(
        path,
        {"suppliers": [{"identifiers": [{"type": "listing_url", "value": opaque}]}]},
        etag=current,
    )
    assert kept.status_code == 200
    assert kept.json()["suppliers"][0]["identifiers"][0]["value"] == opaque


def test_same_identifier_prompts_review_instead_of_merging(owner: tuple[Api, Api]) -> None:
    api, _other = owner
    created = create_case(api, count=2)
    case_id, revision = created["case"]["id"], created["revision"]
    name = licence_rows()[0].firm_name
    response = api.patch(
        f"/cases/{case_id}/revisions/{revision['id']}",
        {
            "suppliers": [
                {"display_name": name, "identifiers": [{"type": "name", "value": name}]},
                {"display_name": name.upper(), "identifiers": [{"type": "name", "value": name}]},
            ]
        },
        etag=revision["etag"],
    )
    assert response.status_code == 200
    assert len(response.json()["suppliers"]) == 2
    assert any(flag["code"] == "shared_identifier" for flag in response.json()["review_flags"])


def test_confirmation_requires_complete_input_and_freezes_the_revision(
    owner: tuple[Api, Api],
) -> None:
    api, _other = owner
    created = create_case(api)
    case_id, revision = created["case"]["id"], created["revision"]
    path = f"/cases/{case_id}/revisions/{revision['id']}"

    # Interpretation text alone is not a confirmed requirement (no part description yet).
    assert api.post(f"{path}/confirm", etag=revision["etag"]).status_code == 422
    assert api.post(f"{path}/claims").status_code == 409  # no claims from draft input

    confirmed = confirm_revision(api, created)
    assert confirmed["status"] == "confirmed"
    assert confirmed["confirmed_at"] is not None and confirmed["confirmed_by"] is not None
    case = api.get(f"/cases/{case_id}").json()
    assert case["active_revision_id"] == revision["id"]
    assert (
        api.patch(
            path, {"requirements": {"part_description": "x"}}, etag=confirmed["etag"]
        ).status_code
        == 409
    )
    assert api.post(f"{path}/confirm", etag=confirmed["etag"]).status_code == 409


def test_checklist_needs_a_required_claim_before_confirmation_and_run_admission(
    owner: tuple[Api, Api],
) -> None:
    api, _other = owner
    created = create_case(api)
    case_id = created["case"]["id"]
    revision = confirm_revision(api, created)
    checklist = propose_checklist(api, case_id, revision["id"])
    types = {claim["type"] for claim in checklist["claims"]}
    assert {"legal_existence", "manufacturer", "part_capability", "certificate"} <= types
    assert all(claim["proof_criteria"]["criteria"] for claim in checklist["claims"])
    assert not any(claim["required_for_shortlist"] for claim in checklist["claims"])
    per_supplier = {claim["supplier_id"] for claim in checklist["claims"]}
    assert len(per_supplier) == 4

    path = f"/cases/{case_id}/checklists/{checklist['id']}"
    run_body = {
        "revision_id": revision["id"],
        "checklist_id": checklist["id"],
        "mode": "live",
    }
    case_etag = api.get(f"/cases/{case_id}").headers["ETag"]
    # Neither confirmation gate may be skipped: no collection from an unconfirmed checklist.
    assert api.post(f"/cases/{case_id}/runs", run_body, etag=case_etag).status_code == 409
    assert api.post(f"{path}/confirm", etag=checklist["etag"]).status_code == 422

    required_ids = [c["id"] for c in checklist["claims"] if c["type"] == "legal_existence"]
    edited = api.patch(
        path,
        {"claims": [{"id": cid, "required_for_shortlist": True} for cid in required_ids]},
        etag=checklist["etag"],
    )
    assert edited.status_code == 200, edited.text
    confirmed = api.post(f"{path}/confirm", etag=edited.json()["etag"])
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "confirmed"
    assert api.patch(path, {"claims": []}, etag=confirmed.json()["etag"]).status_code == 409

    case_etag = api.get(f"/cases/{case_id}").headers["ETag"]
    admitted = api.post(f"/cases/{case_id}/runs", run_body, etag=case_etag)
    assert admitted.status_code == 202, admitted.text
    run = admitted.json()["run"]
    assert run["state"] == "queued" and run["mode"] == "live"
    assert run["initial_deadline"] is not None and run["started_at"] is None
    assert api.get(f"/cases/{case_id}/runs/{run['id']}").json()["run"]["id"] == run["id"]
    assert run["task_count"] > 0

    # A stale case ETag cannot admit another run.
    assert api.post(f"/cases/{case_id}/runs", run_body, etag=case_etag).status_code == 412


def test_cross_case_and_other_owner_references_are_not_found(owner: tuple[Api, Api]) -> None:
    api, other = owner
    created = create_case(api)
    case_id = created["case"]["id"]
    revision = confirm_revision(api, created)
    checklist = propose_checklist(api, case_id, revision["id"])
    second = create_case(api, count=2)

    # Another owner's identifiers produce the same unavailable shape.
    assert other.get(f"/cases/{case_id}").status_code == 404
    assert other.get(f"/cases/{case_id}/revisions/{revision['id']}").status_code == 404
    assert other.get(f"/cases/{case_id}/checklists/{checklist['id']}").status_code == 404
    assert other.post(f"/cases/{case_id}/revisions/{revision['id']}/claims").status_code == 404

    # A same-owner reference from a different case is also unavailable.
    other_case = second["case"]["id"]
    assert api.get(f"/cases/{other_case}/revisions/{revision['id']}").status_code == 404
    assert api.get(f"/cases/{other_case}/checklists/{checklist['id']}").status_code == 404
    etag = api.get(f"/cases/{other_case}").headers["ETag"]
    bad_run = {"revision_id": revision["id"], "checklist_id": checklist["id"], "mode": "live"}
    assert api.post(f"/cases/{other_case}/runs", bad_run, etag=etag).status_code == 404

    api.client.cookies.clear()
    assert api.get(f"/cases/{case_id}").status_code == 401


def test_document_boundary_limits_use_actual_pdfs(owner: tuple[Api, Api]) -> None:
    api, _other = owner
    created = create_case(api, count=1)
    case_id = created["case"]["id"]
    revision = created["revision"]["id"]
    supplier = created["revision"]["suppliers"][0]["supplier_id"]
    fields = {"supplier_id": supplier, "revision_id": revision}

    def upload(name: str, content: bytes, media: str = "application/pdf") -> Any:
        return api.client.post(
            f"/api/v1/cases/{case_id}/documents",
            files={"file": (name, content, media)},
            data=fields,
            headers=api.headers(key=None),
        )

    licence = (RECORDS / "bis-licences.pdf").read_bytes()  # 1 page, actual document
    accepted = upload("licences.pdf", licence)
    assert accepted.status_code == 202, accepted.text
    document = accepted.json()["document"]
    assert document["origin"] == "buyer_upload"
    assert document["sha256"] and "storage_key" not in document
    assert api.get(f"/cases/{case_id}/documents/{document['id']}").status_code == 200

    # The actual 58-page procurement PDF exceeds the 50-page certificate limit.
    tender = (RECORDS / "bis-procurement.pdf").read_bytes()
    assert upload("tender.pdf", tender).status_code == 413
    # Controlled boundary conditions: oversize padding and a non-PDF media type.
    assert upload("padded.pdf", licence + b"\0" * (20 * 1024 * 1024)).status_code == 413
    assert upload("note.txt", b"plain text", "text/plain").status_code == 415
    assert upload("mislabelled.pdf", b"not a pdf document").status_code == 415
