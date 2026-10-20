"""IN/core-v1: exact-ID local export lookup, supplier website, buyer certificates, issuers, BIS."""

from typing import Any
from uuid import UUID

from verisource.country_packs.contracts import PlannedCheck, SourceCapability

VERSION = "IN/core-v1"

# (id, version, access mode, claim types, enabled, disabled reason)
SOURCES: tuple[tuple[str, int, str, tuple[str, ...], bool, str | None], ...] = (
    ("in.local-export", 1, "local_export", ("legal_existence", "regulatory"), True, None),
    (
        "in.supplier-website",
        1,
        "public_page",
        ("manufacturer", "part_capability", "capacity"),
        True,
        None,
    ),
    ("in.buyer-certificate", 1, "buyer_document", ("certificate",), True, None),
    ("in.issuer-pages", 1, "issuer_page", ("certificate",), True, None),
    ("in.bis-orders", 1, "official_document", ("regulatory",), True, None),
    (
        "in.current-gst-status",
        1,
        "free_api",
        ("legal_existence",),
        False,
        "No eligible free current-status access is configured; this claim remains unproven.",
    ),
)
HOSTS = {"in.bis-orders": ["bis.gov.in", "www.bis.gov.in"]}


class IndiaPack:
    jurisdiction = "IN"
    version = VERSION

    def capabilities(self) -> list[SourceCapability]:
        return [
            SourceCapability(source, version, enabled, claims, mode, reason)
            for source, version, mode, claims, enabled, reason in SOURCES
        ]

    def plan_checks(
        self,
        requirements: dict[str, Any],
        supplier: dict[str, Any],
        claims: list[dict[str, Any]],
    ) -> list[PlannedCheck]:
        """Independent typed checks; only genuine document dependencies are chained."""
        supplier_id = UUID(supplier["supplier_id"])

        def ids(*types: str) -> tuple[UUID, ...]:
            return tuple(UUID(c["id"]) for c in claims if c["type"] in types)

        planned = [
            PlannedCheck(
                "local",
                "local_export_lookup",
                "in.local-export",
                ids("legal_existence", "regulatory"),
                supplier_id,
            ),
            PlannedCheck(
                "website",
                "website_traversal",
                "in.supplier-website",
                ids("manufacturer", "part_capability", "capacity"),
                supplier_id,
            ),
        ]
        certificate_claims = ids("certificate")
        if certificate_claims:
            planned += [
                PlannedCheck(
                    "document",
                    "certificate_document",
                    "in.buyer-certificate",
                    certificate_claims,
                    supplier_id,
                    ("website",),  # Reads certificate PDFs the website check downloaded.
                ),
                PlannedCheck(
                    "issuer",
                    "certificate_issuer_lookup",
                    "in.issuer-pages",
                    certificate_claims,
                    supplier_id,
                    ("document",),
                ),
                PlannedCheck(
                    "qr",
                    "certificate_qr_follow",
                    "in.issuer-pages",
                    certificate_claims,
                    supplier_id,
                    ("document",),
                ),
            ]
        if ids("regulatory"):
            planned.append(
                PlannedCheck(
                    "bis", "bis_applicability", "in.bis-orders", ids("regulatory"), supplier_id
                )
            )
        return planned

    def normalize_identity(self, name: str, identifiers: list[dict[str, str]]) -> dict[str, Any]:
        from verisource.country_packs.india.identity import normalize

        return normalize(name, identifiers)

    def execute_check(self, executor: Any, spec: Any) -> Any:
        return executor.execute(spec)

    def interpret_regulation(
        self, db: Any, *, standards: list[str], product_text: str
    ) -> list[Any]:
        from verisource.country_packs.india.bis import applicability_candidates

        return applicability_candidates(db, standards=standards, product_text=product_text)

    def warning_patterns(
        self, evidence: Any, addresses: dict[Any, list[tuple[str, str]]] | None = None
    ) -> list[Any]:
        from verisource.country_packs.india.warnings import detect

        return detect(evidence, addresses)
