"""Supplier identifier/name/address matching and review.

Typed identifier equality is the only automatic basis for a confirmed identity. A fuzzy name
score is a suggestion shown to the buyer and never confirms or contradicts anything; office
and factory addresses may legitimately differ and are recorded, not treated as conflicts.
"""

import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from verisource.db.models import IdentityResolution

REGISTRY_IDENTIFIERS = ("gstin", "cin", "llpin", "udyam", "licence_number")
_SUFFIXES = re.compile(
    r"\b(private|pvt|limited|ltd|llp|co|company|corp|corporation|inc|incorporated)\b\.?",
    re.IGNORECASE,
)


def canonical_name(value: str) -> str:
    text = unicodedata.normalize("NFKC", value).casefold()
    text = re.sub(r"[^\w\s]", " ", text)
    text = _SUFFIXES.sub(" ", text)
    return " ".join(text.split())


def normalize(name: str, identifiers: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "original_name": name,
        "canonical_name": canonical_name(name),
        "identifiers": [{"type": item["type"], "value": item["value"]} for item in identifiers],
    }


def name_similarity(left: str, right: str) -> float:
    """Token-set Jaccard on canonical names; informational only."""
    a, b = set(canonical_name(left).split()), set(canonical_name(right).split())
    return round(len(a & b) / len(a | b), 3) if a and b else 0.0


def address_tokens(address: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]{3,}", unicodedata.normalize("NFKC", address).casefold()))


@dataclass(frozen=True)
class IdentityAssessment:
    state: str  # proposed | confirmed | ambiguous | rejected
    identifier_matches: list[dict[str, str]]
    discrepancies: list[str]
    score: float | None
    basis: str


def assess_candidate(
    supplier_name: str,
    supplier_identifiers: list[dict[str, str]],
    candidate_name: str,
    candidate_identifiers: dict[str, str],
    *,
    supplier_address: str | None = None,
    candidate_address: str | None = None,
) -> IdentityAssessment:
    matches: list[dict[str, str]] = []
    conflicts: list[str] = []
    for item in supplier_identifiers:
        kind = item["type"]
        if kind not in REGISTRY_IDENTIFIERS or kind not in candidate_identifiers:
            continue
        ours, theirs = item["value"].strip().upper(), candidate_identifiers[kind].strip().upper()
        if ours == theirs:
            matches.append({"type": kind, "value": ours})
        else:
            conflicts.append(f"{kind} differs between the buyer input and the record")
    score = name_similarity(supplier_name, candidate_name)
    discrepancies = list(conflicts)
    if supplier_address and candidate_address:
        overlap = address_tokens(supplier_address) & address_tokens(candidate_address)
        if len(overlap) < 2:
            discrepancies.append(
                "addresses differ; an office and a production site may legitimately differ"
            )
    if conflicts:
        return IdentityAssessment("rejected", matches, discrepancies, score, "identifier_conflict")
    if matches:
        if score < 0.2:
            discrepancies.append("identifier matches but the names are dissimilar; review")
            return IdentityAssessment(
                "ambiguous", matches, discrepancies, score, "identifier_match_name_dissimilar"
            )
        return IdentityAssessment(
            "confirmed", matches, discrepancies, score, "exact_identifier_match"
        )
    # Name resemblance alone only proposes a candidate for the buyer to review.
    return IdentityAssessment(
        "proposed" if score >= 0.6 else "ambiguous",
        matches,
        discrepancies,
        score,
        "name_similarity",
    )


def record_resolution(
    db: Session,
    *,
    case_id: UUID,
    revision_id: UUID,
    supplier_id: UUID,
    candidate_record_ref: str,
    assessment: IdentityAssessment,
) -> IdentityResolution:
    confirmed = assessment.state == "confirmed"
    resolution = IdentityResolution(
        case_id=case_id,
        revision_id=revision_id,
        supplier_id=supplier_id,
        candidate_record_ref=candidate_record_ref,
        identifier_matches=assessment.identifier_matches,
        discrepancies=assessment.discrepancies,
        proposed_score=assessment.score,
        state=assessment.state,
        resolution_basis=assessment.basis,
        resolved_by=None,
        resolved_at=datetime.now(UTC) if confirmed else None,
    )
    db.add(resolution)
    db.flush()
    return resolution
