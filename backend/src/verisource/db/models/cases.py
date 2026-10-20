"""Private case aggregates and immutable revisions; composite keys prevent cross-case links."""

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
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from verisource.db.base import Base, CreatedAt, UUIDPrimaryKey


class Case(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "cases"
    __table_args__ = (
        CheckConstraint(
            "state IN ('draft','ready','active','assessed','closed','deleting')", name="state"
        ),
        CheckConstraint("version > 0 AND write_generation > 0", name="positive_versions"),
        CheckConstraint("(state = 'closed') = (closed_at IS NOT NULL)", name="closed_time"),
        CheckConstraint("(state = 'deleting') = (deleting_at IS NOT NULL)", name="deleting_time"),
        ForeignKeyConstraint(
            ["id", "latest_snapshot_id"],
            ["assessment_snapshots.case_id", "assessment_snapshots.id"],
            use_alter=True,
            name="fk_cases_latest_snapshot",
        ),
        ForeignKeyConstraint(
            ["id", "active_revision_id"],
            ["requirement_revisions.case_id", "requirement_revisions.id"],
            use_alter=True,
            name="fk_cases_active_revision",
        ),
    )

    owner_id: Mapped[UUID] = mapped_column(ForeignKey("buyer_accounts.id"), index=True)
    title: Mapped[str]
    state: Mapped[str] = mapped_column(default="draft")
    active_revision_id: Mapped[UUID | None]
    latest_snapshot_id: Mapped[UUID | None]
    version: Mapped[int] = mapped_column(default=1)
    write_generation: Mapped[int] = mapped_column(default=1)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleting_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RequirementRevision(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "requirement_revisions"
    __table_args__ = (
        UniqueConstraint("case_id", "id"),
        UniqueConstraint("case_id", "sequence"),
        CheckConstraint("sequence > 0", name="positive_sequence"),
        CheckConstraint("status IN ('draft','confirmed','abandoned')", name="status"),
        CheckConstraint(
            "(status = 'confirmed' AND confirmed_at IS NOT NULL AND confirmed_by IS NOT NULL) OR "
            "(status <> 'confirmed' AND confirmed_at IS NULL AND confirmed_by IS NULL)",
            name="confirmation_pair",
        ),
        Index(
            "uq_revision_active_draft",
            "case_id",
            unique=True,
            postgresql_where=text("status = 'draft'"),
        ),
    )

    case_id: Mapped[UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    sequence: Mapped[int]
    status: Mapped[str] = mapped_column(default="draft")
    requirements_json: Mapped[dict[str, Any]] = mapped_column(JSONB)
    location_json: Mapped[dict[str, Any]] = mapped_column(JSONB)
    supplier_set_json: Mapped[list[Any]] = mapped_column(JSONB)
    input_provenance: Mapped[dict[str, Any]] = mapped_column(JSONB)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmed_by: Mapped[UUID | None] = mapped_column(ForeignKey("buyer_accounts.id"))


class Supplier(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "suppliers"
    __table_args__ = (UniqueConstraint("case_id", "id"),)

    case_id: Mapped[UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    display_name: Mapped[str]
    original_identifiers: Mapped[list[Any]] = mapped_column(JSONB)
    normalized_identifiers: Mapped[list[Any]] = mapped_column(JSONB)
    source_refs: Mapped[list[Any]] = mapped_column(JSONB)


class SupplierSite(UUIDPrimaryKey, Base):
    __tablename__ = "supplier_sites"
    __table_args__ = (
        UniqueConstraint("case_id", "id"),
        ForeignKeyConstraint(
            ["case_id", "supplier_id"], ["suppliers.case_id", "suppliers.id"], ondelete="CASCADE"
        ),
        CheckConstraint(
            "role IN ('registered_office','production_site','other','unknown')", name="role"
        ),
    )

    case_id: Mapped[UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    supplier_id: Mapped[UUID]
    raw_address: Mapped[str]
    normalized_address: Mapped[dict[str, Any]] = mapped_column(JSONB)
    role: Mapped[str]
    jurisdiction: Mapped[str]
    identity_state: Mapped[str]
    evidence_refs: Mapped[list[Any]] = mapped_column(JSONB)


class IdentityResolution(UUIDPrimaryKey, Base):
    __tablename__ = "identity_resolutions"
    __table_args__ = (
        UniqueConstraint("case_id", "id"),
        ForeignKeyConstraint(
            ["case_id", "supplier_id"], ["suppliers.case_id", "suppliers.id"], ondelete="CASCADE"
        ),
        ForeignKeyConstraint(
            ["case_id", "revision_id"],
            ["requirement_revisions.case_id", "requirement_revisions.id"],
            ondelete="CASCADE",
        ),
        CheckConstraint("state IN ('proposed','confirmed','ambiguous','rejected')", name="state"),
        CheckConstraint(
            "state <> 'confirmed' OR (resolved_at IS NOT NULL AND resolution_basis <> '')",
            name="confirmed_basis",
        ),
    )

    case_id: Mapped[UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    revision_id: Mapped[UUID]
    supplier_id: Mapped[UUID]
    candidate_record_ref: Mapped[str]
    identifier_matches: Mapped[list[Any]] = mapped_column(JSONB)
    discrepancies: Mapped[list[Any]] = mapped_column(JSONB)
    proposed_score: Mapped[float | None]
    state: Mapped[str]
    resolution_basis: Mapped[str]
    resolved_by: Mapped[UUID | None] = mapped_column(ForeignKey("buyer_accounts.id"))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CaseCreationReceipt(CreatedAt, Base):
    """Idempotent POST /cases outcome; holds no case content and no FK so deletion cannot
    resurrect a purged case on a retry."""

    __tablename__ = "case_creation_receipts"

    buyer_id: Mapped[UUID] = mapped_column(ForeignKey("buyer_accounts.id"), primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(primary_key=True)
    body_hash: Mapped[str]
    case_id: Mapped[UUID]
