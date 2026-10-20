"""Checklist, claim, run and check-task mappings; every row carries its case."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from verisource.db.base import Base, CreatedAt, UUIDPrimaryKey

CLAIM_TYPES = (
    "legal_existence",
    "manufacturer",
    "part_capability",
    "certificate",
    "regulatory",
    "capacity",
)


class ChecklistVersion(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "checklist_versions"
    __table_args__ = (
        UniqueConstraint("case_id", "id"),
        UniqueConstraint("case_id", "id", "revision_id"),
        UniqueConstraint("case_id", "revision_id", "sequence"),
        ForeignKeyConstraint(
            ["case_id", "revision_id"],
            ["requirement_revisions.case_id", "requirement_revisions.id"],
            ondelete="CASCADE",
        ),
        CheckConstraint("sequence > 0", name="positive_sequence"),
        CheckConstraint("status IN ('draft','confirmed')", name="status"),
        CheckConstraint(
            "(status = 'confirmed' AND confirmed_at IS NOT NULL AND confirmed_by IS NOT NULL) OR "
            "(status = 'draft' AND confirmed_at IS NULL AND confirmed_by IS NULL)",
            name="confirmation_pair",
        ),
        Index(
            "uq_checklist_active_draft",
            "case_id",
            "revision_id",
            unique=True,
            postgresql_where=text("status = 'draft'"),
        ),
    )

    case_id: Mapped[UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    revision_id: Mapped[UUID]
    sequence: Mapped[int]
    status: Mapped[str] = mapped_column(default="draft")
    confirmed_by: Mapped[UUID | None] = mapped_column(ForeignKey("buyer_accounts.id"))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    policy_version: Mapped[str]


class Claim(UUIDPrimaryKey, Base):
    __tablename__ = "claims"
    __table_args__ = (
        UniqueConstraint("case_id", "id"),
        UniqueConstraint("case_id", "checklist_id", "supplier_id", "id"),
        ForeignKeyConstraint(
            ["case_id", "checklist_id", "revision_id"],
            [
                "checklist_versions.case_id",
                "checklist_versions.id",
                "checklist_versions.revision_id",
            ],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["case_id", "supplier_id"], ["suppliers.case_id", "suppliers.id"], ondelete="CASCADE"
        ),
        ForeignKeyConstraint(
            ["case_id", "site_id"], ["supplier_sites.case_id", "supplier_sites.id"]
        ),
        # Parent and children share case, checklist and supplier (and so revision).
        ForeignKeyConstraint(
            ["case_id", "checklist_id", "supplier_id", "parent_claim_id"],
            ["claims.case_id", "claims.checklist_id", "claims.supplier_id", "claims.id"],
            ondelete="CASCADE",
        ),
        CheckConstraint("parent_claim_id IS NULL OR parent_claim_id <> id", name="no_self_parent"),
        CheckConstraint(
            "type IN ('legal_existence','manufacturer','part_capability','certificate',"
            "'regulatory','capacity')",
            name="type",
        ),
        CheckConstraint(
            "processing_state IN ('proposed','confirmed','queued','checking','evaluated')",
            name="processing_state",
        ),
        CheckConstraint("jsonb_typeof(proof_criteria_json) = 'object'", name="criteria_object"),
    )

    case_id: Mapped[UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    revision_id: Mapped[UUID]
    checklist_id: Mapped[UUID]
    supplier_id: Mapped[UUID]
    site_id: Mapped[UUID | None]
    parent_claim_id: Mapped[UUID | None]
    type: Mapped[str]
    assertion: Mapped[str]
    relevant_period: Mapped[dict[str, Any]] = mapped_column(JSONB)
    required_for_shortlist: Mapped[bool] = mapped_column(default=False)
    proof_criteria_json: Mapped[dict[str, Any]] = mapped_column(JSONB)
    processing_state: Mapped[str] = mapped_column(default="proposed")
    waiting_input: Mapped[bool] = mapped_column(default=False)


class VerificationRun(UUIDPrimaryKey, Base):
    __tablename__ = "verification_runs"
    __table_args__ = (
        UniqueConstraint("case_id", "id"),
        UniqueConstraint("case_id", "id", "revision_id"),
        UniqueConstraint("case_id", "idempotency_key"),
        ForeignKeyConstraint(
            ["case_id", "checklist_id", "revision_id"],
            [
                "checklist_versions.case_id",
                "checklist_versions.id",
                "checklist_versions.revision_id",
            ],
        ),
        CheckConstraint("mode IN ('live','replay')", name="mode"),
        CheckConstraint(
            "state IN ('queued','running','completed','completed_with_gaps','cancelled','failed')",
            name="state",
        ),
        CheckConstraint("generation > 0", name="positive_generation"),
        CheckConstraint("state <> 'queued' OR started_at IS NULL", name="queued_not_started"),
        CheckConstraint(
            "(state IN ('completed','completed_with_gaps','cancelled','failed')) "
            "= (completed_at IS NOT NULL)",
            name="terminal_completion",
        ),
        Index(
            "uq_run_one_active_per_revision",
            "case_id",
            "revision_id",
            unique=True,
            postgresql_where=text("state IN ('queued','running')"),
        ),
    )

    case_id: Mapped[UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    revision_id: Mapped[UUID]
    checklist_id: Mapped[UUID]
    policy_version: Mapped[str]
    country_pack_version: Mapped[str]
    mode: Mapped[str]
    state: Mapped[str] = mapped_column(default="queued")
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    initial_deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    budgets_json: Mapped[dict[str, Any]] = mapped_column(JSONB)
    generation: Mapped[int]
    idempotency_key: Mapped[str]


class CheckTask(UUIDPrimaryKey, Base):
    __tablename__ = "check_tasks"
    __table_args__ = (
        UniqueConstraint("case_id", "id"),
        UniqueConstraint("case_id", "operation_key"),
        ForeignKeyConstraint(
            ["case_id", "run_id"],
            ["verification_runs.case_id", "verification_runs.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["case_id", "supplier_id"], ["suppliers.case_id", "suppliers.id"], ondelete="CASCADE"
        ),
        ForeignKeyConstraint(
            ["case_id", "wait_action_id"],
            ["human_actions.case_id", "human_actions.id"],
            use_alter=True,
            name="fk_check_tasks_wait_action",
        ),
        CheckConstraint(
            "state IN ('queued','running','succeeded','no_evidence','failed','waiting_input',"
            "'cancelled')",
            name="state",
        ),
        CheckConstraint("NOT (id = ANY(dependency_ids))", name="no_self_dependency"),
    )

    case_id: Mapped[UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    run_id: Mapped[UUID] = mapped_column(index=True)
    supplier_id: Mapped[UUID]
    claim_ids: Mapped[list[UUID]] = mapped_column(ARRAY(PG_UUID(as_uuid=True)))
    source_id: Mapped[str]
    check_type: Mapped[str]
    dependency_ids: Mapped[list[UUID]] = mapped_column(ARRAY(PG_UUID(as_uuid=True)))
    state: Mapped[str] = mapped_column(default="queued")
    operation_key: Mapped[str]
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    wait_action_id: Mapped[UUID | None]
