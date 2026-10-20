"""Manufacturer/trader review indicators from real evidence.

These are attributable review prompts for the buyer, never proof or refutation. Business
activity, site, catalogue breadth or headcount alone establishes nothing; every indicator
names the actual records it came from. No real example of a confirmed pattern has been
verified yet, so the indicators are reported as unvalidated heuristics.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from verisource.db.models import EvidenceRecord

TRADER_WORDS = re.compile(
    r"\b(trader|trading|dealer|distributor|wholesale|wholesaler|stockist|reseller|importer)\b",
    re.IGNORECASE,
)
RESIDENTIAL = re.compile(
    r"\b(flat|apartment|residence|residential|room no|shop no|\bPO box)\b", re.IGNORECASE
)
HEADCOUNT = re.compile(
    r"\b\d{1,5}\s+(employees|workers|staff|machines|looms|lines)\b", re.IGNORECASE
)
CATEGORY_WORDS = (
    "garment", "textile", "fabric", "plastic", "steel", "casting", "electronic", "pharma",
    "chemical", "furniture", "toy", "software", "packaging", "machinery", "food", "cosmetic",
)  # fmt: skip
UNVALIDATED = "Unvalidated heuristic: no confirmed real example has been checked."


@dataclass(frozen=True)
class Indicator:
    family: str
    supplier_id: UUID
    evidence_ids: tuple[UUID, ...]
    message: str
    validated: bool = False


def detect(
    evidence: Sequence[EvidenceRecord],
    addresses: dict[UUID, list[tuple[str, str]]] | None = None,
    site_discrepancies: dict[UUID, list[str]] | None = None,
) -> list[Indicator]:
    """`addresses` maps supplier to (role, raw address) pairs from the buyer's input;
    `site_discrepancies` carries unresolved address differences recorded during identity review."""
    indicators: list[Indicator] = []
    by_supplier: dict[UUID, list[EvidenceRecord]] = {}
    for item in evidence:
        by_supplier.setdefault(item.supplier_id, []).append(item)
    for supplier_id, items in by_supplier.items():
        official = [
            e for e in items
            if e.authority_role in {"official_publication", "official_registry"}
            and TRADER_WORDS.search(e.observation)
        ]  # fmt: skip
        claims_to_manufacture = [
            e for e in items
            if e.self_reported and "supports:manufacturer.site_activity" in e.assertion_tags
        ]  # fmt: skip
        if official:
            conflict = bool(claims_to_manufacture)
            indicators.append(
                Indicator(
                    "business_activity_conflict" if conflict else "business_activity_trader_terms",
                    supplier_id,
                    tuple(e.id for e in (*official, *claims_to_manufacture)),
                    (
                        "An official record uses trading terms while the supplier describes "
                        "manufacturing; the two are kept side by side for your review. "
                        if conflict
                        else "An official record uses trading terms; review whether the supplier "
                        "manufactures. "
                    )
                    + UNVALIDATED,
                )
            )
        supplier_pages = [e for e in items if e.self_reported]
        broad = [
            e for e in supplier_pages
            if len({w for w in CATEGORY_WORDS if w in e.observation.casefold()}) >= 6
        ]  # fmt: skip
        if broad:
            indicators.append(
                Indicator(
                    "catalogue_breadth",
                    supplier_id,
                    tuple(e.id for e in broad),
                    "The supplier's pages span many unrelated product categories; breadth alone "
                    "proves nothing. " + UNVALIDATED,
                )
            )
        heads = [e for e in supplier_pages if HEADCOUNT.search(e.observation)]
        if heads:
            indicators.append(
                Indicator(
                    "capacity_headcount_only",
                    supplier_id,
                    tuple(e.id for e in heads),
                    "Headcount or machine counts are stated; these cannot prove capacity. "
                    + UNVALIDATED,
                )
            )
    for supplier_id, notes in (site_discrepancies or {}).items():
        if notes:
            indicators.append(
                Indicator(
                    "site_inconsistency_unresolved",
                    supplier_id,
                    (),
                    "Addresses from different sources differ and are not yet reconciled: "
                    + "; ".join(sorted(set(notes)))
                    + ". "
                    + UNVALIDATED,
                )
            )
    for supplier_id, entries in (addresses or {}).items():
        sites = [raw for role, raw in entries if role == "production_site"]
        if entries and not sites:
            indicators.append(
                Indicator(
                    "site_not_identified",
                    supplier_id,
                    (),
                    "No address was marked as a production site; an office address does not show "
                    "where goods are made. " + UNVALIDATED,
                )
            )
        for raw in sites:
            if RESIDENTIAL.search(raw):
                indicators.append(
                    Indicator(
                        "site_address_residential_terms",
                        supplier_id,
                        (),
                        f"The production-site address uses residential terms: {raw}. "
                        + UNVALIDATED,
                    )
                )
    return indicators
