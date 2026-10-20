"""Draft-only interpretation of buyer text and standalone document extraction jobs.

Interpretation fills only empty draft fields, marks them `model_proposed` with the quoted
source text, and never confirms, starts a run or selects a supplier.
"""

import hashlib
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from verisource.config import Settings
from verisource.db.models import (
    Case,
    ConversationMessage,
    DocumentArtifact,
    Extraction,
    RequirementRevision,
)
from verisource.documents.certificates import SCHEMA_VERSION, extract_certificate, inspect_pdf
from verisource.domain import intake
from verisource.domain.commands import append_event
from verisource.models.ollama import ModelUnavailable
from verisource.models.router import ModelRouter
from verisource.models.schemas import RequirementInterpretation, quote_supported, verify_located
from verisource.orchestration.jobs import Lease
from verisource.storage.filesystem import PrivateFileStore

Applier = Callable[[Session], None]
INSTRUCTIONS = (
    "Read this buyer message. Extract the requested part or equipment description, materials, "
    "processes, certifications, standards and any supplier names the buyer wrote. Do not invent "
    "quantities or capabilities."
)


def interpret_message(
    engine: Engine, router: ModelRouter, lease: Lease, lost: threading.Event
) -> Applier:
    message_id = UUID(str(lease.references["message_id"]))
    with Session(engine) as db:
        message = db.get(ConversationMessage, message_id)
        if message is None:
            return lambda _db: None
        text = message.text
    note = "Draft updated from your message. Review every field and confirm explicitly."
    proposal: RequirementInterpretation | None = None
    try:
        proposal, _backend = router.extract(
            RequirementInterpretation, INSTRUCTIONS, text, data_class="private"
        )
    except ModelUnavailable:
        note = (
            "Automatic interpretation is unavailable. Your message is kept; edit the draft "
            "fields directly."
        )

    def apply(db: Session) -> None:
        message = db.get(ConversationMessage, message_id)
        if message is None:
            return
        case = db.get(Case, message.case_id)
        assert case is not None
        revision = db.get(RequirementRevision, message.revision_id) if message.revision_id else None
        if revision is None:
            revision = db.scalar(
                select(RequirementRevision).where(
                    RequirementRevision.case_id == case.id, RequirementRevision.status == "draft"
                )
            )
        if proposal is not None and revision is not None and revision.status == "draft":
            _apply_proposal(db, case, revision, proposal, text)
        if db.scalar(
            select(ConversationMessage.id).where(
                ConversationMessage.case_id == case.id,
                ConversationMessage.client_message_id == f"interpret:{message_id}",
            )
        ):
            return
        reply = ConversationMessage(
            case_id=case.id,
            revision_id=revision.id if revision else None,
            actor="assistant",
            text=note,
            component_refs=[{"type": "requirement_review", "revision_id": str(revision.id)}]
            if revision
            else [],
            sequence=intake.next_message_sequence(db, case.id),
            client_message_id=f"interpret:{message_id}",
        )
        db.add(reply)
        db.flush()
        append_event(
            db,
            case.id,
            "message.created",
            f"message:{reply.id}",
            {"message_id": str(reply.id)},
            revision_id=reply.revision_id,
        )

    return apply


def _apply_proposal(
    db: Session,
    case: Case,
    revision: RequirementRevision,
    proposal: RequirementInterpretation,
    text: str,
) -> None:
    pages = {1: text}
    notes: list[str] = []
    requirements = dict(revision.requirements_json)
    provenance = dict(requirements.get("field_provenance", {}))
    stamp = datetime.now(UTC).isoformat()

    def propose(field: str, value: object, quote: str) -> None:
        provenance[field] = {"source": "model_proposed", "at": stamp, "quote": quote}
        requirements[field] = value

    description = verify_located(proposal.part_description, pages, "part_description", notes)
    if description and not requirements.get("part_description"):
        propose("part_description", description.value, description.quote)
    for field, items in (
        ("materials", proposal.materials),
        ("processes", proposal.processes),
        ("certifications", proposal.certifications),
        ("standards", proposal.standards),
    ):
        verified = [v for v in (verify_located(i, pages, field, notes) for i in items) if v]
        if verified and not requirements.get(field):
            propose(field, [v.value for v in verified], " | ".join(v.quote for v in verified))
    requirements["field_provenance"] = provenance
    if notes:
        requirements["interpretation_notes"] = notes
    revision.requirements_json = requirements
    existing = {intake.normalize_name(s["display_name"]) for s in revision.supplier_set_json}
    additions = []
    for mention in proposal.suppliers:
        if (
            quote_supported(mention.quote, text)
            and intake.normalize_name(mention.name) not in existing
        ):
            additions.append(
                {
                    "display_name": mention.name,
                    "identifiers": [{"type": "name", "value": mention.name}],
                }
            )
            existing.add(intake.normalize_name(mention.name))
    if additions:
        revision.supplier_set_json = [
            *revision.supplier_set_json,
            *intake.set_suppliers(db, case, additions, revision.location_json.get("country")),
        ]
    db.flush()
    append_event(
        db,
        case.id,
        "revision.updated",
        f"revision-interpreted:{revision.id}:{hashlib.sha256(text.encode()).hexdigest()[:12]}",
        {"revision_id": str(revision.id), "status": "draft"},
        revision_id=revision.id,
    )


def extract_document(
    engine: Engine,
    settings: Settings,
    router: ModelRouter | None,
    lease: Lease,
    lost: threading.Event,
) -> Applier:
    document_id = UUID(str(lease.references["document_id"]))
    store = PrivateFileStore(settings.data_root)
    with Session(engine) as db:
        document = db.get(DocumentArtifact, document_id)
        if document is None or document.state != "queued":
            return lambda _db: None
        content = store.read(document.storage_key, document.sha256)
    inspection = inspect_pdf(content)
    fields, method, missing = (
        extract_certificate(router, inspection) if not inspection.failure_reason else (None, "", [])
    )

    def apply(db: Session) -> None:
        document = db.get(DocumentArtifact, document_id)
        if document is None or document.state != "queued":
            return
        if inspection.failure_reason or fields is None:
            document.state = "quarantined"
            document.state_reason = inspection.failure_reason
            return
        data = {
            name: getattr(fields, name).model_dump()
            for name in (
                "certificate_number",
                "holder_name",
                "issuer",
                "standard",
                "scope",
                "site_address",
                "issue_date",
                "expiry_date",
            )
            if getattr(fields, name) is not None
        }
        db.add(
            Extraction(
                case_id=document.case_id,
                artifact_id=document.id,
                page_refs=sorted(inspection.pages),
                method="rule" if method == "rule" else "model",
                fields=data,
                missing_fields=missing,
                uncertainties=list(fields.uncertainties),
                model_id=None if method == "rule" else method,
                schema_version=SCHEMA_VERSION,
                content_hash=hashlib.sha256(repr(sorted(data.items())).encode()).hexdigest(),
            )
        )
        document.state = "extracted"
        append_event(
            db,
            document.case_id,
            "revision.updated",
            f"document-extracted:{document.id}",
            {"document_id": str(document.id), "state": "extracted"},
            revision_id=document.revision_id,
        )

    return apply
