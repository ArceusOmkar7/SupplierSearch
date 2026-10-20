"""Global source configuration and optional free-project quota; no premium prerequisite."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    PrimaryKeyConstraint,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from verisource.db.base import Base, CreatedAt, UUIDPrimaryKey


class SourceDefinition(CreatedAt, Base):
    """Immutable (id, version) configuration; contains no secret values."""

    __tablename__ = "source_definitions"
    __table_args__ = (
        PrimaryKeyConstraint("id", "version"),
        CheckConstraint(
            "access_mode IN ('public_page','official_document','local_export','issuer_page','buyer_document',"
            "'free_api')",
            name="access_mode",
        ),
    )

    id: Mapped[str]
    version: Mapped[int]
    provider_family: Mapped[str]
    jurisdiction: Mapped[str]
    claim_coverage: Mapped[list[Any]] = mapped_column(JSONB)
    allowed_hosts: Mapped[list[Any]] = mapped_column(JSONB)
    access_mode: Mapped[str]
    authority_roles: Mapped[list[Any]] = mapped_column(JSONB)
    policy_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    policy_refs: Mapped[list[Any]] = mapped_column(JSONB)
    terms_version: Mapped[str | None]
    capabilities: Mapped[dict[str, Any]] = mapped_column(JSONB)


class ProviderAccount(UUIDPrimaryKey, Base):
    __tablename__ = "provider_accounts"
    __table_args__ = (
        CheckConstraint("mode = 'free'", name="free_only"),  # Paid mode stays disabled.
    )

    provider: Mapped[str]
    secret_ref: Mapped[str | None]
    mode: Mapped[str] = mapped_column(default="free")
    enabled_capabilities: Mapped[list[Any]] = mapped_column(JSONB)
    policy_refs: Mapped[list[Any]] = mapped_column(JSONB)
    allowed_data_classes: Mapped[list[Any]] = mapped_column(JSONB)
    quota_window: Mapped[str | None]
    limits: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SourceAuthorization(UUIDPrimaryKey, Base):
    __tablename__ = "source_authorizations"
    __table_args__ = (
        UniqueConstraint("case_id", "id"),
        ForeignKeyConstraint(
            ["case_id", "supplier_id"], ["suppliers.case_id", "suppliers.id"], ondelete="CASCADE"
        ),
    )

    case_id: Mapped[UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    supplier_id: Mapped[UUID]
    provider_account_id: Mapped[UUID] = mapped_column(ForeignKey("provider_accounts.id"))
    basis: Mapped[str]
    authorization_evidence_ref: Mapped[str]
    scope: Mapped[str]
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_by: Mapped[UUID] = mapped_column(ForeignKey("buyer_accounts.id"))


class BudgetReservation(UUIDPrimaryKey, Base):
    __tablename__ = "budget_reservations"
    __table_args__ = (
        UniqueConstraint("case_id", "operation_key"),
        ForeignKeyConstraint(
            ["case_id", "run_id"],
            ["verification_runs.case_id", "verification_runs.id"],
            ondelete="CASCADE",
        ),
        CheckConstraint("state IN ('reserved','settled','released','expired')", name="state"),
        CheckConstraint(
            "reserved_amount >= 0 AND (settled_amount IS NULL OR settled_amount >= 0)",
            name="non_negative",
        ),
    )

    provider_account_id: Mapped[UUID | None] = mapped_column(ForeignKey("provider_accounts.id"))
    run_id: Mapped[UUID]
    case_id: Mapped[UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    consumer: Mapped[str]
    unit: Mapped[str]
    reserved_amount: Mapped[int]
    settled_amount: Mapped[int | None]
    cycle: Mapped[str | None]
    state: Mapped[str] = mapped_column(default="reserved")
    operation_key: Mapped[str]
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
