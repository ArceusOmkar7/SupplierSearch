"""Separated claims, editable criteria/required flags and immutable checklist confirmation.

Claims are proposed only from a confirmed revision. Required-for-shortlist flags are the
buyer's explicit choice: nothing is flagged by default, and confirmation needs at least one
required claim so a shortlist can never be vacuously qualified.
"""

import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from verisource.api.errors import reject
from verisource.db.models import (
    Case,
    ChecklistVersion,
    Claim,
    RequirementRevision,
)
from verisource.db.models.verification import CLAIM_TYPES
from verisource.domain.intake import json_hash

POLICY_VERSION = "core-v1"
CRITERION_KEYS = {
    "criterion_id",
    "assertion",
    "evidence_class",
    "authority",
    "independent_corroboration",
    "constraints",
    "missing_evidence_condition",
}


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")[:60] or "item"


def criterion(
    key: str,
    assertion: str,
    evidence_class: str,
    authority: list[str],
    *,
    independent: bool,
    site: bool = False,
    missing: str,
) -> dict[str, Any]:
    return {
        "criterion_id": key,
        "assertion": assertion,
        "evidence_class": evidence_class,
        "authority": authority,
        "independent_corroboration": independent,
        "constraints": {"identity": True, "site": site, "period": True},
        "missing_evidence_condition": missing,
    }


def criteria(*items: dict[str, Any]) -> dict[str, Any]:
    return {"schema_version": 1, "criteria": list(items)}


def validate_criteria(value: Any) -> dict[str, Any]:
    if (
        not isinstance(value, dict)
        or not isinstance(value.get("criteria"), list)
        or not value["criteria"]
    ):
        raise reject(422, "invalid_criteria", "Every claim needs explicit proof criteria.")
    seen: set[str] = set()
    for item in value["criteria"]:
        if (
            not isinstance(item, dict)
            or CRITERION_KEYS - set(item)
            or not isinstance(item["criterion_id"], str)
            or not item["criterion_id"]
            or item["criterion_id"] in seen
            or not isinstance(item["assertion"], str)
            or not item["assertion"].strip()
            or not isinstance(item["independent_corroboration"], bool)
            or not isinstance(item["constraints"], dict)
            or not isinstance(item["authority"], list)
        ):
            raise reject(422, "invalid_criteria", "Check the proof criteria.")
        seen.add(item["criterion_id"])
    return {"schema_version": 1, "criteria": [dict(item) for item in value["criteria"]]}


class ClaimDraft:
    def __init__(
        self,
        supplier_id: UUID,
        site_id: UUID | None,
        claim_type: str,
        assertion: str,
        proof: dict[str, Any],
        *,
        parent: ClaimDraft | None = None,
    ) -> None:
        self.id = uuid4()
        self.supplier_id = supplier_id
        self.site_id = site_id
        self.type = claim_type
        self.assertion = assertion
        self.proof = proof
        self.parent = parent


def propose_claims(
    requirements: dict[str, Any], suppliers: list[dict[str, Any]]
) -> list[ClaimDraft]:
    """Deterministic standard separated claims for each frozen supplier."""
    drafts: list[ClaimDraft] = []
    part = (requirements.get("part_description") or "the confirmed requirement").strip()
    for entry in suppliers:
        supplier_id = UUID(entry["supplier_id"])
        site = UUID(entry["site_id"]) if entry.get("site_id") else None
        name = entry["display_name"]
        drafts.append(
            ClaimDraft(
                supplier_id,
                None,
                "legal_existence",
                f"{name} is a legally existing, active entity",
                criteria(
                    criterion(
                        "legal.registry",
                        "Matching official registry record shows an active entity",
                        "official_registry_current",
                        ["official_registry"],
                        independent=False,
                        missing="No matching current official registry result",
                    )
                ),
            )
        )
        drafts.append(
            ClaimDraft(
                supplier_id,
                site,
                "manufacturer",
                f"{name} manufactures at the relevant production site",
                criteria(
                    criterion(
                        "manufacturer.site_activity",
                        "Production-site evidence for the relevant activity",
                        "production_site_record",
                        ["official_publication", "third_party"],
                        independent=True,
                        site=True,
                        missing="No attributable production-site record",
                    )
                ),
            )
        )
        capability = ClaimDraft(
            supplier_id,
            site,
            "part_capability",
            f"{name} can produce: {part}",
            criteria(
                criterion(
                    "capability.overall",
                    "Every required material, process and tolerance subclaim is proven",
                    "capability_record",
                    ["third_party", "buyer"],
                    independent=True,
                    site=True,
                    missing="Required capability subclaims are not all proven",
                )
            ),
        )
        drafts.append(capability)
        for label, values in (
            ("material", requirements.get("materials") or []),
            ("process", requirements.get("processes") or []),
        ):
            for value in values:
                drafts.append(
                    ClaimDraft(
                        supplier_id,
                        site,
                        "part_capability",
                        f"{name} handles {label}: {value}",
                        criteria(
                            criterion(
                                f"capability.{label}.{slug(str(value))}",
                                f"Independent record of {label} {value}",
                                "production_or_inspection_record",
                                ["third_party", "buyer"],
                                independent=True,
                                site=True,
                                missing=f"No independent record of {label} {value}",
                            )
                        ),
                        parent=capability,
                    )
                )
        for certification in requirements.get("certifications") or []:
            parent = ClaimDraft(
                supplier_id,
                site,
                "certificate",
                f"{name} holds a valid {certification} certificate",
                criteria(
                    criterion(
                        "certificate.compound",
                        "Status, accreditation, scope and site are all proven",
                        "certificate_set",
                        ["issuer", "accreditation_body"],
                        independent=True,
                        site=True,
                        missing="Not every certificate subclaim is proven",
                    )
                ),
            )
            drafts.append(parent)
            for key, text, cls, authority in (
                (
                    "validity",
                    "certificate status is valid at the relevant time",
                    "issuer_status",
                    ["issuer"],
                ),
                (
                    "accreditation",
                    "issuer holds relevant accreditation",
                    "accreditation_record",
                    ["accreditation_body"],
                ),
                ("scope", f"certificate scope covers {part}", "certificate_scope", ["issuer"]),
                ("site", "certificate covers the production site", "certificate_site", ["issuer"]),
            ):
                drafts.append(
                    ClaimDraft(
                        supplier_id,
                        site,
                        "certificate",
                        f"{certification}: {text}",
                        criteria(
                            criterion(
                                f"certificate.{key}",
                                text,
                                cls,
                                authority,
                                independent=False,
                                site=key == "site",
                                missing=f"No authoritative {key} evidence",
                            )
                        ),
                        parent=parent,
                    )
                )
        for standard in requirements.get("standards") or []:
            drafts.append(
                ClaimDraft(
                    supplier_id,
                    site,
                    "regulatory",
                    f"{name} satisfies regulatory requirement {standard}",
                    criteria(
                        criterion(
                            "regulatory.order",
                            f"Current official order, applicability and exemption basis for {standard}",
                            "official_order",
                            ["official_publication"],
                            independent=False,
                            missing="No current official applicability basis",
                        ),
                        criterion(
                            "regulatory.licence",
                            f"Current official licence covering the product and site for {standard}",
                            "licence_record",
                            ["official_publication", "official_registry"],
                            independent=False,
                            site=True,
                            missing="No current official licence record covering product and site",
                        ),
                    ),
                )
            )
        quantity = requirements.get("quantity")
        if quantity:
            drafts.append(
                ClaimDraft(
                    supplier_id,
                    site,
                    "capacity",
                    f"{name} plausibly has capacity for {quantity['value']} {quantity['unit']}",
                    criteria(
                        criterion(
                            "capacity.output",
                            "Dated site/process/output records for the required volume",
                            "capacity_record",
                            ["third_party"],
                            independent=True,
                            site=True,
                            missing="Headcount or machine counts alone cannot prove capacity",
                        )
                    ),
                )
            )
    return drafts


def etag_for(checklist: ChecklistVersion, claims: list[Claim]) -> str:
    digest = json_hash([checklist.status, [present_claim(c) for c in claims]])
    return f'"{checklist.id}:{digest[:16]}"'


def present_claim(claim: Claim) -> dict[str, Any]:
    return {
        "id": str(claim.id),
        "supplier_id": str(claim.supplier_id),
        "site_id": str(claim.site_id) if claim.site_id else None,
        "parent_claim_id": str(claim.parent_claim_id) if claim.parent_claim_id else None,
        "type": claim.type,
        "assertion": claim.assertion,
        "relevant_period": claim.relevant_period,
        "required_for_shortlist": claim.required_for_shortlist,
        "proof_criteria": claim.proof_criteria_json,
        "processing_state": claim.processing_state,
        "waiting_input": claim.waiting_input,
    }


def load_claims(db: Session, checklist: ChecklistVersion) -> list[Claim]:
    return list(
        db.scalars(
            select(Claim)
            .where(Claim.case_id == checklist.case_id, Claim.checklist_id == checklist.id)
            .order_by(Claim.id)
        )
    )


def present_checklist(db: Session, checklist: ChecklistVersion) -> dict[str, Any]:
    claims = load_claims(db, checklist)
    ordered = sorted(claims, key=lambda c: (str(c.supplier_id), c.parent_claim_id is not None))
    return {
        "id": str(checklist.id),
        "case_id": str(checklist.case_id),
        "revision_id": str(checklist.revision_id),
        "sequence": checklist.sequence,
        "status": checklist.status,
        "policy_version": checklist.policy_version,
        "confirmed_at": checklist.confirmed_at.isoformat() if checklist.confirmed_at else None,
        "confirmed_by": str(checklist.confirmed_by) if checklist.confirmed_by else None,
        "claims": [present_claim(c) for c in ordered],
        "etag": etag_for(checklist, claims),
    }


def create_draft_checklist(
    db: Session, case: Case, revision: RequirementRevision
) -> ChecklistVersion:
    if revision.status != "confirmed":
        raise reject(409, "revision_not_confirmed", "Confirm the requirement revision first.")
    existing = list(
        db.scalars(
            select(ChecklistVersion).where(
                ChecklistVersion.case_id == case.id, ChecklistVersion.revision_id == revision.id
            )
        )
    )
    draft = next((c for c in existing if c.status == "draft"), None)
    if draft is not None:
        return draft
    if existing:
        raise reject(409, "checklist_exists", "Use a new checklist version for confirmed work.")
    checklist = ChecklistVersion(
        case_id=case.id, revision_id=revision.id, sequence=1, policy_version=POLICY_VERSION
    )
    db.add(checklist)
    db.flush()
    drafts = propose_claims(revision.requirements_json, revision.supplier_set_json)
    for item in drafts:  # Parents first so composite parent keys resolve.
        if item.parent is None:
            _add_claim(db, case, revision, checklist, item)
    db.flush()
    for item in drafts:
        if item.parent is not None:
            _add_claim(db, case, revision, checklist, item)
    db.flush()
    return checklist


def _add_claim(
    db: Session,
    case: Case,
    revision: RequirementRevision,
    checklist: ChecklistVersion,
    item: ClaimDraft,
) -> Claim:
    claim = Claim(
        id=item.id,
        case_id=case.id,
        revision_id=revision.id,
        checklist_id=checklist.id,
        supplier_id=item.supplier_id,
        site_id=item.site_id,
        parent_claim_id=item.parent.id if item.parent else None,
        type=item.type,
        assertion=item.assertion,
        relevant_period={"kind": "current", "as_of": None},
        required_for_shortlist=False,
        proof_criteria_json=item.proof,
    )
    db.add(claim)
    return claim


def clone_checklist(db: Session, case: Case, source: ChecklistVersion) -> ChecklistVersion:
    """Edits to a confirmed checklist are made in a new draft version; the old one stays."""
    if source.status != "confirmed":
        raise reject(409, "checklist_not_confirmed", "Only a confirmed checklist is versioned.")
    if db.scalar(
        select(ChecklistVersion).where(
            ChecklistVersion.case_id == case.id,
            ChecklistVersion.revision_id == source.revision_id,
            ChecklistVersion.status == "draft",
        )
    ):
        raise reject(409, "draft_exists", "A draft checklist already exists for this revision.")
    sequence = int(
        db.scalar(
            select(func.max(ChecklistVersion.sequence)).where(
                ChecklistVersion.case_id == case.id,
                ChecklistVersion.revision_id == source.revision_id,
            )
        )
        or 0
    )
    draft = ChecklistVersion(
        case_id=case.id,
        revision_id=source.revision_id,
        sequence=sequence + 1,
        policy_version=source.policy_version,
    )
    db.add(draft)
    db.flush()
    mapping: dict[UUID, UUID] = {}
    originals = load_claims(db, source)
    for original in sorted(originals, key=lambda c: c.parent_claim_id is not None):
        copy = Claim(
            case_id=case.id,
            revision_id=original.revision_id,
            checklist_id=draft.id,
            supplier_id=original.supplier_id,
            site_id=original.site_id,
            parent_claim_id=mapping.get(original.parent_claim_id)
            if original.parent_claim_id
            else None,
            type=original.type,
            assertion=original.assertion,
            relevant_period=original.relevant_period,
            required_for_shortlist=original.required_for_shortlist,
            proof_criteria_json=original.proof_criteria_json,
        )
        db.add(copy)
        db.flush()
        mapping[original.id] = copy.id
    return draft


def apply_checklist_patch(
    db: Session, case: Case, checklist: ChecklistVersion, body: dict[str, Any]
) -> None:
    if checklist.status != "draft":
        raise reject(409, "checklist_confirmed", "Confirmed checklists are immutable.")
    unknown = set(body) - {"claims", "add", "remove"}
    if unknown:
        raise reject(422, "unknown_field", "Check the submitted fields.", fields=sorted(unknown))
    claims = {c.id: c for c in load_claims(db, checklist)}
    for change in body.get("claims", []):
        claim = claims.get(_uuid(change.get("id")))
        if claim is None:
            raise reject(404, "not_found", "This resource is unavailable.")
        if "required_for_shortlist" in change:
            if not isinstance(change["required_for_shortlist"], bool):
                raise reject(422, "invalid_field", "Check the required flag.")
            claim.required_for_shortlist = change["required_for_shortlist"]
        if "assertion" in change:
            if not isinstance(change["assertion"], str) or not change["assertion"].strip():
                raise reject(422, "invalid_field", "Check the claim assertion.")
            claim.assertion = change["assertion"].strip()
        if "relevant_period" in change:
            if not isinstance(change["relevant_period"], dict):
                raise reject(422, "invalid_field", "Check the relevant period.")
            claim.relevant_period = change["relevant_period"]
        if "proof_criteria" in change:
            claim.proof_criteria_json = validate_criteria(change["proof_criteria"])
    for removal in body.get("remove", []):
        target = claims.get(_uuid(removal))
        if target is None:
            raise reject(404, "not_found", "This resource is unavailable.")
        db.delete(target)  # Children cascade through the composite parent key.
    for addition in body.get("add", []):
        supplier_id = _uuid(addition.get("supplier_id"))
        revision = db.get(RequirementRevision, checklist.revision_id)
        assert revision is not None
        if str(supplier_id) not in {s["supplier_id"] for s in revision.supplier_set_json}:
            raise reject(404, "not_found", "This resource is unavailable.")
        if addition.get("type") not in CLAIM_TYPES:
            raise reject(422, "invalid_field", "Check the claim type.")
        parent = (
            claims.get(_uuid(addition["parent_claim_id"]))
            if addition.get("parent_claim_id")
            else None
        )
        if addition.get("parent_claim_id") and (
            parent is None or parent.supplier_id != supplier_id
        ):
            raise reject(404, "not_found", "This resource is unavailable.")
        if not isinstance(addition.get("assertion"), str) or not addition["assertion"].strip():
            raise reject(422, "invalid_field", "Check the claim assertion.")
        db.add(
            Claim(
                case_id=case.id,
                revision_id=checklist.revision_id,
                checklist_id=checklist.id,
                supplier_id=supplier_id,
                parent_claim_id=parent.id if parent else None,
                type=addition["type"],
                assertion=addition["assertion"].strip(),
                relevant_period=addition.get("relevant_period")
                or {"kind": "current", "as_of": None},
                required_for_shortlist=bool(addition.get("required_for_shortlist", False)),
                proof_criteria_json=validate_criteria(addition.get("proof_criteria")),
            )
        )
    db.flush()


def _uuid(value: Any) -> UUID:
    try:
        return UUID(str(value))
    except ValueError:
        raise reject(404, "not_found", "This resource is unavailable.") from None


def confirm_checklist(db: Session, case: Case, checklist: ChecklistVersion, buyer_id: UUID) -> None:
    if checklist.status != "draft":
        raise reject(409, "checklist_confirmed", "This checklist is already confirmed.")
    claims = load_claims(db, checklist)
    if not claims:
        raise reject(422, "no_claims", "Add at least one claim.")
    for claim in claims:
        validate_criteria(claim.proof_criteria_json)
        if not claim.relevant_period:
            raise reject(422, "missing_period", "Every claim needs a relevant period.")
    if not any(claim.required_for_shortlist for claim in claims):
        raise reject(
            422,
            "no_required_claim",
            "Select at least one claim as required for the shortlist.",
        )
    for claim in claims:
        claim.processing_state = "confirmed"
    checklist.status = "confirmed"
    checklist.confirmed_at = datetime.now(UTC)
    checklist.confirmed_by = buyer_id
