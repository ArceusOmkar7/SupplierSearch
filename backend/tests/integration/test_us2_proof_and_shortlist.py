"""Qualification lists derived from verdicts, plus one end-to-end qualified path on real data.

Classification tests use verdict values only (no invented evidence). The positive path replays
the genuine BSI directory capture of an actual issued certificate; that organisation is not a
casting supplier, so this exercises the policy on real issuer data, not a sourcing claim.
Natural 'contradicted' source examples are not available and are not manufactured.
"""

from collections.abc import Iterator
from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from support import RECORDS
from test_verification_schema import build

from verisource.db.models import Claim
from verisource.domain.claims import criteria, criterion
from verisource.domain.evidence_policy import assess_checklist
from verisource.domain.shortlist import classify, required_claims
from verisource.domain.snapshots import publish_snapshot
from verisource.orchestration.persistence import persist_observation
from verisource.sources.issuers import profile_observations, visible_text
from verisource.sources.manifests import load_record

pytestmark = [pytest.mark.integration, pytest.mark.real_records]


@pytest.fixture
def db(test_database_url: str) -> Iterator[Session]:
    engine = create_engine(test_database_url, hide_parameters=True)
    with engine.connect() as connection, connection.begin() as outer:
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
            yield session
        outer.rollback()
    engine.dispose()


def claim(supplier: object, assertion: str, *, required: bool, parent: object = None) -> Claim:
    return Claim(
        id=uuid4(),
        supplier_id=supplier,
        parent_claim_id=getattr(parent, "id", None),
        assertion=assertion,
        required_for_shortlist=required,
        type="legal_existence",
    )


def test_a_supplier_is_qualified_only_when_every_required_claim_is_proven() -> None:
    a, b, c, d = uuid4(), uuid4(), uuid4(), uuid4()
    claims = [
        claim(a, "A legal", required=True),
        claim(a, "A cert", required=True),
        claim(a, "A optional", required=False),
        claim(b, "B legal", required=True),
        claim(b, "B cert", required=True),
        claim(c, "C legal", required=True),
        claim(d, "D optional only", required=False),
    ]
    by_text = {x.assertion: x.id for x in claims}
    verdicts = {
        by_text["A legal"]: "proven",
        by_text["A cert"]: "proven",
        by_text["A optional"]: "unproven",  # optional outcomes stay visible but do not block
        by_text["B legal"]: "proven",
        by_text["B cert"]: "unproven",
        by_text["C legal"]: "contradicted",
    }
    outcomes = {o.supplier_id: o for o in classify(claims, verdicts, [a, b, c, d])}
    assert outcomes[a].status == "qualified"
    assert outcomes[b].status == "follow_up" and "B cert" in outcomes[b].reasons[0]
    assert outcomes[c].status == "excluded" and outcomes[c].reasons == ["Contradicted: C legal"]
    # No required claim means no vacuous qualification.
    assert outcomes[d].status == "follow_up" and "No required claim" in outcomes[d].reasons[0]


def test_unevaluated_required_claims_are_follow_up_not_qualified() -> None:
    s = uuid4()
    only = claim(s, "Not yet checked", required=True)
    (outcome,) = classify([only], {}, [s])
    assert outcome.status == "follow_up" and outcome.reasons[0].startswith("Not yet evaluated")


def test_required_parent_covers_its_subclaims_once() -> None:
    s = uuid4()
    parent = claim(s, "Certificate", required=True)
    child = claim(s, "Certificate validity", required=True, parent=parent)
    assert [c.assertion for c in required_claims([parent, child], s)] == ["Certificate"]
    # A required subclaim of a non-required parent is still required.
    loose = claim(s, "Parent", required=False)
    kid = claim(s, "Kid", required=True, parent=loose)
    assert [c.assertion for c in required_claims([loose, kid], s)] == ["Kid"]


def test_real_issuer_record_yields_a_qualified_supplier_and_a_matching_snapshot(
    db: Session,
) -> None:
    manifest, content = load_record(RECORDS / "bsi-client-profile.manifest.json")
    collected = datetime.fromisoformat(manifest["obtained_at"])
    built = build(db)
    _a, case, revision, supplier, checklist, base, run, task = built
    base.required_for_shortlist = True  # unproven: no evidence exists for it
    name = "SBICAP Securities Limited"
    supplier.display_name = name
    (observation,) = profile_observations(
        visible_text(content.decode("utf-8")),
        manifest["original_url"],
        content,
        name,
        [{"type": "certificate_number", "value": "IS 822433"}],
        collected,
        replay=True,
    )
    persist_observation(db, task, run, observation, {})
    validity = Claim(
        case_id=case.id,
        revision_id=revision.id,
        checklist_id=checklist.id,
        supplier_id=supplier.id,
        type="certificate",
        assertion="ISO/IEC 27001:2022 certificate status is valid",
        relevant_period={"kind": "current", "as_of": None},
        required_for_shortlist=True,
        proof_criteria_json=criteria(
            criterion(
                "certificate.validity",
                "Issuer-published status",
                "issuer_status",
                ["issuer"],
                independent=False,
                missing="No issuer status",
            )
        ),
    )
    db.add(validity)
    db.flush()
    from sqlalchemy import select

    required = list(
        db.scalars(
            select(Claim).where(
                Claim.checklist_id == checklist.id, Claim.supplier_id == supplier.id
            )
        )
    )
    assess_checklist(db, run, required, now=collected)
    snapshot = publish_snapshot(db, case, run, "completed")
    assert snapshot is not None
    assert snapshot.qualified_ids == [] and snapshot.follow_up_ids == [str(supplier.id)]
    # Dropping the unprovable claim from the required set (an explicit buyer edit) leaves only
    # the certificate claim, which the real issuer record proves.
    base.required_for_shortlist = False
    db.flush()
    assess_checklist(db, run, required, now=collected)
    later = publish_snapshot(db, case, run, "updated")
    assert later is not None and later.sequence == snapshot.sequence + 1
    assert later.qualified_ids == [str(supplier.id)] and later.follow_up_ids == []
    row = later.content_json["suppliers"][0]
    assert row["status"] == "qualified"
    cert = next(c for c in row["claims"] if c["claim_id"] == str(validity.id))
    assert cert["verdict"] == "proven" and cert["evidence"][0]["identity_state"] == "confirmed"
    assert cert["evidence"][0]["replay"] is True  # replay of a capture is labeled, not live
    # Earlier snapshots are unchanged by later arrivals.
    assert snapshot.qualified_ids == [] and snapshot.sequence == 1


def test_review_indicators_cite_real_records_and_never_assert_a_verdict() -> None:
    """Indicators over the actual captured Amruta page and actual licence-list addresses."""
    import re

    from support import licence_rows

    from verisource.country_packs.india.warnings import HEADCOUNT, RESIDENTIAL, detect
    from verisource.db.models import EvidenceRecord
    from verisource.sources.websites import _text_and_links

    _m, page = load_record(RECORDS / "amruta-pumppartinvest.manifest.json")
    _title, text, _links = _text_and_links(page, "https://www.amrutaindustries.in/")
    supplier = uuid4()
    record = EvidenceRecord(
        id=uuid4(), supplier_id=supplier, observation=text[:4000], self_reported=True,
        authority_role="supplier", assertion_tags=[],
    )  # fmt: skip
    rows = licence_rows()
    addresses = {uuid4(): [("production_site", row.factory_address)] for row in rows}
    indicators = detect([record], addresses)
    families = {i.family for i in indicators}
    assert families <= {
        "business_activity_trader_terms", "catalogue_breadth", "capacity_headcount_only",
        "site_not_identified", "site_address_residential_terms", "business_activity_conflict",
        "site_inconsistency_unresolved",
    }  # fmt: skip
    # Each indicator is explainable from the real input and is explicitly unvalidated.
    assert all(not i.validated and "Unvalidated" in i.message for i in indicators)
    flagged_sites = sum(1 for i in indicators if i.family == "site_address_residential_terms")
    assert flagged_sites == sum(1 for row in rows if RESIDENTIAL.search(row.factory_address))
    has_headcount = bool(HEADCOUNT.search(record.observation))
    assert any(i.family == "capacity_headcount_only" for i in indicators) == has_headcount
    assert not re.search(r"proven|contradicted", " ".join(i.message for i in indicators))
    # An office-only address set is flagged as not identifying a production site.
    office = detect([], {uuid4(): [("registered_office", rows[0].factory_address)]})
    assert [i.family for i in office] == ["site_not_identified"]
