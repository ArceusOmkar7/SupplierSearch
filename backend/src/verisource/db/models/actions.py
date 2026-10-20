"""Dependent buyer actions; never a manual portal, CAPTCHA or scraping task."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from verisource.db.base import Base, CreatedAt, UUIDPrimaryKey


class HumanAction(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "human_actions"
    __table_args__ = (
        UniqueConstraint("case_id", "id"),
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
        ForeignKeyConstraint(
            ["case_id", "requested_document_ref"],
            ["document_artifacts.case_id", "document_artifacts.id"],
            ondelete="CASCADE",
        ),
        CheckConstraint("type IN ('supply_unlocked_document','resolve_identity')", name="type"),
        CheckConstraint("state IN ('pending','resolved','cancelled')", name="state"),
        CheckConstraint(
            "(state = 'resolved') = (resolved_at IS NOT NULL AND resolution_ref IS NOT NULL)",
            name="resolution_pair",
        ),
    )

    case_id: Mapped[UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    revision_id: Mapped[UUID]
    run_id: Mapped[UUID]
    affected_task_ids: Mapped[list[UUID]] = mapped_column(ARRAY(PG_UUID(as_uuid=True)))
    type: Mapped[str]
    requested_document_ref: Mapped[UUID | None]
    state: Mapped[str] = mapped_column(default="pending")
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution_ref: Mapped[str | None]
