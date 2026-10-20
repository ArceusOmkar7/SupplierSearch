"""Run admission: persist the run, independent check tasks and root work in one transaction."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from verisource.api.errors import reject
from verisource.country_packs.contracts import PlannedCheck
from verisource.country_packs.registry import UnsupportedJurisdiction, pack_for
from verisource.db.models import (
    Case,
    ChecklistVersion,
    CheckTask,
    Claim,
    RequirementRevision,
    SourceDefinition,
    VerificationRun,
)
from verisource.domain.claims import POLICY_VERSION, load_claims, present_claim
from verisource.orchestration.jobs import enqueue
from verisource.orchestration.scheduling import queue_ready
from verisource.sources.quotas import LIMITS, budgets_json

UNSUPPORTED_SOURCE = "core.unsupported-jurisdiction"


def ensure_source_definitions(db: Session, jurisdiction: str) -> None:
    """Register the pack's immutable (id, version) rows; insertion is idempotent."""
    from verisource.country_packs.india.pack import HOSTS, SOURCES

    pack = pack_for(jurisdiction)
    del pack  # Only supported packs register definitions.
    for source_id, version, mode, claims, _enabled, _reason in SOURCES:
        db.execute(
            insert(SourceDefinition)
            .values(
                id=source_id,
                version=version,
                provider_family="india",
                jurisdiction="IN",
                claim_coverage=list(claims),
                allowed_hosts=HOSTS.get(source_id, []),
                access_mode=mode,
                authority_roles=[],
                policy_checked_at=None,
                policy_refs=[],
                terms_version=None,
                capabilities={"free": True},
                created_at=datetime.now(UTC),
            )
            .on_conflict_do_nothing()
        )


def plan_for_supplier(
    revision: RequirementRevision, supplier: dict[str, Any], claims: list[Claim]
) -> tuple[str, list[PlannedCheck]]:
    country = revision.location_json.get("country") or "IN"
    supplier_id = UUID(supplier["supplier_id"])
    own = [present_claim(c) for c in claims if c.supplier_id == supplier_id]
    try:
        pack = pack_for(country)
    except UnsupportedJurisdiction:
        return (
            f"unsupported:{country}",
            [
                PlannedCheck(
                    "coverage",
                    "coverage_unsupported",
                    UNSUPPORTED_SOURCE,
                    tuple(UUID(c["id"]) for c in own),
                    supplier_id,
                )
            ],
        )
    return pack.version, pack.plan_checks(revision.requirements_json, supplier, own)


def admit_run(
    db: Session,
    case: Case,
    revision: RequirementRevision,
    checklist: ChecklistVersion,
    *,
    mode: str,
    idempotency_key: str,
) -> VerificationRun:
    if mode not in {"live", "replay"}:
        raise reject(422, "invalid_mode", "Choose live retrieval or labeled record replay.")
    if case.state in {"closed", "deleting"}:
        raise reject(409, "case_closed", "Reopen the case before starting verification.")
    if revision.status != "confirmed" or case.active_revision_id != revision.id:
        raise reject(409, "revision_not_active", "Run the current confirmed revision.")
    if checklist.status != "confirmed" or checklist.revision_id != revision.id:
        raise reject(409, "checklist_not_confirmed", "Confirm the checklist before collection.")
    claims = load_claims(db, checklist)
    if not any(c.required_for_shortlist for c in claims):
        raise reject(409, "no_required_claim", "Select a required claim first.")
    active = db.scalar(
        select(VerificationRun.id).where(
            VerificationRun.case_id == case.id,
            VerificationRun.revision_id == revision.id,
            VerificationRun.state.in_(("queued", "running")),
        )
    )
    if active is not None:
        raise reject(409, "run_active", "A verification run is already in progress.")

    now = datetime.now(UTC)
    country = revision.location_json.get("country") or "IN"
    ensure_source_definitions(db, "IN") if country.upper() == "IN" else None
    pack_version = (
        pack_for(country).version if country.upper() == "IN" else f"unsupported:{country}"
    )
    run = VerificationRun(
        id=uuid4(),
        case_id=case.id,
        revision_id=revision.id,
        checklist_id=checklist.id,
        policy_version=POLICY_VERSION,
        country_pack_version=pack_version,
        mode=mode,
        state="queued",
        requested_at=now,
        initial_deadline=now + timedelta(seconds=LIMITS.initial_report_seconds),
        budgets_json=budgets_json(),
        generation=case.write_generation,
        idempotency_key=idempotency_key,
    )
    db.add(run)
    db.flush()

    key_to_id: dict[tuple[UUID, str], UUID] = {}
    planned: list[tuple[UUID, PlannedCheck]] = []
    for supplier in revision.supplier_set_json:
        _version, checks = plan_for_supplier(revision, supplier, claims)
        for check in checks:
            task_id = uuid4()
            key_to_id[(check.supplier_id, check.key)] = task_id
            planned.append((task_id, check))
    due = now
    for task_id, check in planned:
        db.add(
            CheckTask(
                id=task_id,
                case_id=case.id,
                run_id=run.id,
                supplier_id=check.supplier_id,
                claim_ids=list(check.claim_ids),
                source_id=check.source_id,
                check_type=check.check_type,
                dependency_ids=[key_to_id[(check.supplier_id, k)] for k in check.dependency_keys],
                state="queued",
                operation_key=f"run:{run.id}:{check.supplier_id}:{check.key}",
                due_at=due,
                deadline_at=now + timedelta(seconds=LIMITS.website_deadline_seconds)
                if check.check_type == "website_traversal"
                else run.initial_deadline,
            )
        )
    db.flush()
    db.execute(
        update(Claim)
        .where(Claim.case_id == case.id, Claim.checklist_id == checklist.id)
        .values(processing_state="queued")
    )
    case.state = "active"
    enqueue(
        db,
        case,
        kind="run_deadline",
        operation_key=f"deadline:{run.id}",
        references={"run_id": str(run.id)},
        run_id=run.id,
        due_at=run.initial_deadline,
    )
    queue_ready(db, case, run)
    return run
