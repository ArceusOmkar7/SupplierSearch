"""Operator-level genuine source corpus; known-supplier lookup only, never a discovery index."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from verisource.db.base import Base, UUIDPrimaryKey


class SourceDataset(UUIDPrimaryKey, Base):
    __tablename__ = "source_datasets"
    __table_args__ = (
        UniqueConstraint("sha256", "schema_version"),
        CheckConstraint("state IN ('imported','quarantined','failed')", name="state"),
        CheckConstraint("format IN ('csv','xlsx','pdf','html')", name="format"),
    )

    source_version: Mapped[str]
    publisher: Mapped[str]
    original_url: Mapped[str]
    licence_attribution: Mapped[str]
    obtained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    publication_cutoff: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cutoff_unknown_reason: Mapped[str | None]
    coverage: Mapped[list[Any]] = mapped_column(JSONB)
    local_storage_key: Mapped[str]
    sha256: Mapped[str]
    format: Mapped[str]
    schema_version: Mapped[str]
    state: Mapped[str]
    imported_count: Mapped[int] = mapped_column(default=0)
    quarantined_count: Mapped[int] = mapped_column(default=0)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SourceDatasetRecord(UUIDPrimaryKey, Base):
    __tablename__ = "source_dataset_records"
    __table_args__ = (
        UniqueConstraint("dataset_id", "locator"),
        Index(
            "ix_source_dataset_records_identifiers",
            "normalized_identifiers",
            postgresql_using="gin",
        ),
    )

    dataset_id: Mapped[UUID] = mapped_column(
        ForeignKey("source_datasets.id", ondelete="CASCADE"), index=True
    )
    locator: Mapped[str]
    normalized_identifiers: Mapped[dict[str, Any]] = mapped_column(JSONB)
    selected_business_fields: Mapped[dict[str, Any]] = mapped_column(JSONB)
    origin_hash: Mapped[str]


class QcoRecord(UUIDPrimaryKey, Base):
    __tablename__ = "qco_records"
    __table_args__ = (
        CheckConstraint("coverage_state IN ('complete','partial','stale')", name="coverage"),
    )

    source_document_id: Mapped[UUID] = mapped_column(
        ForeignKey("source_datasets.id", ondelete="CASCADE"), index=True
    )
    order_number: Mapped[str]
    standard_codes: Mapped[list[Any]] = mapped_column(JSONB)
    product_scope: Mapped[str]
    exclusions: Mapped[list[Any]] = mapped_column(JSONB)
    issued_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    effective_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    amended_on: Mapped[list[Any]] = mapped_column(JSONB)
    supersedes_ref: Mapped[str | None]
    coverage_state: Mapped[str]
    extracted_basis: Mapped[str]
