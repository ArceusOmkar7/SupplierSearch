"""Certificate reading on an actual supplier-published certificate PDF.

The PDF is the real DNV ISO 9001:2015 certificate that Ghatge Patil Industries publishes on its
website (valid 30 Sep 2023 - 29 Sep 2026, so it has expired at the time of this run). It is used
as supplied; no field is edited. The local model check asserts quotation support, not accuracy.
"""

from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from support import RECORDS, drain

from verisource.config import Settings
from verisource.db.models import Assessment, DocumentArtifact, EvidenceRecord, Extraction
from verisource.documents.certificates import extract_certificate, inspect_pdf
from verisource.models.ollama import ModelUnavailable
from verisource.models.router import ModelRouter
from verisource.models.schemas import parse_date
from verisource.sources.manifests import load_record

pytestmark = [pytest.mark.real_records]
CERT = RECORDS / "gpi-iso9001-certificate.manifest.json"


def test_rule_extraction_reads_the_actual_certificate_with_verified_quotes() -> None:
    _manifest, content = load_record(CERT)
    inspection = inspect_pdf(content)
    assert inspection.failure_reason is None and inspection.text_pages == [1]
    fields, method, missing = extract_certificate(None, inspection)
    assert method == "rule"
    assert fields.certificate_number is not None and fields.certificate_number.value == "C615162"
    assert fields.standard is not None and fields.standard.value == "ISO 9001:2015"
    assert fields.expiry_date is not None
    expiry = parse_date(fields.expiry_date.value)
    assert expiry is not None and expiry.isoformat() == "2026-09-29"
    assert "holder_name" in missing  # not stated in a rule-readable form; stays unknown
    page = " ".join(inspection.pages[1].split())
    for name in ("certificate_number", "standard", "issue_date", "expiry_date"):
        assert " ".join(getattr(fields, name).quote.split()) in page


@pytest.mark.live
def test_local_model_proposals_are_quote_checked_against_the_certificate() -> None:
    _manifest, content = load_record(CERT)
    inspection = inspect_pdf(content)
    router = ModelRouter(Settings())
    try:
        from verisource.models.ollama import OllamaClient

        OllamaClient(Settings()).verify_installed()
    except ModelUnavailable as exc:
        pytest.skip(f"Missing prerequisite: pinned local model ({exc})")
    fields, method, _missing = extract_certificate(router, inspection)
    page = " ".join(inspection.pages[1].split()).casefold()
    if method == "rule":  # The local model did not answer (cold start or busy): not a result.
        pytest.skip(f"Missing prerequisite: local model unavailable ({fields.uncertainties})")
    assert method.startswith("model:ollama")
    for name in ("certificate_number", "holder_name", "issuer", "standard", "scope", "site_address",
                 "issue_date", "expiry_date"):  # fmt: skip
        located = getattr(fields, name)
        if located is not None:  # Everything kept must be quoted from the actual page.
            assert " ".join(located.quote.split()).casefold() in page, name
    # The rule-based quoted fields survive the merge regardless of what the model proposed.
    assert fields.certificate_number is not None and fields.certificate_number.value == "C615162"


def test_uploaded_certificate_is_read_but_is_not_proof(
    buyer_pair: tuple[Settings, str, str, str],
) -> None:
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from support import ORIGIN, Api

    from verisource.api.app import create_app
    from verisource.db.checkpoints import checkpointer

    settings, first, _second, password = buyer_pair
    engine = create_engine(settings.database_url.get_secret_value(), hide_parameters=True)
    with checkpointer(settings, initialize=True):
        pass
    _manifest, content = load_record(CERT)
    name = "Ghatge Patil Industries Ltd."
    with TestClient(create_app(settings), base_url=ORIGIN) as client:
        api = Api(client, first, password)
        created = api.post(
            "/cases",
            {
                "title": "Actual published ISO 9001 certificate",
                "suppliers": [
                    {"display_name": name, "identifiers": [{"type": "name", "value": name}]}
                ],
            },
        ).json()
        case_id, revision = created["case"]["id"], created["revision"]
        patched = api.patch(
            f"/cases/{case_id}/revisions/{revision['id']}",
            {
                "requirements": {
                    "part_description": "Grey and SG iron castings",
                    "certifications": ["ISO 9001:2015"],
                },
                "location": {"country": "IN"},
            },
            etag=revision["etag"],
        ).json()
        confirmed = api.post(
            f"/cases/{case_id}/revisions/{revision['id']}/confirm", etag=patched["etag"]
        ).json()
        supplier_id = revision["suppliers"][0]["supplier_id"]
        upload = api.client.post(
            f"/api/v1/cases/{case_id}/documents",
            files={"file": ("certificate.pdf", content, "application/pdf")},
            data={"supplier_id": supplier_id, "revision_id": revision["id"]},
            headers=api.headers(key=None),
        )
        assert upload.status_code == 202, upload.text
        checklist = api.post(f"/cases/{case_id}/revisions/{revision['id']}/claims").json()[
            "checklist"
        ]
        required = [c["id"] for c in checklist["claims"] if c["type"] == "certificate"]
        edited = api.patch(
            f"/cases/{case_id}/checklists/{checklist['id']}",
            {"claims": [{"id": i, "required_for_shortlist": True} for i in required]},
            etag=checklist["etag"],
        ).json()
        api.post(f"/cases/{case_id}/checklists/{checklist['id']}/confirm", etag=edited["etag"])
        etag = api.get(f"/cases/{case_id}").headers["ETag"]
        run = api.post(
            f"/cases/{case_id}/runs",
            {"revision_id": confirmed["id"], "checklist_id": checklist["id"], "mode": "live"},
            etag=etag,
        ).json()["run"]
    drain(settings, engine)

    with Session(engine) as db:
        document = db.scalars(
            select(DocumentArtifact).where(DocumentArtifact.case_id == UUID(case_id))
        ).one()
        assert document.origin == "buyer_upload" and document.state == "extracted"
        extraction = db.scalars(
            select(Extraction).where(Extraction.case_id == UUID(case_id))
        ).first()
        assert (
            extraction is not None and extraction.fields["certificate_number"]["value"] == "C615162"
        )
        evidence = list(
            db.scalars(select(EvidenceRecord).where(EvidenceRecord.run_id == UUID(run["id"])))
        )
        certificate = [e for e in evidence if e.origin_lineage.startswith("document:")]
        assert certificate and all(
            e.self_reported and e.authority_role == "supplier" for e in certificate
        )
        assert "C615162" in certificate[0].observation
        verdicts = {
            a.verdict
            for a in db.scalars(select(Assessment).where(Assessment.run_id == UUID(run["id"])))
        }
        assert verdicts == {"unproven"}  # a supplier-supplied, expired certificate proves nothing
    engine.dispose()
