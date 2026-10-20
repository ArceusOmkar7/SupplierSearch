"""Live traversal of an actual supplier website named in the project research.

Requires network access. Everything asserted is what the real site returned; no response is
simulated. The captured text is the supplier's self-report, never independent proof.
"""

import hashlib

import pytest

from verisource.security.egress import GuardedFetch
from verisource.sources import websites
from verisource.sources.quotas import LIMITS

pytestmark = [pytest.mark.live, pytest.mark.real_records]
SITE = "https://www.amrutaindustries.in/pumppartinvest.html"  # Cited in specs research.md D05.


def test_real_supplier_site_is_read_within_limits_as_self_report() -> None:
    fetcher = GuardedFetch()
    try:
        result = websites.traverse(
            SITE,
            tag_terms={"investment cast": "supports:capability.process.investment-casting"},
            fetcher=fetcher,
            renderer=None,
        )
    finally:
        fetcher.close()
    if not result.pages:
        pytest.skip(f"Missing prerequisite: supplier site unreachable ({result.coverage_gaps})")
    assert len(result.pages) <= LIMITS.pages_per_supplier
    dispatched = [a for a in result.attempts if a.request_dispatched]
    assert dispatched and dispatched[0].target.endswith("/robots.txt")  # permission first
    assert all(a.http_status is None or 100 <= a.http_status < 600 for a in dispatched)
    # Every retry points at an earlier attempt for the same URL.
    for index, attempt in enumerate(result.attempts):
        if attempt.retry_of is not None:
            assert attempt.retry_of < index
            assert result.attempts[attempt.retry_of].target == attempt.target
    assert result.observations
    for observation in result.observations:
        assert observation.self_reported and observation.authority_role == "supplier"
        assert "@" not in observation.observation  # contact details are redacted
    page = result.pages[0]
    assert any(o.content_hash == hashlib.sha256(page.body).hexdigest() for o in result.observations)


def test_marketplace_links_are_never_requested() -> None:
    fetcher = GuardedFetch()
    try:
        result = websites.traverse(
            "https://www.indiamart.com/proddetail/actual-listing.html",
            tag_terms={},
            fetcher=fetcher,
            renderer=None,
        )
    finally:
        fetcher.close()
    assert result.attempts and not any(a.request_dispatched for a in result.attempts)
    assert result.attempts[0].reason_code == "not_supported" and not result.pages


def test_playwright_renderer_reads_a_real_page_through_the_destination_guard() -> None:
    from verisource.sources import browser

    rendered = browser.render(SITE)
    if rendered is None:
        pytest.skip("Missing prerequisite: Chromium unavailable or the site unreachable")
    status, html = rendered
    assert status == 200 and b"<html" in html.lower() and len(html) > 5_000
    # Internal destinations never reach the browser.
    assert browser.render("http://127.0.0.1:11434/api/tags") is None
