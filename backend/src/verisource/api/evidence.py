"""Owner-scoped evidence and attempt detail: original observation, dates, lineage, gaps."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter

from verisource.api.dependencies import Database, SignedIn, owned_child
from verisource.db.models import CheckAttempt, EvidenceRecord, IdentityResolution

router = APIRouter(prefix="/api/v1")


@router.get("/cases/{case_id}/evidence/{evidence_id}")
def read_evidence(
    case_id: UUID, evidence_id: UUID, session: SignedIn, db: Database
) -> dict[str, Any]:
    item = owned_child(db, EvidenceRecord, evidence_id, case_id=case_id, buyer_id=session.buyer_id)
    resolution = db.get(IdentityResolution, item.identity_resolution_id)
    return {
        "id": str(item.id),
        "run_id": str(item.run_id),
        "supplier_id": str(item.supplier_id),
        "site_id": str(item.site_id) if item.site_id else None,
        "source_version": item.source_version,
        "source_ref": item.source_ref,
        "locator": item.locator,
        "observation": item.observation,
        "assertion_tags": item.assertion_tags,
        "authority_role": item.authority_role,
        "self_reported": item.self_reported,
        "origin_lineage": item.origin_lineage,
        "collected_at": item.collected_at.isoformat(),
        "issued_at": item.issued_at.isoformat() if item.issued_at else None,
        "effective_at": item.effective_at.isoformat() if item.effective_at else None,
        "expires_at": item.expires_at.isoformat() if item.expires_at else None,
        "replay": item.replay,
        "content_hash": item.content_hash,
        "artifact_id": str(item.artifact_id) if item.artifact_id else None,
        "identity": {
            "state": resolution.state,
            "basis": resolution.resolution_basis,
            "matches": resolution.identifier_matches,
            "discrepancies": resolution.discrepancies,
            "score": resolution.proposed_score,
        }
        if resolution
        else None,
    }


@router.get("/cases/{case_id}/attempts/{attempt_id}")
def read_attempt(
    case_id: UUID, attempt_id: UUID, session: SignedIn, db: Database
) -> dict[str, Any]:
    a = owned_child(db, CheckAttempt, attempt_id, case_id=case_id, buyer_id=session.buyer_id)
    return {
        "id": str(a.id),
        "run_id": str(a.run_id),
        "task_id": str(a.task_id),
        "supplier_id": str(a.supplier_id),
        "claim_ids": [str(c) for c in a.claim_ids],
        "source_version": a.source_version,
        "kind": a.kind,
        "target": a.target,
        "requested_at": a.requested_at.isoformat(),
        "started_at": a.started_at.isoformat() if a.started_at else None,
        "finished_at": a.finished_at.isoformat(),
        "request_dispatched": a.request_dispatched,
        "outcome": a.outcome,
        "reason_code": a.reason_code,
        "http_status": a.http_status,
        "artifact_refs": a.artifact_refs,
        "retry_of": str(a.retry_of) if a.retry_of else None,
    }
