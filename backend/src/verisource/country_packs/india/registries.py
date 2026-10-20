"""Exact-ID lookup in imported official exports and official-link follow-through.

GST syntax is a format check, not registry proof. MCA/Udyam/BIS export cutoffs are preserved:
a record from an old export supports only what that export said at its cutoff. Only exact
official URLs found in a real obtained certificate are followed (QR image decoding is not
available locally, so QR-only links remain a disclosed gap).
"""

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlsplit

from sqlalchemy.orm import Session

from verisource.country_packs.contracts import IdentityClaim, Observation
from verisource.country_packs.india.identity import (
    REGISTRY_IDENTIFIERS,
    IdentityAssessment,
    address_tokens,
    assess_candidate,
)
from verisource.sources.imports import LookupMatch, lookup_exact

OFFICIAL_HOSTS = frozenset(
    {
        "udyamregistration.gov.in",
        "bis.gov.in",
        "www.bis.gov.in",
        "www.manakonline.in",
        "manakonline.in",
        "nabcb.qci.org.in",
        "www.mca.gov.in",
        "www.bsigroup.com",
    }
)
_URL = re.compile(r"https?://[^\s<>\"')\]]+", re.IGNORECASE)


@dataclass(frozen=True)
class ExportHit:
    observation: Observation
    identity: IdentityAssessment
    record_ref: str
    site_matched: bool = False


def _validity(fields: dict[str, str]) -> datetime | None:
    value = fields.get("validity", "")
    try:
        return datetime.fromisoformat(value).replace(tzinfo=UTC)
    except ValueError:
        return None


def lookup_supplier(
    db: Session, supplier_name: str, identifiers: list[dict[str, str]], *, address: str | None
) -> list[ExportHit]:
    """Observations for each exact identifier match in an imported official export."""
    hits: list[ExportHit] = []
    seen: set[tuple[str, str]] = set()
    for item in identifiers:
        kind, value = item["type"], item["value"]
        if kind not in REGISTRY_IDENTIFIERS:
            continue
        for match in lookup_exact(db, identifier_type=kind, value=value):
            key = (str(match.dataset_id), match.locator)
            if key in seen:
                continue
            seen.add(key)
            hits.append(_hit(supplier_name, identifiers, match, kind, value, address))
    return hits


def _hit(
    supplier_name: str,
    identifiers: list[dict[str, str]],
    match: LookupMatch,
    kind: str,
    value: str,
    address: str | None,
) -> ExportHit:
    fields = {k: str(v) for k, v in match.fields.items()}
    identity = assess_candidate(
        supplier_name,
        identifiers,
        fields.get("firm_name", ""),
        {kind: value},
        supplier_address=address,
        candidate_address=fields.get("factory_address"),
    )
    cutoff = match.publication_cutoff
    text = (
        f"{fields.get('firm_name', '?')} appears in an official export "
        f"({'cutoff ' + cutoff.date().isoformat() if cutoff else 'cutoff unknown'}; "
        f"imported record, not a current status): {kind} {value}"
    )
    if fields.get("validity"):
        text += f"; validity as listed {fields['validity']}"
    if fields.get("factory_address"):
        text += f"; address as listed: {fields['factory_address']}"
    observation = Observation(
        source_id="in.local-export",
        source_version=1,
        source_ref=str(match.dataset_id),
        locator=match.locator,
        observation=text,
        collected_at=datetime.now(UTC),
        authority_role="official_publication",
        origin_lineage=f"dataset:{match.dataset_id}",
        self_reported=False,
        content_hash=str(match.record_id),
        assertion_tags=("export_record", f"id:{kind}"),
        issued_at=cutoff,
        expires_at=_validity(fields),
        identity=IdentityClaim(
            f"{match.dataset_id}#{match.locator}",
            identity.state,
            identity.basis,
            tuple(identity.identifier_matches),
            tuple(identity.discrepancies),
            identity.score,
        ),
    )
    listed, ours = fields.get("factory_address"), address
    matched = bool(listed and ours and len(address_tokens(listed) & address_tokens(ours)) >= 2)
    return ExportHit(observation, identity, f"{match.dataset_id}#{match.locator}", matched)


def official_urls(text: str) -> list[str]:
    """Exact URLs printed in a certificate that point at an allow-listed official host."""
    found: list[str] = []
    for raw in _URL.findall(text):
        url = raw.rstrip(".,;")
        host = (urlsplit(url).hostname or "").lower()
        if host in OFFICIAL_HOSTS and url not in found:
            found.append(url)
    return found
