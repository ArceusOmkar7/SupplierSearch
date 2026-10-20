"""Deterministic qualified / follow-up / excluded classification.

A supplier is qualified only if every buyer-required claim is proven. Contradicted required
claims exclude it from both lists while staying in the matrix. Criteria are never relaxed to
fill a list; an empty qualified list is a valid, explicit result.
"""

from dataclasses import dataclass, field
from uuid import UUID

from verisource.db.models import Claim


@dataclass(frozen=True)
class RequiredResult:
    claim_id: UUID
    assertion: str
    verdict: str
    evaluated: bool


@dataclass(frozen=True)
class SupplierOutcome:
    supplier_id: UUID
    status: str  # qualified | follow_up | excluded
    required: list[RequiredResult] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


def required_claims(claims: list[Claim], supplier_id: UUID) -> list[Claim]:
    """Required claims counted once: a required parent covers its (compound) subclaims."""
    own = [c for c in claims if c.supplier_id == supplier_id]
    required_parents = {c.id for c in own if c.required_for_shortlist and c.parent_claim_id is None}
    return [
        c
        for c in own
        if c.required_for_shortlist
        and (c.parent_claim_id is None or c.parent_claim_id not in required_parents)
    ]


def classify(
    claims: list[Claim], verdicts: dict[UUID, str], supplier_ids: list[UUID]
) -> list[SupplierOutcome]:
    outcomes: list[SupplierOutcome] = []
    for supplier_id in supplier_ids:
        required = required_claims(claims, supplier_id)
        results = [
            RequiredResult(c.id, c.assertion, verdicts.get(c.id, "unproven"), c.id in verdicts)
            for c in required
        ]
        reasons: list[str] = []
        if not results:
            outcomes.append(
                SupplierOutcome(
                    supplier_id,
                    "follow_up",
                    results,
                    ["No required claim was selected for this supplier, so it cannot qualify."],
                )
            )
            continue
        contradicted = [r for r in results if r.verdict == "contradicted"]
        unproven = [r for r in results if r.verdict != "proven"]
        if contradicted:
            reasons = [f"Contradicted: {r.assertion}" for r in contradicted]
            status = "excluded"
        elif unproven:
            reasons = [
                f"{'Not yet evaluated' if not r.evaluated else 'Unproven'}: {r.assertion}"
                for r in unproven
            ]
            status = "follow_up"
        else:
            status = "qualified"
        outcomes.append(SupplierOutcome(supplier_id, status, results, reasons))
    return outcomes
