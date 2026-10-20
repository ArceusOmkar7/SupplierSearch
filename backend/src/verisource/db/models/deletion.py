"""Metadata-only deletion tracking and app-managed local snapshot records.

Neither table holds case content: only the random case UUID, the requesting owner and timing.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from verisource.db.base import Base, CreatedAt, UUIDPrimaryKey


class DeletionRequest(UUIDPrimaryKey, Base):
    __tablename__ = "deletion_requests"
    __table_args__ = (
        CheckConstraint("state IN ('accepted','purging','completed')", name="state"),
        CheckConstraint(
            "(state = 'completed') = (active_purge_completed_at IS NOT NULL "
            "AND managed_snapshots_purged_at IS NOT NULL)",
            name="completion_requires_both_purges",
        ),
        CheckConstraint(
            "managed_snapshots_purged_at IS NULL OR active_purge_completed_at IS NOT NULL",
            name="snapshots_after_active",
        ),
    )

    case_uuid: Mapped[UUID] = mapped_column(index=True)  # No FK: the case row is purged.
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("buyer_accounts.id"), index=True)
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    state: Mapped[str] = mapped_column(default="accepted")
    active_purge_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    managed_snapshots_purged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_category: Mapped[str | None]
    last_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    write_generation: Mapped[int]


class LocalSnapshot(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "local_snapshots"
    __table_args__ = (
        CheckConstraint("state IN ('valid','purged')", name="state"),
        CheckConstraint("deletion_sequence >= 0", name="sequence"),
    )

    manifest_path: Mapped[str]
    case_uuid_set: Mapped[list[Any]] = mapped_column(JSONB)
    file_hash_manifest: Mapped[dict[str, Any]] = mapped_column(JSONB)
    deletion_sequence: Mapped[int]
    state: Mapped[str] = mapped_column(default="valid")
