"""Operator-run capture of genuine source bytes with a provenance manifest.

The capture is refused unless robots permits it, the response is a real HTTP 200 and the
operator supplies the reuse rights and attribution. Failed attempts are logged but never
produce a manifest; nothing is generated, edited or substituted.
"""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from jsonschema import Draft202012Validator, FormatChecker

from verisource.security.egress import EgressDenied, GuardedFetch
from verisource.sources.manifests import DEFAULT_RECORDS_ROOT, SCHEMA_PATH
from verisource.sources.policy import host_prohibited, robots_decision

FORMATS = {
    "text/html": "html",
    "application/pdf": "pdf",
    "text/csv": "csv",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "text/plain": "txt",
    "application/json": "json",
}


class CaptureRefused(Exception):
    """The source could not be captured; the reason is also written to the attempt log."""


def _log(root: Path, entry: dict[str, Any]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    with (root / "capture-attempts.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(entry, ensure_ascii=False) + "\n")


def capture_source(
    url: str,
    *,
    name: str,
    kind: str,
    publisher: str,
    rights: str,
    attribution: str,
    coverage: list[str],
    publication_cutoff: str | None = None,
    cutoff_unknown_reason: str | None = None,
    locator: str = "original complete response",
    records_root: Path | None = None,
    fetcher: GuardedFetch | None = None,
) -> Path:
    root = (records_root or DEFAULT_RECORDS_ROOT).resolve()
    if not name.replace("-", "").replace("_", "").isalnum():
        raise ValueError("Use a simple capture name")
    if not rights.strip() or not attribution.strip():
        raise ValueError("Rights and attribution are required from the operator")
    if publication_cutoff is None and not cutoff_unknown_reason:
        cutoff_unknown_reason = (
            "No single publication cutoff verified; collection time does not establish currency"
        )
    own = fetcher is None
    fetcher = fetcher or GuardedFetch()
    attempt: dict[str, Any] = {"url": url, "at": datetime.now(UTC).isoformat()}
    try:
        if host_prohibited(url):  # Checked before any request, including robots.txt.
            raise CaptureRefused("not_supported")
        if any(root.glob(f"{name}.*")):  # Never overwrite or re-fetch an existing capture.
            raise CaptureRefused("capture_exists")
        robots_url = httpx.URL(url).join("/robots.txt")
        try:
            robots, _ = fetcher.get(str(robots_url), max_bytes=512 * 1024)
            decision = robots_decision(
                robots.text if robots.status_code == 200 else None, robots.status_code, url
            )
        except EgressDenied as exc:
            raise CaptureRefused("source_unavailable") from exc
        except httpx.HTTPError:
            decision = robots_decision(None, None, url)
        if not decision.allowed:
            raise CaptureRefused(decision.reason_code or "permission_unverified")
        response, final_url = fetcher.get(url)
        attempt.update(
            request_dispatched=True, http_status=response.status_code, final_url=final_url
        )
        if response.status_code != 200:
            raise CaptureRefused(f"http_{response.status_code}")
        media = response.headers.get("content-type", "").split(";")[0].strip().lower()
        if media not in FORMATS:
            raise CaptureRefused("unsupported_media_type")
        content = response.content
        extension = FORMATS[media]
        file_name = f"{name}.{extension}"
        target = root / file_name
        manifest_path = root / f"{name}.manifest.json"
        if target.exists() or manifest_path.exists():
            raise CaptureRefused("capture_exists")
        manifest = {
            "schema_version": 1,
            "kind": kind,
            "mode": "live",
            "publisher": publisher,
            "original_url": final_url,
            "rights": rights,
            "attribution": attribution,
            "obtained_at": datetime.now(UTC).isoformat(),
            "publication_cutoff": publication_cutoff,
            "cutoff_unknown_reason": cutoff_unknown_reason if publication_cutoff is None else None,
            "coverage": coverage,
            "file": file_name,
            "sha256": hashlib.sha256(content).hexdigest(),
            "format": extension,
            "locator": locator,
        }
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(manifest)
        root.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        attempt.update(outcome="retrieved", bytes=len(content), manifest=manifest_path.name)
        return manifest_path
    except CaptureRefused as exc:
        attempt.update(outcome="refused", reason=str(exc))
        raise
    except (EgressDenied, httpx.HTTPError) as exc:
        attempt.update(outcome="unavailable", reason=type(exc).__name__)
        raise CaptureRefused("source_unavailable") from exc
    finally:
        _log(root, attempt)
        if own:
            fetcher.close()
