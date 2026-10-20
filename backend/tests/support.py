"""Genuine-record readers and an authenticated API helper shared by story tests."""

import io
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

import pdfplumber
from fastapi.testclient import TestClient
from records import load_record

from verisource.config import Settings

ORIGIN = "http://127.0.0.1:8000"
RECORDS = Path(".local/records")


@dataclass(frozen=True)
class LicenceRow:
    licence_no: str
    firm_name: str
    factory_address: str
    validity: str
    contact_domain: str | None = None  # Company domain of the listed contact email, if any.


FREE_MAIL = {
    "gmail.com",
    "hotmail.com",
    "yahoo.com",
    "yahoo.co.in",
    "outlook.com",
    "rediffmail.com",
}


def _company_domain(contact: str) -> str | None:
    text = "".join(contact.split())  # PDF wraps split addresses across lines.
    at = text.find("@")
    if at < 0:
        return None
    domain = text[at + 1 :].lower().rstrip(".")
    return None if domain in FREE_MAIL or "." not in domain else domain


def licence_rows() -> list[LicenceRow]:
    """Rows of the actual BIS IS 9473 licence PDF (historical, 27 Aug 2020 cutoff)."""
    _manifest, content = load_record(RECORDS / "bis-licences.manifest.json")
    rows: list[LicenceRow] = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for table in pdf.pages[0].extract_tables():
            for row in table:
                if row and row[0] and row[0].strip().isdigit() and row[1] and row[2]:
                    rows.append(
                        LicenceRow(
                            row[1].strip(),
                            " ".join(row[2].split()),
                            " ".join((row[3] or "").split()),
                            (row[6] or "").strip(),
                            _company_domain(row[4] or ""),
                        )
                    )
    assert rows, "The actual licence PDF yielded no rows"
    return rows


def tender_description() -> str:
    """Verbatim English description line of the actual BIS public procurement request."""
    _manifest, content = load_record(RECORDS / "bis-procurement.manifest.json")
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        text = pdf.pages[3].extract_text() or ""
    marker = "Supply, Installation and"
    start = text.index(marker)
    snippet = " ".join(text[start : start + 140].split())
    assert "Universal Testing Machine" in text
    return snippet.split(" (Please")[0].strip()


class Api:
    """Signed-in same-origin client that attaches CSRF, Origin and idempotency headers."""

    def __init__(self, client: TestClient, username: str, password: str) -> None:
        self.client = client
        token = client.get("/api/v1/auth/csrf").json()["csrf_token"]
        response = client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": password},
            headers={"Origin": ORIGIN, "X-CSRF-Token": token},
        )
        assert response.status_code == 200, response.text
        self.csrf = response.json()["csrf_token"]

    def headers(
        self, *, key: str | None = "auto", etag: str | None = None, csrf: bool = True
    ) -> dict[str, str]:
        headers = {"Origin": ORIGIN}
        if csrf:
            headers["X-CSRF-Token"] = self.csrf
        if key == "auto":
            headers["Idempotency-Key"] = str(uuid4())
        elif key:
            headers["Idempotency-Key"] = key
        if etag:
            headers["If-Match"] = etag
        return headers

    def get(self, path: str) -> Any:
        return self.client.get(f"/api/v1{path}")

    def post(
        self,
        path: str,
        body: dict[str, Any] | None = None,
        *,
        key: str | None = "auto",
        etag: str | None = None,
        csrf: bool = True,
    ) -> Any:
        return self.client.post(
            f"/api/v1{path}",
            json=body if body is not None else {},
            headers=self.headers(key=key, etag=etag, csrf=csrf),
        )

    def patch(self, path: str, body: dict[str, Any], *, etag: str | None = None) -> Any:
        return self.client.patch(
            f"/api/v1{path}", json=body, headers=self.headers(key=str(uuid4()), etag=etag)
        )


def supplier_entries(count: int = 4) -> list[dict[str, Any]]:
    return [
        {
            "display_name": row.firm_name,
            "identifiers": [{"type": "name", "value": row.firm_name}],
            "address": row.factory_address,
        }
        for row in licence_rows()[:count]
    ]


def create_case(api: Api, *, count: int = 4) -> dict[str, Any]:
    response = api.post(
        "/cases",
        {
            "title": "Actual BIS UTM tender with historical licence-list suppliers",
            "initial_text": tender_description(),
            "suppliers": supplier_entries(count),
        },
    )
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def confirm_revision(api: Api, created: dict[str, Any]) -> dict[str, Any]:
    case_id, revision = created["case"]["id"], created["revision"]
    patched = api.patch(
        f"/cases/{case_id}/revisions/{revision['id']}",
        {
            "requirements": {
                "part_description": tender_description(),
                "certifications": ["IS 9473"],
            },
            "location": {"country": "IN"},
        },
        etag=revision["etag"],
    )
    assert patched.status_code == 200, patched.text
    confirmed = api.post(
        f"/cases/{case_id}/revisions/{revision['id']}/confirm",
        etag=patched.json()["etag"],
    )
    assert confirmed.status_code == 200, confirmed.text
    body: dict[str, Any] = confirmed.json()
    return body


def propose_checklist(api: Api, case_id: str, revision_id: str) -> dict[str, Any]:
    response = api.post(f"/cases/{case_id}/revisions/{revision_id}/claims")
    assert response.status_code == 202, response.text
    checklist: dict[str, Any] = response.json()["checklist"]
    return checklist


def admitted_run(api: Api, *, count: int = 4, mode: str = "live") -> dict[str, Any]:
    """Create, confirm and admit a real-input case; returns ids for downstream assertions."""
    created = create_case(api, count=count)
    case_id = created["case"]["id"]
    revision = confirm_revision(api, created)
    checklist = propose_checklist(api, case_id, revision["id"])
    path = f"/cases/{case_id}/checklists/{checklist['id']}"
    required = [c["id"] for c in checklist["claims"] if c["type"] == "legal_existence"]
    edited = api.patch(
        path,
        {"claims": [{"id": cid, "required_for_shortlist": True} for cid in required]},
        etag=checklist["etag"],
    )
    assert edited.status_code == 200, edited.text
    confirmed = api.post(f"{path}/confirm", etag=edited.json()["etag"])
    assert confirmed.status_code == 200, confirmed.text
    etag = api.get(f"/cases/{case_id}").headers["ETag"]
    run = api.post(
        f"/cases/{case_id}/runs",
        {"revision_id": revision["id"], "checklist_id": checklist["id"], "mode": mode},
        etag=etag,
    )
    assert run.status_code == 202, run.text
    return {
        "case_id": case_id,
        "revision_id": revision["id"],
        "checklist_id": checklist["id"],
        "run_id": run.json()["run"]["id"],
        "suppliers": created["revision"]["suppliers"],
    }


def start_run(api: Api, rows: list[Any]) -> dict[str, Any]:
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
    ).json()
    case_id, revision = created["case"]["id"], created["revision"]
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
    ).json()
    confirmed = api.post(
        f"/cases/{case_id}/revisions/{revision['id']}/confirm", etag=patched["etag"]
    ).json()
    checklist = api.post(f"/cases/{case_id}/revisions/{revision['id']}/claims").json()["checklist"]
    required = [
        c["id"] for c in checklist["claims"] if c["type"] in {"legal_existence", "regulatory"}
    ]
    edited = api.patch(
        f"/cases/{case_id}/checklists/{checklist['id']}",
        {"claims": [{"id": cid, "required_for_shortlist": True} for cid in required]},
        etag=checklist["etag"],
    ).json()
    assert (
        api.post(
            f"/cases/{case_id}/checklists/{checklist['id']}/confirm", etag=edited["etag"]
        ).status_code
        == 200
    )
    etag = api.get(f"/cases/{case_id}").headers["ETag"]
    run = api.post(
        f"/cases/{case_id}/runs",
        {"revision_id": confirmed["id"], "checklist_id": checklist["id"], "mode": "live"},
        etag=etag,
    )
    assert run.status_code == 202, run.text
    return {
        "case_id": case_id,
        "run_id": run.json()["run"]["id"],
        "revision_id": confirmed["id"],
        "checklist": checklist,
    }


def drain(settings: Settings, engine: Any, owner: str = "test-worker") -> int:
    from verisource.orchestration.executors import Executor
    from verisource.orchestration.worker import build_handlers, run_once

    handlers = build_handlers(settings, engine, Executor(settings, engine, router=None))
    count = 0
    while run_once(engine, handlers, owner=owner):
        count += 1
        assert count < 200, "worker did not converge"
    return count
