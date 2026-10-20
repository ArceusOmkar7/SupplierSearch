"""Persist work intents, event ordering and references to library-managed graph checkpoints."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from verisource.db.base import Base, CreatedAt, UUIDPrimaryKey


class WorkItem(UUIDPrimaryKey, Base):
    __tablename__ = "work_items"
    __table_args__ = (
        UniqueConstraint("case_id", "id"),
        UniqueConstraint("case_id", "operation_key"),
        CheckConstraint(
            "state IN ('queued','leased','retry_wait','succeeded','failed','cancelled')",
            name="state",
        ),
        ForeignKeyConstraint(
            ["case_id", "run_id"],
            ["verification_runs.case_id", "verification_runs.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["case_id", "task_id"], ["check_tasks.case_id", "check_tasks.id"], ondelete="CASCADE"
        ),
        CheckConstraint("fence > 0 AND attempts >= 0", name="lease_counts"),
        CheckConstraint(
            "state <> 'leased' OR (lease_owner IS NOT NULL AND lease_expires_at IS NOT NULL AND heartbeat_at IS NOT NULL)",
            name="leased_fields",
        ),
    )

    case_id: Mapped[UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    run_id: Mapped[UUID | None]
    task_id: Mapped[UUID | None]
    kind: Mapped[str]
    state: Mapped[str] = mapped_column(default="queued")
    operation_key: Mapped[str]
    lease_owner: Mapped[str | None]
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fence: Mapped[int]
    attempts: Mapped[int] = mapped_column(default=0)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    payload_refs: Mapped[dict[str, Any]] = mapped_column(JSONB)


class CaseEvent(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "case_events"
    __table_args__ = (
        UniqueConstraint("case_id", "sequence"),
        UniqueConstraint("case_id", "operation_key"),
        ForeignKeyConstraint(
            ["case_id", "revision_id"],
            ["requirement_revisions.case_id", "requirement_revisions.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["case_id", "run_id"],
            ["verification_runs.case_id", "verification_runs.id"],
            ondelete="CASCADE",
        ),
        CheckConstraint("sequence > 0", name="positive_sequence"),
    )

    case_id: Mapped[UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    sequence: Mapped[int]
    type: Mapped[str]
    revision_id: Mapped[UUID | None]
    run_id: Mapped[UUID | None]
    object_refs: Mapped[dict[str, Any]] = mapped_column(JSONB)
    public_payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    operation_key: Mapped[str]


class GraphCheckpointReference(CreatedAt, Base):
    __tablename__ = "graph_checkpoint_refs"
    __table_args__ = (
        UniqueConstraint("case_id", "thread_id", "checkpoint_namespace", "checkpoint_id"),
        ForeignKeyConstraint(
            ["case_id", "run_id"],
            ["verification_runs.case_id", "verification_runs.id"],
            ondelete="CASCADE",
        ),
    )

    thread_id: Mapped[str] = mapped_column(primary_key=True)
    checkpoint_namespace: Mapped[str] = mapped_column(primary_key=True)
    checkpoint_id: Mapped[str] = mapped_column(primary_key=True)
    case_id: Mapped[UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    run_id: Mapped[UUID]
    state_refs: Mapped[dict[str, Any]] = mapped_column(JSONB)
