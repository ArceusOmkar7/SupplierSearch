"""Issuer directory profile reading on the actual captured BSI client-directory page.

The record is a real BSI-published certificate profile for an organisation unrelated to
casting; it exercises the certificate-status path on genuine issuer data only.
"""

import re

import pytest
from support import RECORDS

from verisource.security.egress import GuardedFetch
from verisource.sources.issuers import parse_bsi_profile, read_profile
from verisource.sources.manifests import load_record

pytestmark = pytest.mark.real_records
HOLDER = "SBICAP Securities Limited"


def captured_text() -> str:
    _manifest, content = load_record(RECORDS / "bsi-client-profile.manifest.json")
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", content.decode("utf-8"), flags=re.DOTALL)
    return re.sub(r"<[^>]+>", " ", html)


def test_actual_profile_fields_are_parsed_exactly() -> None:
    profile = parse_bsi_profile(captured_text())
    assert profile is not None
    assert profile.holder == HOLDER and profile.certificate_number == "IS 822433"
    assert profile.standard == "ISO/IEC 27001:2022"
    assert (profile.start.isoformat(), profile.expiry.isoformat()) == ("2025-04-10", "2028-04-09")
    assert parse_bsi_profile("An unrelated page with no certificate profile") is None


@pytest.mark.live
def test_live_profile_confirms_identity_only_with_number_and_name() -> None:
    manifest, _ = load_record(RECORDS / "bsi-client-profile.manifest.json")
    url = manifest["original_url"]
    fetcher = GuardedFetch()
    try:
        matched = read_profile(
            fetcher, url, supplier_name=HOLDER,
            supplier_identifiers=[{"type": "certificate_number", "value": "IS 822433"}],
        )  # fmt: skip
        unmatched = read_profile(fetcher, url, supplier_name="Some Other Company Limited",
                                 supplier_identifiers=[])  # fmt: skip
    finally:
        fetcher.close()
    if not matched.observations:
        pytest.skip(f"Missing prerequisite: issuer page unavailable ({matched.gaps})")
    observation = matched.observations[0]
    assert observation.identity is not None and observation.identity.state == "confirmed"
    assert observation.authority_role == "issuer" and not observation.self_reported
    assert "supports:certificate.validity" in observation.assertion_tags
    assert unmatched.observations[0].identity.state == "proposed"  # type: ignore[union-attr]
    assert any(a.request_dispatched and a.http_status == 200 for a in matched.attempts)


@pytest.mark.live
def test_nabcb_adapter_reports_only_what_the_real_page_says() -> None:
    from verisource.sources.issuers import check_issuer, visible_text

    fetcher = GuardedFetch()
    try:
        found = check_issuer(fetcher, "BSI Assurance UK Limited", "IS 822433")
    finally:
        fetcher.close()
    dispatched = [a for a in found.attempts if a.request_dispatched and a.outcome == "success"]
    if not dispatched:
        pytest.skip(f"Missing prerequisite: NABCB page unavailable ({found.gaps})")
    manifest, content = load_record(RECORDS / "nabcb-msc.manifest.json")
    page = visible_text(content.decode("utf-8")).casefold()
    listed = "bsi assurance" in page
    # An accreditation observation may exist only when the real page text names the issuer.
    if found.observations:
        assert listed
    for observation in found.observations:
        assert observation.authority_role == "accreditation_body"
        assert "accreditation:issuer_listed" in observation.assertion_tags
    # IAF CertSEARCH is explicitly unavailable, never a fabricated success.
    assert any("IAF CertSEARCH" in gap for gap in found.gaps)
    assert manifest["publisher"]


def test_actual_casting_company_profile_lists_each_certificate_separately() -> None:
    from verisource.sources.issuers import parse_bsi_profiles, visible_text

    _manifest, content = load_record(RECORDS / "bsi-crescent-foundry.manifest.json")
    profiles = parse_bsi_profiles(visible_text(content.decode("utf-8")))
    by_number = {p.certificate_number: p for p in profiles}
    assert set(by_number) == {"OHS 550040", "EMS 554464", "FM 689386"}
    nine = by_number["FM 689386"]
    assert nine.standard == "ISO 9001:2015" and nine.holder == "Crescent Foundry Co. Pvt. Ltd."
    assert (nine.start.isoformat(), nine.expiry.isoformat()) == ("2018-03-17", "2027-03-16")
    assert "CI & DI casting" in nine.scope
