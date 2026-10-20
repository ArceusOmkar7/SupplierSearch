"""Live capture of an actual official page into a temporary records root.

Requires network access; the bytes are the real BIS copyright-policy page, never a stand-in.
"""

import json
from pathlib import Path

import pytest

from verisource.operations.capture import CaptureRefused, capture_source
from verisource.sources.manifests import load_record

pytestmark = [pytest.mark.live, pytest.mark.real_records]
URL = "https://bis.gov.in/copyright-policy/?lang=en"


def test_capture_writes_hash_checked_provenance_and_logs_refusals(tmp_path: Path) -> None:
    try:
        path = capture_source(
            URL,
            name="bis-policy-live",
            kind="official",
            publisher="Bureau of Indian Standards",
            rights="BIS copyright policy permits accurate attributed reproduction",
            attribution="Bureau of Indian Standards, Government of India; original source linked",
            coverage=["IN", "source policy"],
            records_root=tmp_path,
        )
    except CaptureRefused as exc:
        pytest.skip(f"Missing prerequisite: official source unavailable ({exc})")
    manifest, content = load_record(path, tmp_path)
    assert manifest["mode"] == "live" and manifest["format"] == "html"
    assert manifest["publication_cutoff"] is None and manifest["cutoff_unknown_reason"]
    assert len(content) > 10_000
    with pytest.raises(CaptureRefused, match="capture_exists"):
        capture_source(
            URL,
            name="bis-policy-live",
            kind="official",
            publisher="Bureau of Indian Standards",
            rights="r",
            attribution="a",
            coverage=["IN"],
            records_root=tmp_path,
        )
    log = [
        json.loads(line) for line in (tmp_path / "capture-attempts.jsonl").read_text().splitlines()
    ]
    assert [entry["outcome"] for entry in log] == ["retrieved", "refused"]


def test_capture_refuses_internal_and_marketplace_targets(tmp_path: Path) -> None:
    for url, reason in (
        ("http://127.0.0.1:11434/api/tags", "source_unavailable"),
        ("https://www.indiamart.com/proddetail/actual-listing.html", "not_supported"),
    ):
        with pytest.raises(CaptureRefused, match=reason):
            capture_source(
                url,
                name="refused-control",
                kind="supplier",
                publisher="control",
                rights="control",
                attribution="control",
                coverage=["IN"],
                records_root=tmp_path,
            )
    assert not list(tmp_path.glob("*.manifest.json"))
