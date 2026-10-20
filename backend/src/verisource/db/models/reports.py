"""Report records: one per snapshot and renderer version, bound to immutable rendered bytes."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from verisource.db.base import Base, CreatedAt, UUIDPrimaryKey


class Report(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "reports"
    __table_args__ = (
        UniqueConstraint("case_id", "id"),
        UniqueConstraint("case_id", "snapshot_id", "renderer_version"),
        ForeignKeyConstraint(
            ["case_id", "snapshot_id"],
            ["assessment_snapshots.case_id", "assessment_snapshots.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["case_id", "revision_id"],
            ["requirement_revisions.case_id", "requirement_revisions.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["case_id", "artifact_id"],
            ["document_artifacts.case_id", "document_artifacts.id"],
            ondelete="CASCADE",
        ),
        CheckConstraint("state IN ('generating','ready','failed')", name="state"),
        # Ready reports carry all three bindings; others carry none (no placeholder values).
        CheckConstraint(
            "(state = 'ready' AND artifact_id IS NOT NULL AND content_hash IS NOT NULL "
            "AND generated_at IS NOT NULL) OR "
            "(state <> 'ready' AND artifact_id IS NULL AND content_hash IS NULL "
            "AND generated_at IS NULL)",
            name="ready_bindings",
        ),
        CheckConstraint("(state = 'failed') = (error IS NOT NULL)", name="error_only_on_failure"),
    )

    case_id: Mapped[UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    revision_id: Mapped[UUID]
    snapshot_id: Mapped[UUID]
    renderer_version: Mapped[str]
    state: Mapped[str] = mapped_column(default="generating")
    artifact_id: Mapped[UUID | None]
    content_hash: Mapped[str | None]
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None]
