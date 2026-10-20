"""PostgreSQL constraints of the verification tables, using actual BIS source records.

Rows reference the genuine licence-list firms and procurement request; impossible states are
injected as disclosed controls to prove the database refuses them.
"""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from support import licence_rows
from test_foundation_schema import case_revision

from verisource.db.base import Base
from verisource.db.models import (
    Assessment,
    BuyerAccount,
    Case,
    CheckAttempt,
    ChecklistVersion,
    CheckTask,
    Claim,
    RequirementRevision,
    Supplier,
    VerificationRun,
)
from verisource.domain.claims import POLICY_VERSION

pytestmark = [pytest.mark.integration, pytest.mark.real_records]


@pytest.fixture
def db(test_database_url: str) -> Iterator[Session]:
    engine = create_engine(test_database_url, hide_parameters=True)
    with engine.connect() as connection, connection.begin() as outer:
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
            yield session
        outer.rollback()
    engine.dispose()


def build(
    db: Session,
) -> tuple[
    BuyerAccount,
    Case,
    RequirementRevision,
    Supplier,
    ChecklistVersion,
    Claim,
    VerificationRun,
    CheckTask,
]:
    account, case, revision = case_revision(db)
    row = licence_rows()[0]
    supplier = Supplier(
        case_id=case.id,
        display_name=row.firm_name,
        original_identifiers=[{"type": "licence_number", "value": row.licence_no}],
        normalized_identifiers=[{"type": "licence_number", "value": row.licence_no}],
        source_refs=[],
    )
    db.add(supplier)
    db.flush()
    revision.supplier_set_json = [
        {"supplier_id": str(supplier.id), "display_name": supplier.display_name}
    ]
    revision.status = "confirmed"
    revision.confirmed_at = datetime.now(UTC)
    revision.confirmed_by = account.id
    checklist = ChecklistVersion(
        case_id=case.id, revision_id=revision.id, sequence=1, policy_version=POLICY_VERSION
    )
    db.add(checklist)
    db.flush()
    claim = Claim(
        case_id=case.id,
        revision_id=revision.id,
        checklist_id=checklist.id,
        supplier_id=supplier.id,
        type="legal_existence",
        assertion="Actual firm is a legally existing entity",
        relevant_period={"kind": "current"},
        proof_criteria_json={"criteria": []},
    )
    db.add(claim)
    now = datetime.now(UTC)
    run = VerificationRun(
        case_id=case.id,
        revision_id=revision.id,
        checklist_id=checklist.id,
        policy_version=POLICY_VERSION,
        country_pack_version="IN/core-v1",
        mode="live",
        requested_at=now,
        initial_deadline=now + timedelta(minutes=30),
        budgets_json={},
        generation=1,
        idempotency_key=str(uuid4()),
    )
    db.add(run)
    db.flush()
    task = CheckTask(
        case_id=case.id,
        run_id=run.id,
        supplier_id=supplier.id,
        claim_ids=[claim.id],
        source_id="in.local-export",
        check_type="local_export_lookup",
        dependency_ids=[],
        operation_key=str(uuid4()),
        due_at=now,
        deadline_at=now,
    )
    db.add(task)
    db.flush()
    return account, case, revision, supplier, checklist, claim, run, task


def attempt(
    case: Case,
    run: VerificationRun,
    revision: RequirementRevision,
    supplier: Supplier,
    task: CheckTask,
    **overrides: Any,
) -> CheckAttempt:
    now = datetime.now(UTC)
    values = {
        "case_id": case.id,
        "run_id": run.id,
        "task_id": task.id,
        "revision_id": revision.id,
        "supplier_id": supplier.id,
        "claim_ids": [],
        "source_version": "in.local-export@1",
        "kind": "remote_request",
        "target": "https://bis.gov.in/copyright-policy/",
        "requested_at": now,
        "finished_at": now,
        "request_dispatched": True,
        "outcome": "success",
        "artifact_refs": [],
        "operation_key": str(uuid4()),
    }
    values.update(overrides)
    return CheckAttempt(**values)


def rejected(db: Session, row: Base) -> bool:
    try:
        with db.begin_nested():
            db.add(row)
            db.flush()
    except DBAPIError:
        return True
    return False


def test_attempt_rules_reject_impossible_states(db: Session) -> None:
    _a, case, revision, supplier, _c, _claim, run, task = build(db)
    assert not rejected(db, attempt(case, run, revision, supplier, task))
    # A local capability decision cannot claim a network dispatch.
    assert rejected(
        db,
        attempt(
            case,
            run,
            revision,
            supplier,
            task,
            kind="capability_check",
            outcome="skipped",
            reason_code="not_configured",
        ),
    )
    # A skipped check was never dispatched, and blocked/skipped must say why.
    assert rejected(
        db, attempt(case, run, revision, supplier, task, outcome="skipped", reason_code="deadline")
    )
    assert rejected(db, attempt(case, run, revision, supplier, task, outcome="blocked"))
    assert rejected(db, attempt(case, run, revision, supplier, task, reason_code="invented_reason"))
    now = datetime.now(UTC)
    assert rejected(
        db,
        attempt(
            case,
            run,
            revision,
            supplier,
            task,
            requested_at=now,
            finished_at=now - timedelta(seconds=5),
        ),
    )
    assert rejected(
        db,
        attempt(
            case,
            run,
            revision,
            supplier,
            task,
            kind="capability_check",
            request_dispatched=False,
            outcome="skipped",
            reason_code="not_configured",
            http_status=200,
        ),
    )
    assert not rejected(
        db,
        attempt(
            case,
            run,
            revision,
            supplier,
            task,
            kind="capability_check",
            request_dispatched=False,
            outcome="skipped",
            reason_code="not_configured",
        ),
    )


def test_cross_case_references_are_rejected(db: Session) -> None:
    _account, _case, revision, supplier, checklist, _claim, run, _task = build(db)
    _a2, other_case, other_revision = case_revision(db)
    # A run cannot bind a revision/checklist pair that belongs to a different case.
    now = datetime.now(UTC)
    assert rejected(
        db,
        VerificationRun(
            case_id=other_case.id,
            revision_id=revision.id,
            checklist_id=checklist.id,
            policy_version=POLICY_VERSION,
            country_pack_version="IN/core-v1",
            mode="live",
            requested_at=now,
            initial_deadline=now,
            budgets_json={},
            generation=1,
            idempotency_key=str(uuid4()),
        ),
    )
    # A claim cannot name a supplier from another case.
    assert rejected(
        db,
        Claim(
            case_id=other_case.id,
            revision_id=other_revision.id,
            checklist_id=checklist.id,
            supplier_id=supplier.id,
            type="manufacturer",
            assertion="x",
            relevant_period={},
            proof_criteria_json={"criteria": []},
        ),
    )
    # A task cannot attach a supplier from another case.
    assert rejected(
        db,
        CheckTask(
            case_id=other_case.id,
            run_id=run.id,
            supplier_id=supplier.id,
            claim_ids=[],
            source_id="s",
            check_type="t",
            dependency_ids=[],
            operation_key=str(uuid4()),
            due_at=now,
            deadline_at=now,
        ),
    )


def test_claim_parent_must_share_supplier_and_checklist(db: Session) -> None:
    _a, case, revision, supplier, checklist, claim, _run, _task = build(db)
    other_supplier = Supplier(
        case_id=case.id,
        display_name=licence_rows()[1].firm_name,
        original_identifiers=[],
        normalized_identifiers=[],
        source_refs=[],
    )
    db.add(other_supplier)
    db.flush()

    def child(**overrides: Any) -> Claim:
        values = {
            "case_id": case.id,
            "revision_id": revision.id,
            "checklist_id": checklist.id,
            "supplier_id": supplier.id,
            "parent_claim_id": claim.id,
            "type": "legal_existence",
            "assertion": "subclaim",
            "relevant_period": {},
            "proof_criteria_json": {"criteria": []},
        }
        values.update(overrides)
        return Claim(**values)

    assert not rejected(db, child())
    assert rejected(db, child(supplier_id=other_supplier.id))  # different supplier than parent
    assert rejected(db, child(type="not_a_family"))
    assert rejected(db, child(proof_criteria_json=[]))  # criteria must be an object


def test_one_active_run_and_draft_checklist_per_scope(db: Session) -> None:
    _a, case, revision, _s, checklist, _c, run, _t = build(db)
    now = datetime.now(UTC)
    second = VerificationRun(
        case_id=case.id,
        revision_id=revision.id,
        checklist_id=checklist.id,
        policy_version=POLICY_VERSION,
        country_pack_version="IN/core-v1",
        mode="live",
        requested_at=now,
        initial_deadline=now,
        budgets_json={},
        generation=1,
        idempotency_key=str(uuid4()),
    )
    assert rejected(db, second)  # another queued/running run in the same case
    run.state = "completed"
    run.started_at = now
    run.completed_at = now
    db.flush()
    assert not rejected(db, second)
    checklist_two = ChecklistVersion(
        case_id=case.id, revision_id=revision.id, sequence=2, policy_version=POLICY_VERSION
    )
    assert rejected(db, checklist_two)  # first checklist is still a draft
    # Queued runs cannot already have started; terminal runs need a completion time.
    assert rejected(
        db,
        VerificationRun(
            case_id=case.id,
            revision_id=revision.id,
            checklist_id=checklist.id,
            policy_version=POLICY_VERSION,
            country_pack_version="IN/core-v1",
            mode="live",
            state="queued",
            started_at=now,
            requested_at=now,
            initial_deadline=now,
            budgets_json={},
            generation=1,
            idempotency_key=str(uuid4()),
        ),
    )


def test_assessments_are_append_only_with_one_of_three_verdicts(db: Session) -> None:
    _a, case, revision, _s, checklist, claim, run, _t = build(db)

    def assessment(**overrides: Any) -> Assessment:
        values = {
            "case_id": case.id,
            "run_id": run.id,
            "revision_id": revision.id,
            "checklist_id": checklist.id,
            "claim_id": claim.id,
            "sequence": 1,
            "verdict": "unproven",
            "reasoning": "No retrieved evidence",
            "criterion_results": [],
            "evidence_refs": [],
            "attempt_refs": [],
            "gaps": ["no_evidence"],
            "policy_version": POLICY_VERSION,
        }
        values.update(overrides)
        return Assessment(**values)

    stored = assessment()
    assert not rejected(db, stored)
    assert rejected(db, assessment(verdict="probably"))
    assert rejected(db, assessment(sequence=1))  # sequence is unique per claim and run
    with pytest.raises(DBAPIError), db.begin_nested():
        db.execute(
            text("UPDATE assessments SET verdict = 'proven' WHERE id = :id"),
            {"id": stored.id},
        )
