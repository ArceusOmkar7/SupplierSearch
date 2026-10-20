"""Immutable snapshot reads and explicit snapshot-bound buyer decisions."""

from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Query, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from verisource.api.cases import (
    IdempotencyKey,
    IfMatch,
    command_response,
    decode_cursor,
    encode_cursor,
    page,
)
from verisource.api.dependencies import Database, MutationSession, SignedIn, owned_case, owned_child
from verisource.api.errors import reject
from verisource.db.models import AssessmentSnapshot, Case, SupplierDecision
from verisource.domain.commands import execute_command

router = APIRouter(prefix="/api/v1")


class DecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    snapshot_id: UUID
    decision: Literal["select", "reject", "no_selection"]
    supplier_id: UUID | None = None
    reason: str | None = None


def present_decision(decision: SupplierDecision) -> dict[str, Any]:
    return {
        "id": str(decision.id),
        "snapshot_id": str(decision.snapshot_id),
        "supplier_id": str(decision.supplier_id) if decision.supplier_id else None,
        "decision": decision.decision,
        "reason": decision.reason,
        "buyer_id": str(decision.buyer_id),
        "created_at": decision.created_at.isoformat(),
    }


def summarize(snapshot: AssessmentSnapshot, case: Case | None = None) -> dict[str, Any]:
    coverage = snapshot.coverage_summary
    return {
        "historical": case is not None and snapshot.revision_id != case.active_revision_id,
        "closed_snapshot": case is not None
        and case.state == "closed"
        and case.latest_snapshot_id == snapshot.id,
        "id": str(snapshot.id),
        "case_id": str(snapshot.case_id),
        "run_id": str(snapshot.run_id),
        "revision_id": str(snapshot.revision_id),
        "checklist_id": str(snapshot.checklist_id),
        "sequence": snapshot.sequence,
        "trigger": snapshot.trigger,
        "created_at": snapshot.created_at.isoformat(),
        "event_cutoff": snapshot.event_cutoff,
        "content_hash": snapshot.content_hash,
        "partial": bool(snapshot.pending_action_refs)
        or any(state != "complete" for state in snapshot.supplier_processing_states.values())
        or coverage.get("evaluated_claims", 0) < coverage.get("total_claims", 0),
        "counts": {
            "qualified": len(snapshot.qualified_ids),
            "follow_up": len(snapshot.follow_up_ids),
            "excluded": len(snapshot.excluded_reasons),
        },
    }


@router.get("/cases/{case_id}/snapshots")
def list_snapshots(
    case_id: UUID,
    session: SignedIn,
    db: Database,
    cursor: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    run_id: UUID | None = None,
    revision_id: UUID | None = None,
) -> dict[str, Any]:
    case = owned_case(db, case_id, session.buyer_id)
    query = (
        select(AssessmentSnapshot)
        .where(AssessmentSnapshot.case_id == case.id)
        .order_by(AssessmentSnapshot.created_at.desc(), AssessmentSnapshot.id.desc())
        .limit(limit + 1)
    )
    if run_id:
        query = query.where(AssessmentSnapshot.run_id == run_id)
    if revision_id:
        query = query.where(AssessmentSnapshot.revision_id == revision_id)
    parts = decode_cursor(cursor)
    if parts:
        skip = int(parts[0])
        query = query.offset(skip)
    items = [summarize(s, case) for s in db.scalars(query)]
    start = int(parts[0]) if parts else 0
    return page(items, limit, lambda item: encode_cursor(start + limit))


@router.get("/cases/{case_id}/snapshots/{snapshot_id}")
def read_snapshot(
    case_id: UUID, snapshot_id: UUID, response: Response, session: SignedIn, db: Database
) -> dict[str, Any]:
    snapshot = owned_child(
        db, AssessmentSnapshot, snapshot_id, case_id=case_id, buyer_id=session.buyer_id
    )
    decisions = db.scalars(
        select(SupplierDecision)
        .where(
            SupplierDecision.case_id == snapshot.case_id,
            SupplierDecision.snapshot_id == snapshot.id,
        )
        .order_by(SupplierDecision.created_at)
    )
    response.headers["ETag"] = f'"{snapshot.id}:{snapshot.content_hash[:16]}"'
    return {
        **summarize(snapshot, owned_case(db, case_id, session.buyer_id)),
        "content": snapshot.content_json,
        "decisions": [present_decision(d) for d in decisions],
    }


@router.post("/cases/{case_id}/decisions")
def decide(
    case_id: UUID,
    body: DecisionRequest,
    session: MutationSession,
    db: Database,
    key: IdempotencyKey = None,
    if_match: IfMatch = None,
) -> JSONResponse:
    def apply(case: Case) -> dict[str, Any]:
        if case.state == "closed":
            raise reject(409, "case_closed", "Reopen the case before recording decisions.")
        snapshot = owned_child(
            db, AssessmentSnapshot, body.snapshot_id, case_id=case.id, buyer_id=case.owner_id
        )
        suppliers = {s["supplier_id"]: s for s in snapshot.content_json["suppliers"]}
        reason = (body.reason or "").strip() or None
        if body.decision == "no_selection":
            if body.supplier_id is not None:
                raise reject(
                    422, "invalid_field", "No supplier applies to a no-selection decision."
                )
        else:
            entry = suppliers.get(str(body.supplier_id))
            if entry is None:
                raise reject(404, "not_found", "This resource is unavailable.")
            if body.decision == "select":
                if entry["status"] == "excluded":
                    raise reject(
                        409, "supplier_excluded", "A contradicted supplier cannot be selected."
                    )
                if entry["status"] == "follow_up" and reason is None:
                    raise reject(
                        422,
                        "reason_required",
                        "Explain why a supplier with unproven required claims is selected.",
                    )
        decision = SupplierDecision(
            case_id=case.id,
            snapshot_id=snapshot.id,
            supplier_id=body.supplier_id,
            decision=body.decision,
            buyer_id=case.owner_id,
            reason=reason,
            operation_key=str(key),
        )
        db.add(decision)
        db.flush()
        return {"decision": present_decision(decision)}

    result, etag = execute_command(
        db,
        case_id=case_id,
        buyer_id=session.buyer_id,
        operation="decide",
        key=key,
        if_match=if_match,
        body=body.model_dump(mode="json"),
        apply=apply,
    )
    return command_response(result, etag, 201)
