"""India pack building blocks and the shared evidence policy, on actual BIS records.

Positive policy path: the actual BIS IS 9473 licence list shows a firm holding a licence as of
its 27 Aug 2020 cutoff, so a claim dated exactly then is provable from that record. The same
record cannot prove a current claim. State changes applied to genuine rows (an ambiguous
identity, another supplier's claim) are disclosed controls. Natural contradicted examples are
absent and are not invented; the contradiction rule is tested on outcomes only.
"""

import re
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from support import RECORDS, licence_rows
from test_verification_schema import build

from verisource.country_packs.india.bis import (
    applicability_candidates,
    find_dates,
    ingest_qco_catalog,
    standard_codes,
)
from verisource.country_packs.india.identity import assess_candidate, name_similarity
from verisource.country_packs.india.registries import lookup_supplier, official_urls
from verisource.db.models import (
    Assessment,
    Claim,
    EvidenceUse,
    IdentityResolution,
    QcoRecord,
    Supplier,
)
from verisource.domain.claims import POLICY_VERSION, criteria, criterion
from verisource.domain.evidence_policy import assess_checklist, combine, compound
from verisource.orchestration.persistence import persist_observation
from verisource.sources.imports import import_source_dataset
from verisource.storage.filesystem import PrivateFileStore

pytestmark = [pytest.mark.integration, pytest.mark.real_records]


@pytest.fixture
def db(test_database_url: str) -> Iterator[Session]:
    engine = create_engine(test_database_url, hide_parameters=True)
    with engine.connect() as connection, connection.begin() as outer:
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
            yield session
        outer.rollback()
    engine.dispose()


def test_actual_qco_catalogue_is_parsed_with_partial_coverage(db: Session, tmp_path: Path) -> None:
    store = PrivateFileStore(tmp_path)
    dataset, count = ingest_qco_catalog(db, store, RECORDS / "bis-qco-scheme1.manifest.json")
    assert count > 500 and dataset.cutoff_unknown_reason  # no cutoff was verified for the page
    cement = db.scalar(select(QcoRecord).where(QcoRecord.standard_codes.contains(["IS 12330"])))
    assert cement is not None
    assert cement.order_number == "S.O. 191(E)"
    assert cement.issued_on == datetime(2003, 2, 17, tzinfo=UTC)
    assert cement.effective_on is None  # implementation dates live in unread order PDFs
    assert cement.coverage_state == "partial"
    assert db.scalar(select(func.count()).select_from(QcoRecord)) == count
    # Re-importing the same bytes is idempotent.
    again, again_count = ingest_qco_catalog(db, store, RECORDS / "bis-qco-scheme1.manifest.json")
    assert again.id == dataset.id and again_count == count

    assert applicability_candidates(db, standards=["IS 12330"], product_text="")
    assert applicability_candidates(db, standards=["IS 99999"], product_text="") == []
    # Whatever the catalogue holds for IS 9473 must agree with the raw captured page.
    html = (RECORDS / "bis-qco-scheme1.html").read_bytes()
    page_text = BeautifulSoup(html, "html.parser").get_text(" ")
    listed = bool(re.search(r"IS\s*9473\b", page_text))
    assert bool(applicability_candidates(db, standards=["IS 9473"], product_text="")) == listed


def test_date_and_standard_parsers_read_actual_notification_text() -> None:
    text = "Polyurethanes (Quality Control) Order, 2021 (S.O. 3931 (E) dated 13.09.2021)"
    assert find_dates(text) == [datetime(2021, 9, 13, tzinfo=UTC)]
    assert standard_codes("IS 17397 (Part 1) : 2020/ISO 16365-1 : 2014") == ["IS 17397 (Part 1)"]
    assert find_dates("Dt. 17 Feb 2003")[0].month == 2
    assert find_dates("no dates here") == []


def test_only_exact_typed_identifiers_confirm_identity() -> None:
    row, other = licence_rows()[0], licence_rows()[2]
    ids = [{"type": "licence_number", "value": row.licence_no}]
    same = assess_candidate(
        row.firm_name, ids, row.firm_name, {"licence_number": row.licence_no},
        supplier_address=row.factory_address, candidate_address=row.factory_address,
    )  # fmt: skip
    assert same.state == "confirmed" and same.basis == "exact_identifier_match"
    # The identifier matches but the registry names another firm: needs buyer review.
    mismatch = assess_candidate(
        row.firm_name, ids, other.firm_name, {"licence_number": row.licence_no}
    )
    assert mismatch.state == "ambiguous"
    # A different identifier of the same type is a conflict, not a fuzzy match.
    conflict = assess_candidate(
        row.firm_name, ids, row.firm_name, {"licence_number": other.licence_no}
    )
    assert conflict.state == "rejected"
    # A near-identical name alone only proposes a candidate; it never confirms.
    named = assess_candidate(row.firm_name, [], row.firm_name.upper(), {})
    assert named.state == "proposed" and named.score == 1.0
    assert name_similarity(row.firm_name, other.firm_name) < 0.5
    # Differing office/factory addresses are recorded, not treated as contradictions.
    moved = assess_candidate(
        row.firm_name, ids, row.firm_name, {"licence_number": row.licence_no},
        supplier_address="Registered office, 12 Example Marg, Mumbai",
        candidate_address=row.factory_address,
    )  # fmt: skip
    assert moved.state == "confirmed" and any("addresses differ" in d for d in moved.discrepancies)


def test_official_links_are_exact_and_allow_listed() -> None:
    text = (
        "Verify at https://udyamregistration.gov.in/verify/ABC123. "
        "Also https://example.invalid/phish and https://www.bis.gov.in/copyright-policy/?lang=en."
    )
    assert official_urls(text) == [
        "https://udyamregistration.gov.in/verify/ABC123",
        "https://www.bis.gov.in/copyright-policy/?lang=en",
    ]


def test_compound_rules_over_outcomes() -> None:
    assert compound(["proven", "proven"]) == "proven"
    assert compound(["proven", "unproven"]) == "unproven"
    assert compound(["proven", "contradicted", "unproven"]) == "contradicted"
    assert compound([]) == "unproven"  # an empty compound is never vacuously proven
    assert combine(["satisfied", "satisfied"]) == "proven"
    assert combine(["satisfied", "insufficient"]) == "unproven"
    assert combine(["refuted", "satisfied"]) == "contradicted"
    assert combine([]) == "unproven"


def licence_claim(db: Session, built: Any, period: dict[str, Any]) -> Claim:
    _a, case, revision, supplier, checklist, _c, _run, _t = built
    claim = Claim(
        case_id=case.id,
        revision_id=revision.id,
        checklist_id=checklist.id,
        supplier_id=supplier.id,
        type="regulatory",
        assertion="Firm held an IS 9473 licence",
        relevant_period=period,
        required_for_shortlist=True,
        proof_criteria_json=criteria(
            criterion(
                "regulatory.licence",
                "Official licence record",
                "licence_record",
                ["official_publication", "official_registry"],
                independent=False,
                missing="No official licence record",
            )
        ),
    )
    db.add(claim)
    db.flush()
    return claim


def test_actual_licence_record_proves_only_the_dated_claim(db: Session, tmp_path: Path) -> None:
    built = build(db)
    _a, case, revision, supplier, checklist, _c, run, task = built
    row = licence_rows()[0]
    import_source_dataset(db, PrivateFileStore(tmp_path), RECORDS / "bis-licences.manifest.json")
    hits = lookup_supplier(
        db, supplier.display_name, [{"type": "licence_number", "value": row.licence_no}],
        address=row.factory_address,
    )  # fmt: skip
    assert len(hits) == 1 and hits[0].identity.state == "confirmed"
    from dataclasses import replace

    observation = replace(
        hits[0].observation,
        assertion_tags=(*hits[0].observation.assertion_tags, "supports:regulatory.licence"),
    )
    evidence = persist_observation(db, task, run, observation, {})
    dated = licence_claim(db, built, {"kind": "as_of", "as_of": "2020-08-27"})
    current = licence_claim(db, built, {"kind": "current", "as_of": None})
    wrong_date = licence_claim(db, built, {"kind": "as_of", "as_of": "2021-01-01"})
    assessments = {a.claim_id: a for a in assess_checklist(db, run, [dated, current, wrong_date])}

    proven = assessments[dated.id]
    assert proven.verdict == "proven" and proven.evidence_refs == [str(evidence.id)]
    use = db.scalar(select(EvidenceUse).where(EvidenceUse.assessment_id == proven.id))
    assert use is not None and use.role == "supporting" and use.evidence_id == evidence.id
    # The same record cannot prove a present-tense claim or a date outside what it states.
    assert assessments[current.id].verdict == "unproven"
    assert "validity has ended" in " ".join(assessments[current.id].gaps)
    assert assessments[wrong_date.id].verdict == "unproven"
    assert "does not cover the claimed date" in " ".join(assessments[wrong_date.id].gaps)

    # Controlled state change: the identity becomes ambiguous, so the record no longer counts.
    resolution = db.get(IdentityResolution, evidence.identity_resolution_id)
    assert resolution is not None
    resolution.state = "ambiguous"
    db.flush()
    (again,) = assess_checklist(db, run, [dated])
    assert again.verdict == "unproven" and again.sequence == 2  # history is appended
    assert "identity is ambiguous" in " ".join(again.gaps)
    # The earlier proven assessment is still inspectable.
    assert db.get(Assessment, proven.id) is not None and proven.sequence == 1
    del checklist, revision, case


def test_another_suppliers_claim_cannot_use_the_record(db: Session, tmp_path: Path) -> None:
    built = build(db)
    _a, case, revision, supplier, checklist, _c, run, task = built
    row = licence_rows()[0]
    import_source_dataset(db, PrivateFileStore(tmp_path), RECORDS / "bis-licences.manifest.json")
    hit = lookup_supplier(
        db, supplier.display_name, [{"type": "licence_number", "value": row.licence_no}],
        address=None,
    )[0]  # fmt: skip
    from dataclasses import replace

    persist_observation(
        db, task, run,
        replace(hit.observation, assertion_tags=("supports:regulatory.licence",)), {},
    )  # fmt: skip
    other = Supplier(
        case_id=case.id, display_name=licence_rows()[1].firm_name, original_identifiers=[],
        normalized_identifiers=[], source_refs=[],
    )  # fmt: skip
    db.add(other)
    db.flush()
    foreign = Claim(
        case_id=case.id, revision_id=revision.id, checklist_id=checklist.id,
        supplier_id=other.id, type="regulatory", assertion="Other firm held a licence",
        relevant_period={"kind": "as_of", "as_of": "2020-08-27"},
        proof_criteria_json=criteria(
            criterion("regulatory.licence", "Official record", "licence_record",
                      ["official_publication"], independent=False, missing="none")
        ),
    )  # fmt: skip
    db.add(foreign)
    db.flush()
    (result,) = assess_checklist(db, run, [foreign])
    assert result.verdict == "unproven"
    assert "does not belong to this case and supplier" in " ".join(result.gaps)
    assert POLICY_VERSION == result.policy_version


def test_actual_issuer_profile_proves_certificate_validity_only_for_the_matched_holder(
    db: Session,
) -> None:
    """Replay of the genuine BSI directory capture (dated by its capture time, labeled replay)."""
    from datetime import datetime as dt

    from verisource.sources.issuers import profile_observations, visible_text
    from verisource.sources.manifests import load_record

    manifest, content = load_record(RECORDS / "bsi-client-profile.manifest.json")
    text = visible_text(content.decode("utf-8"))
    collected = dt.fromisoformat(manifest["obtained_at"])
    built = build(db)
    _a, case, revision, supplier, checklist, _c, run, task = built
    supplier.display_name = "SBICAP Securities Limited"  # the holder named by the real profile
    claim = Claim(
        case_id=case.id, revision_id=revision.id, checklist_id=checklist.id,
        supplier_id=supplier.id, type="certificate",
        assertion="ISO/IEC 27001:2022 certificate status is valid",
        relevant_period={"kind": "current", "as_of": None}, required_for_shortlist=True,
        proof_criteria_json=criteria(
            criterion("certificate.validity", "Issuer-published status", "issuer_status",
                      ["issuer"], independent=False, missing="No issuer status")
        ),
    )  # fmt: skip
    db.add(claim)
    db.flush()

    def evidence_for(name: str, identifiers: list[dict[str, str]]) -> Any:
        (observation,) = profile_observations(
            text, manifest["original_url"], content, name, identifiers, collected, replay=True
        )
        return persist_observation(db, task, run, observation, {})

    matched = evidence_for(
        "SBICAP Securities Limited", [{"type": "certificate_number", "value": "IS 822433"}]
    )
    (verdict,) = assess_checklist(db, run, [claim], now=collected)
    assert verdict.verdict == "proven" and verdict.evidence_refs == [str(matched.id)]
    assert matched.replay is True and matched.authority_role == "issuer"

    # The same page for a differently named buyer supplier is only a proposed identity.
    resolution = db.get(IdentityResolution, matched.identity_resolution_id)
    db.delete(resolution)  # Controlled reset (cascades to its evidence) to re-derive identity.
    db.flush()
    evidence_for("A Different Company Limited", [])
    (unmatched,) = assess_checklist(db, run, [claim], now=collected)
    assert unmatched.verdict == "unproven"
    assert "identity is proposed" in " ".join(unmatched.gaps)


def test_casting_company_certificate_is_proven_only_for_the_buyer_supplied_number(
    db: Session,
) -> None:
    """Replay of the genuine BSI directory capture for a ferrous casting company."""
    from datetime import datetime as dt

    from verisource.sources.issuers import profile_observations, visible_text
    from verisource.sources.manifests import load_record

    manifest, content = load_record(RECORDS / "bsi-crescent-foundry.manifest.json")
    collected = dt.fromisoformat(manifest["obtained_at"])
    built = build(db)
    _a, case, revision, supplier, checklist, _c, run, task = built
    name = "Crescent Foundry Co. Pvt. Ltd."
    supplier.display_name = name
    observations = profile_observations(
        visible_text(content.decode("utf-8")), manifest["original_url"], content, name,
        [{"type": "certificate_number", "value": "FM 689386"}], collected, replay=True,
    )  # fmt: skip
    assert len(observations) == 3
    for observation in observations:
        persist_observation(db, task, run, observation, {})
    claim = Claim(
        case_id=case.id, revision_id=revision.id, checklist_id=checklist.id,
        supplier_id=supplier.id, type="certificate",
        assertion="ISO 9001:2015 certificate FM 689386 is valid",
        relevant_period={"kind": "current", "as_of": None}, required_for_shortlist=True,
        proof_criteria_json=criteria(
            criterion("certificate.validity", "Issuer-published status", "issuer_status",
                      ["issuer"], independent=False, missing="No issuer status")
        ),
    )  # fmt: skip
    db.add(claim)
    db.flush()
    (verdict,) = assess_checklist(db, run, [claim], now=collected)
    # Only the record whose number the buyer supplied has a confirmed identity.
    assert verdict.verdict == "proven" and len(verdict.evidence_refs) == 1
    rejected = " | ".join(verdict.gaps)
    assert rejected.count("identity is proposed") == 2, rejected
