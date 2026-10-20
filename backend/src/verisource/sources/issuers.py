"""Eligible free issuer/accreditation adapters.

Each adapter states exactly what its source can show. NABCB accreditation of an issuer is
not validation of a supplier's certificate; an issuer client list shows an association, not
current status. IAF CertSEARCH is unavailable without licensed access, and no adapter needs
an Enterprise key, so a missing check stays an explicit gap instead of a fabricated success.
"""

import hashlib
import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from urllib.parse import urlsplit

from verisource.country_packs.contracts import AttemptSpec, IdentityClaim, Observation
from verisource.country_packs.india.identity import canonical_name
from verisource.documents.certificates import inspect_pdf
from verisource.security.egress import GuardedFetch
from verisource.sources.fetching import permitted_get

SOURCE_ID = "in.issuer-pages"


@dataclass(frozen=True)
class IssuerAdapter:
    key: str
    description: str
    url: str | None
    applies_to: tuple[str, ...]  # canonical issuer-name fragments; empty = any issuer
    enabled: bool = True
    disabled_reason: str | None = None


ADAPTERS: tuple[IssuerAdapter, ...] = (
    IssuerAdapter(
        "nabcb",
        "NABCB management-system certification bodies (issuer accreditation only)",
        "https://nabcb.qci.org.in/management-system-certification/",
        (),
    ),
    IssuerAdapter(
        "tuv-rheinland-india-list",
        "TUV Rheinland India client list (historical association of a certificate number)",
        "https://www.tuv.com/content-media-files/india/pdfs/1009-certification-according-to-en-iso-13485/tuev-rheinland-india-list-of-clients.pdf",
        ("tuv rheinland", "tüv rheinland", "tuev rheinland"),
    ),
    IssuerAdapter(
        "iaf-certsearch",
        "IAF CertSEARCH",
        None,
        (),
        enabled=False,
        disabled_reason="Browser scraping is restricted by its terms and licensed access is not configured.",
    ),
    IssuerAdapter(
        "bsi-directory",
        "BSI client directory",
        None,
        ("bsi",),
        enabled=False,
        disabled_reason="No verified automatic lookup route; a profile cannot be derived from a certificate number.",
    ),
    IssuerAdapter(
        "tuv-sud-finder",
        "TUV SUD certificate finder",
        None,
        ("tuv sud", "tüv süd"),
        enabled=False,
        disabled_reason="Automatic form submission has not been verified for this source.",
    ),
)


@dataclass
class IssuerCheck:
    attempts: list[AttemptSpec] = field(default_factory=list)
    observations: list[Observation] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)


def applicable(adapter: IssuerAdapter, issuer_name: str) -> bool:
    if not adapter.applies_to:
        return True
    name = canonical_name(issuer_name)
    return any(fragment in name for fragment in adapter.applies_to)


def _snippet(text: str, needle: str, width: int = 400) -> str | None:
    position = " ".join(text.split()).casefold().find(needle.casefold())
    flat = " ".join(text.split())
    if position < 0:
        return None
    start = max(position - width // 2, 0)
    return flat[start : start + width]


def check_issuer(
    fetcher: GuardedFetch, issuer_name: str, certificate_number: str | None
) -> IssuerCheck:
    result = IssuerCheck()
    for adapter in ADAPTERS:
        if not applicable(adapter, issuer_name):
            continue
        if not adapter.enabled or adapter.url is None:
            stamp = datetime.now(UTC)
            result.attempts.append(
                AttemptSpec(
                    "capability_check",
                    f"adapter:{adapter.key}",
                    stamp,
                    stamp,
                    False,
                    "skipped",
                    "not_supported",
                )
            )
            result.gaps.append(f"{adapter.description}: {adapter.disabled_reason}")
            continue
        fetched = permitted_get(fetcher, adapter.url, max_bytes=20 * 1024 * 1024)
        result.attempts.extend(fetched.attempts)
        if fetched.response is None:
            result.gaps.append(f"{adapter.description}: {fetched.gap}")
            continue
        collected = datetime.now(UTC)
        body = fetched.response.content
        digest = hashlib.sha256(body).hexdigest()
        if body.startswith(b"%PDF-"):
            inspection = inspect_pdf(body)
            text = "\n".join(inspection.pages.values())
            if inspection.failure_reason:
                result.gaps.append(
                    f"{adapter.description}: unreadable ({inspection.failure_reason})"
                )
                continue
        else:
            text = re.sub(r"<[^>]+>", " ", fetched.response.text)
        if adapter.key == "nabcb":
            hit = _snippet(text, canonical_name(issuer_name)) or _snippet(text, issuer_name)
            if hit is None:
                result.gaps.append(
                    "NABCB page was read but does not name this issuer; accreditation is unproven."
                )
                continue
            result.observations.append(
                Observation(
                    SOURCE_ID,
                    1,
                    fetched.final_url,
                    fetched.final_url,
                    f"NABCB page text naming the issuer: {hit}",
                    collected,
                    "accreditation_body",
                    f"nabcb:{digest[:16]}",
                    False,
                    digest,
                    ("accreditation:issuer_listed",),
                )
            )
        elif certificate_number:
            hit = _snippet(text, certificate_number)
            if hit is None:
                result.gaps.append(
                    f"{adapter.description}: the certificate number was not found in the list."
                )
                continue
            result.observations.append(
                Observation(
                    SOURCE_ID,
                    1,
                    fetched.final_url,
                    fetched.final_url,
                    f"Issuer list text containing the certificate number: {hit}",
                    collected,
                    "issuer",
                    f"issuer-list:{digest[:16]}",
                    False,
                    digest,
                    ("issuer_list:certificate_number",),
                )
            )
    return result


# ---- issuer directory profiles --------------------------------------------------------------

_BSI_NUMBER = re.compile(r"Certificate number:\s*([A-Z]{1,4}\s?\d{4,})")
_BSI_SCOPE = re.compile(r"Scope:\s*(.+?)\s+Standard/Scheme number")
_BSI_STANDARD = re.compile(
    r"(ISO(?:/IEC)?\s?\d{3,6}(?::\d{4})?)\s+(\d{4}-\d{2}-\d{2})\s+(\d{4}-\d{2}-\d{2})"
)
_BSI_HOLDER = re.compile(r"Upgrade\s+(.+?)\s+\1\s")
PROFILE_HOSTS = frozenset({"www.bsigroup.com", "bsigroup.com"})


@dataclass(frozen=True)
class IssuerProfile:
    holder: str
    certificate_number: str
    scope: str
    standard: str
    start: date
    expiry: date


def parse_bsi_profiles(text: str) -> list[IssuerProfile]:
    """Every certificate block of a BSI client-directory page; incomplete blocks are skipped."""
    flat = " ".join(text.split())
    holder = _BSI_HOLDER.search(flat)
    if not holder:
        return []
    profiles: list[IssuerProfile] = []
    blocks = re.split(r"(?=Certificate number:)", flat)
    for block in blocks:
        number, scope, standard = (
            _BSI_NUMBER.search(block),
            _BSI_SCOPE.search(block),
            _BSI_STANDARD.search(block),
        )
        if number and scope and standard:
            profiles.append(
                IssuerProfile(
                    holder.group(1).strip(),
                    " ".join(number.group(1).split()),
                    scope.group(1).strip(),
                    standard.group(1),
                    date.fromisoformat(standard.group(2)),
                    date.fromisoformat(standard.group(3)),
                )
            )
    return profiles


def parse_bsi_profile(text: str) -> IssuerProfile | None:
    """The first certificate block, or None when no complete profile can be read."""
    profiles = parse_bsi_profiles(text)
    return profiles[0] if profiles else None


def profile_observations(
    text: str,
    url: str,
    body_bytes: bytes,
    supplier_name: str,
    supplier_identifiers: list[dict[str, str]],
    collected_at: datetime,
    *,
    replay: bool = False,
) -> list[Observation]:
    """Observation for a parsed issuer profile; identity needs the number AND the holder name."""

    observations: list[Observation] = []
    for profile in parse_bsi_profiles(text):
        observations.append(
            _profile_observation(
                profile, url, body_bytes, supplier_name, supplier_identifiers, collected_at, replay
            )
        )
    return observations


def _profile_observation(
    profile: IssuerProfile,
    url: str,
    body: bytes,
    supplier_name: str,
    supplier_identifiers: list[dict[str, str]],
    collected_at: datetime,
    replay: bool,
) -> Observation:
    host = (urlsplit(url).hostname or "").lower()
    ours = {
        i["value"].replace(" ", "").upper()
        for i in supplier_identifiers
        if i["type"] == "certificate_number"
    }
    number_match = profile.certificate_number.replace(" ", "").upper() in ours
    same_name = canonical_name(profile.holder) == canonical_name(supplier_name)
    if number_match and same_name:
        identity = IdentityClaim(
            f"issuer-profile:{url}#{profile.certificate_number.replace(' ', '')}",
            "confirmed",
            "certificate_number_and_name_match",
            ({"type": "certificate_number", "value": profile.certificate_number},),
        )
    else:
        identity = IdentityClaim(
            f"issuer-profile:{url}#{profile.certificate_number.replace(' ', '')}",
            "proposed",
            "issuer_profile_unmatched",
            (),
            ("holder or certificate number differs from the buyer input",),
        )
    start = datetime.combine(profile.start, datetime.min.time(), tzinfo=UTC)
    expiry = datetime.combine(profile.expiry, datetime.min.time(), tzinfo=UTC)
    return Observation(
        SOURCE_ID,
        1,
        url,
        f"{url}#{profile.certificate_number.replace(' ', '')}",
        f"Issuer directory profile: {profile.holder}; certificate {profile.certificate_number}; "
        f"{profile.standard}; valid {profile.start} to {profile.expiry}; scope: {profile.scope}",
        collected_at,
        "issuer",
        f"issuer:{host}",
        False,
        hashlib.sha256(body).hexdigest(),
        ("current_status", "supports:certificate.validity"),
        issued_at=start,
        expires_at=expiry,
        effective_at=start,
        replay=replay,
        identity=identity,
    )


def read_profile(
    fetcher: GuardedFetch,
    url: str,
    *,
    supplier_name: str,
    supplier_identifiers: list[dict[str, str]],
) -> IssuerCheck:
    """Fetch an exact issuer-profile URL (printed on a certificate) and record what it states."""
    result = IssuerCheck()
    host = (urlsplit(url).hostname or "").lower()
    if host not in PROFILE_HOSTS:
        stamp = datetime.now(UTC)
        result.attempts.append(
            AttemptSpec("capability_check", url, stamp, stamp, False, "skipped", "not_supported")
        )
        result.gaps.append("No profile reader exists for this issuer host.")
        return result
    fetched = permitted_get(fetcher, url, max_bytes=2 * 1024 * 1024)
    result.attempts.extend(fetched.attempts)
    if fetched.response is None:
        result.gaps.append(f"Issuer profile: {fetched.gap}")
        return result
    found = profile_observations(
        visible_text(fetched.response.text),
        fetched.final_url,
        fetched.response.content,
        supplier_name,
        supplier_identifiers,
        datetime.now(UTC),
    )
    if not found:
        result.gaps.append("The issuer page was read but no certificate profile could be parsed.")
    result.observations.extend(found)
    return result


def visible_text(html: str) -> str:
    """Page text without scripts and styles."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return " ".join(soup.get_text(" ").split())
