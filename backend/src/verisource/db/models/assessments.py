"""Immutable assessment snapshots and explicit buyer decisions."""

from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from verisource.db.base import Base, CreatedAt, UUIDPrimaryKey


class AssessmentSnapshot(UUIDPrimaryKey, CreatedAt, Base):
    """A materialized table and lists; a trigger rejects UPDATE so history cannot change."""

    __tablename__ = "assessment_snapshots"
    __table_args__ = (
        UniqueConstraint("case_id", "id"),
        UniqueConstraint("case_id", "run_id", "content_hash"),
        ForeignKeyConstraint(
            ["case_id", "run_id", "revision_id"],
            ["verification_runs.case_id", "verification_runs.id", "verification_runs.revision_id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["case_id", "checklist_id", "revision_id"],
            [
                "checklist_versions.case_id",
                "checklist_versions.id",
                "checklist_versions.revision_id",
            ],
            ondelete="CASCADE",
        ),
        CheckConstraint("trigger IN ('initial','deadline','updated','completed')", name="trigger"),
        CheckConstraint("event_cutoff >= 0", name="cutoff"),
        CheckConstraint("sequence > 0", name="positive_sequence"),
        UniqueConstraint("case_id", "run_id", "sequence"),
        Index("ix_snapshots_case_created", "case_id", "created_at"),
    )

    case_id: Mapped[UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    run_id: Mapped[UUID]
    revision_id: Mapped[UUID]
    checklist_id: Mapped[UUID]
    sequence: Mapped[int]
    trigger: Mapped[str]
    event_cutoff: Mapped[int]
    assessment_ids: Mapped[list[Any]] = mapped_column(JSONB)
    supplier_processing_states: Mapped[dict[str, Any]] = mapped_column(JSONB)
    pending_action_refs: Mapped[list[Any]] = mapped_column(JSONB)
    coverage_summary: Mapped[dict[str, Any]] = mapped_column(JSONB)
    qualified_ids: Mapped[list[Any]] = mapped_column(JSONB)
    follow_up_ids: Mapped[list[Any]] = mapped_column(JSONB)
    excluded_reasons: Mapped[dict[str, Any]] = mapped_column(JSONB)
    content_json: Mapped[dict[str, Any]] = mapped_column(JSONB)
    content_hash: Mapped[str]


class SupplierDecision(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "supplier_decisions"
    __table_args__ = (
        UniqueConstraint("case_id", "id"),
        ForeignKeyConstraint(
            ["case_id", "snapshot_id"],
            ["assessment_snapshots.case_id", "assessment_snapshots.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["case_id", "supplier_id"], ["suppliers.case_id", "suppliers.id"], ondelete="CASCADE"
        ),
        CheckConstraint("decision IN ('select','reject','no_selection')", name="decision"),
        CheckConstraint(
            "(decision = 'no_selection') = (supplier_id IS NULL)", name="supplier_matches_decision"
        ),
    )

    case_id: Mapped[UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    snapshot_id: Mapped[UUID]
    supplier_id: Mapped[UUID | None]
    decision: Mapped[str]
    buyer_id: Mapped[UUID] = mapped_column(ForeignKey("buyer_accounts.id"))
    reason: Mapped[str | None]
    operation_key: Mapped[str]
