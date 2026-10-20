"""Owner-scoped draft requirements, typed supplier identifiers and explicit confirmation.

Missing values stay null/unknown; nothing here infers a capability or confirms on the
buyer's behalf. Supplier rows are case-local and never merged across or within a case.
"""

import hashlib
import json
import re
import unicodedata
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from verisource.api.errors import reject
from verisource.db.models import (
    Case,
    ConversationMessage,
    RequirementRevision,
    Supplier,
    SupplierSite,
)

SCHEMA_VERSION = 1

REQUIREMENT_FIELDS: dict[str, Any] = {
    "part_description": None,
    "materials": [],
    "processes": [],
    "quantity": None,
    "certifications": [],
    "tolerance": None,
    "standards": [],
}
LOCATION_FIELDS: dict[str, Any] = {"country": None, "reference_location": None, "radius": None}
RADIUS_UNITS = {"km", "mi", "m"}
SITE_ROLES = {"registered_office", "production_site", "other", "unknown"}

_PATTERNS: dict[str, re.Pattern[str]] = {
    "gstin": re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$"),
    "udyam": re.compile(r"^UDYAM-[A-Z]{2}-\d{2}-\d{7}$"),
    "cin": re.compile(r"^[LU]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}$"),
    "llpin": re.compile(r"^[A-Z]{3}-\d{4}$"),
    "licence_number": re.compile(r"^\d{4,12}$"),
}
IDENTIFIER_TYPES = {
    "name",
    "website",
    "certificate_number",
    "listing_url",
    *_PATTERNS,
}


def json_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
        ).encode("utf-8")
    ).hexdigest()


def normalize_name(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def normalize_identifier(kind: str, value: str) -> str:
    """Syntax normalization only; a well-formed value is not evidence the entity exists."""
    text = value.strip()
    if kind not in IDENTIFIER_TYPES or not text or len(text) > 2048:
        raise reject(422, "invalid_identifier", "Check the supplier identifier.", type=kind)
    if kind == "name":
        return normalize_name(text)
    if kind == "listing_url":
        return text  # Opaque: never fetched, previewed or used to seed collection.
    if kind == "website":
        parts = urlsplit(text if "//" in text else f"https://{text}")
        if parts.scheme not in {"http", "https"} or not parts.hostname:
            raise reject(422, "invalid_identifier", "Check the supplier website.", type=kind)
        return (parts.hostname.lower() + parts.path.rstrip("/")).removeprefix("www.")
    if kind == "certificate_number":
        return re.sub(r"\s+", "", text).upper()
    normalized = re.sub(r"\s+", "", text).upper()
    if not _PATTERNS[kind].match(normalized):
        raise reject(422, "invalid_identifier", "Check the supplier identifier.", type=kind)
    return normalized


def validate_requirements(requirements: dict[str, Any]) -> dict[str, Any]:
    unknown = set(requirements) - set(REQUIREMENT_FIELDS)
    if unknown:
        raise reject(422, "unknown_field", "Check the requirement fields.", fields=sorted(unknown))
    for key in ("part_description", "tolerance"):
        value = requirements.get(key)
        if value is not None and (not isinstance(value, str) or len(value) > 8000):
            raise reject(422, "invalid_field", "Check the requirement field.", field=key)
    for key in ("materials", "processes", "certifications", "standards"):
        value = requirements.get(key)
        if value is not None and (
            not isinstance(value, list)
            or not all(isinstance(item, str) and item.strip() for item in value)
        ):
            raise reject(422, "invalid_field", "Check the requirement field.", field=key)
    quantity = requirements.get("quantity")
    if quantity is not None:
        valid = (
            isinstance(quantity, dict)
            and isinstance(quantity.get("value"), int | float)
            and not isinstance(quantity.get("value"), bool)
            and quantity["value"] > 0
            and isinstance(quantity.get("unit"), str)
            and quantity["unit"].strip()
            and (quantity.get("period") is None or isinstance(quantity.get("period"), str))
        )
        if not valid:
            raise reject(
                422,
                "invalid_quantity",
                "Quantity must be positive with a unit.",
                field="quantity",
            )
    return requirements


def validate_location(location: dict[str, Any]) -> dict[str, Any]:
    unknown = set(location) - set(LOCATION_FIELDS)
    if unknown:
        raise reject(422, "unknown_field", "Check the location fields.", fields=sorted(unknown))
    radius = location.get("radius")
    if radius is not None:
        valid = (
            isinstance(radius, dict)
            and isinstance(radius.get("value"), int | float)
            and not isinstance(radius.get("value"), bool)
            and radius["value"] > 0
            and radius.get("unit") in RADIUS_UNITS
            and isinstance(location.get("reference_location"), str)
            and location["reference_location"].strip()
        )
        if not valid:
            raise reject(
                422,
                "invalid_radius",
                "A radius needs a unit and a reference location.",
                field="radius",
            )
    for key in ("country", "reference_location"):
        value = location.get(key)
        if value is not None and not isinstance(value, str):
            raise reject(422, "invalid_field", "Check the location field.", field=key)
    return location


def revision_etag(revision: RequirementRevision) -> str:
    digest = json_hash(
        [
            revision.status,
            revision.requirements_json,
            revision.location_json,
            revision.supplier_set_json,
        ]
    )
    return f'"{revision.id}:{digest[:16]}"'


def missing_fields(requirements: dict[str, Any]) -> list[str]:
    return [key for key in REQUIREMENT_FIELDS if requirements.get(key) in (None, [], "")]


def review_flags(suppliers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Shared names/identifiers prompt buyer review; they are never silently merged."""
    seen: dict[tuple[str, str], list[int]] = {}
    for index, supplier in enumerate(suppliers):
        for item in supplier["identifiers"]:
            if item["type"] in {"name", "gstin", "udyam", "cin", "llpin", "licence_number"}:
                seen.setdefault((item["type"], item["normalized"]), []).append(index)
    return [
        {"code": "shared_identifier", "type": kind, "supplier_indexes": sorted(set(indexes))}
        for (kind, _value), indexes in seen.items()
        if len(set(indexes)) > 1
    ]


def present_revision(revision: RequirementRevision) -> dict[str, Any]:
    suppliers = list(revision.supplier_set_json)
    requirements = revision.requirements_json
    return {
        "id": str(revision.id),
        "case_id": str(revision.case_id),
        "sequence": revision.sequence,
        "status": revision.status,
        "requirements": {k: requirements.get(k, v) for k, v in REQUIREMENT_FIELDS.items()},
        "missing_fields": missing_fields(requirements),
        "field_provenance": requirements.get("field_provenance", {}),
        "location": {k: revision.location_json.get(k, v) for k, v in LOCATION_FIELDS.items()},
        "suppliers": suppliers,
        "review_flags": review_flags(suppliers),
        "input_provenance": revision.input_provenance,
        "confirmed_at": revision.confirmed_at.isoformat() if revision.confirmed_at else None,
        "confirmed_by": str(revision.confirmed_by) if revision.confirmed_by else None,
        "created_at": revision.created_at.isoformat(),
        "etag": revision_etag(revision),
    }


def _supplier_entry(
    db: Session, case: Case, entry: dict[str, Any], country: str | None
) -> dict[str, Any]:
    if not isinstance(entry, dict) or not isinstance(entry.get("identifiers", []), list):
        raise reject(422, "invalid_supplier", "Check the supplier entry.")
    identifiers = []
    for item in entry.get("identifiers", []):
        if not isinstance(item, dict):
            raise reject(422, "invalid_supplier", "Check the supplier entry.")
        kind, value = str(item.get("type", "")), item.get("value")
        if not isinstance(value, str):
            raise reject(422, "invalid_identifier", "Check the supplier identifier.", type=kind)
        identifiers.append(
            {"type": kind, "value": value.strip(), "normalized": normalize_identifier(kind, value)}
        )
    display = entry.get("display_name")
    if display is not None and not isinstance(display, str):
        raise reject(422, "invalid_supplier", "Check the supplier entry.")
    display_name = (display or "").strip() or next(
        (i["value"] for i in identifiers if i["type"] == "name"), ""
    )
    if not display_name and not identifiers:
        raise reject(422, "invalid_supplier", "A supplier needs a name or an identifier.")
    address = entry.get("address")
    role = entry.get("address_role", "unknown")
    if address is not None and not isinstance(address, str):
        raise reject(422, "invalid_supplier", "Check the supplier address.")
    if role not in SITE_ROLES:
        raise reject(422, "invalid_supplier", "Check the supplier address role.")

    supplier: Supplier | None = None
    if entry.get("supplier_id") is not None:
        try:
            supplier = db.get(Supplier, UUID(str(entry["supplier_id"])))
        except ValueError:
            supplier = None
        if supplier is None or supplier.case_id != case.id:
            raise reject(404, "not_found", "This resource is unavailable.")
    normalized = [{"type": i["type"], "value": i["normalized"]} for i in identifiers]
    originals = [{"type": i["type"], "value": i["value"]} for i in identifiers]
    if supplier is None:
        supplier = Supplier(
            case_id=case.id,
            display_name=display_name or "(unnamed supplier)",
            original_identifiers=originals,
            normalized_identifiers=normalized,
            source_refs=[{"origin": "buyer_input"}],
        )
        db.add(supplier)
        db.flush()
    else:
        supplier.display_name = display_name or supplier.display_name
        supplier.original_identifiers = originals
        supplier.normalized_identifiers = normalized
    site_id: str | None = None
    if address and address.strip():
        site = db.scalar(
            select(SupplierSite).where(
                SupplierSite.case_id == case.id,
                SupplierSite.supplier_id == supplier.id,
                SupplierSite.raw_address == address,
            )
        )
        if site is None:
            site = SupplierSite(
                case_id=case.id,
                supplier_id=supplier.id,
                raw_address=address,
                normalized_address={
                    "schema_version": SCHEMA_VERSION,
                    "text": " ".join(address.split()),
                },
                role=role,
                jurisdiction=country or "unknown",
                identity_state="unresolved",
                evidence_refs=[],
            )
            db.add(site)
            db.flush()
        site_id = str(site.id)
    return {
        "supplier_id": str(supplier.id),
        "display_name": supplier.display_name,
        "identifiers": identifiers,
        "address": address,
        "address_role": role if address else None,
        "site_id": site_id,
    }


def set_suppliers(
    db: Session, case: Case, entries: list[dict[str, Any]], country: str | None
) -> list[dict[str, Any]]:
    if not isinstance(entries, list) or len(entries) > 200:
        raise reject(422, "invalid_supplier", "Check the supplier list.")
    return [_supplier_entry(db, case, entry, country) for entry in entries]


def provenance_for(fields: list[str], source: str = "buyer") -> dict[str, Any]:
    stamp = datetime.now(UTC).isoformat()
    return {name: {"source": source, "at": stamp} for name in fields}


def create_case_draft(
    db: Session,
    *,
    buyer_id: UUID,
    title: str,
    initial_text: str | None,
    suppliers: list[dict[str, Any]],
) -> tuple[Case, RequirementRevision, ConversationMessage | None]:
    case = Case(owner_id=buyer_id, title=title.strip() or "Untitled case")
    db.add(case)
    db.flush()
    message = None
    if initial_text and initial_text.strip():
        message = ConversationMessage(
            case_id=case.id,
            actor="buyer",
            text=initial_text.strip(),
            component_refs=[],
            sequence=1,
        )
        db.add(message)
        db.flush()
    entries = set_suppliers(db, case, suppliers, None)
    revision = RequirementRevision(
        case_id=case.id,
        sequence=1,
        status="draft",
        requirements_json={
            "schema_version": SCHEMA_VERSION,
            **REQUIREMENT_FIELDS,
            "field_provenance": {},
        },
        location_json={"schema_version": SCHEMA_VERSION, **LOCATION_FIELDS},
        supplier_set_json=entries,
        input_provenance={
            "schema_version": SCHEMA_VERSION,
            "mode": "buyer_text" if message else "buyer_form",
            "message_id": str(message.id) if message else None,
            "text_sha256": hashlib.sha256(initial_text.strip().encode()).hexdigest()
            if initial_text and initial_text.strip()
            else None,
        },
    )
    db.add(revision)
    db.flush()
    if message is not None:
        message.revision_id = revision.id
    return case, revision, message


def apply_revision_patch(
    db: Session, case: Case, revision: RequirementRevision, body: dict[str, Any]
) -> None:
    if revision.status != "draft":
        raise reject(409, "revision_confirmed", "Confirmed revisions are immutable.")
    unknown = set(body) - {"requirements", "location", "suppliers"}
    if unknown:
        raise reject(422, "unknown_field", "Check the submitted fields.", fields=sorted(unknown))
    requirements = dict(revision.requirements_json)
    location = dict(revision.location_json)
    if "requirements" in body:
        update = validate_requirements(dict(body["requirements"]))
        requirements.update(update)
        provenance = dict(requirements.get("field_provenance", {}))
        provenance.update(provenance_for(sorted(update)))
        requirements["field_provenance"] = provenance
    if "location" in body:
        update = dict(body["location"])
        validate_location({**{k: location.get(k) for k in LOCATION_FIELDS}, **update})
        location = {**location, **update}
    revision.requirements_json = requirements
    revision.location_json = location
    if "suppliers" in body:
        revision.supplier_set_json = set_suppliers(
            db, case, list(body["suppliers"]), location.get("country")
        )


def confirm_revision(
    db: Session, case: Case, revision: RequirementRevision, buyer_id: UUID
) -> None:
    if revision.status != "draft":
        raise reject(409, "revision_confirmed", "This revision is already confirmed.")
    requirements = revision.requirements_json
    problems = []
    if not (requirements.get("part_description") or "").strip():
        problems.append("part_description")
    if not revision.supplier_set_json:
        problems.append("suppliers")
    if problems:
        raise reject(
            422,
            "incomplete_requirements",
            "Complete the required fields before confirming.",
            fields=problems,
        )
    validate_requirements({k: requirements.get(k) for k in REQUIREMENT_FIELDS})
    revision.status = "confirmed"
    revision.confirmed_at = datetime.now(UTC)
    revision.confirmed_by = buyer_id
    case.active_revision_id = revision.id
    if case.state == "draft":
        case.state = "ready"


def next_message_sequence(db: Session, case_id: UUID) -> int:
    return (
        int(
            db.scalar(
                select(func.coalesce(func.max(ConversationMessage.sequence), 0)).where(
                    ConversationMessage.case_id == case_id
                )
            )
            or 0
        )
        + 1
    )
