"""Retrieved observations, their use and append-only assessments; same-case keys only."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from verisource.db.base import Base, CreatedAt, UUIDPrimaryKey


class EvidenceRecord(UUIDPrimaryKey, Base):
    __tablename__ = "evidence_records"
    __table_args__ = (
        UniqueConstraint("case_id", "id"),
        ForeignKeyConstraint(
            ["case_id", "run_id"],
            ["verification_runs.case_id", "verification_runs.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["case_id", "supplier_id"], ["suppliers.case_id", "suppliers.id"], ondelete="CASCADE"
        ),
        ForeignKeyConstraint(
            ["case_id", "site_id"], ["supplier_sites.case_id", "supplier_sites.id"]
        ),
        ForeignKeyConstraint(
            ["case_id", "identity_resolution_id"],
            ["identity_resolutions.case_id", "identity_resolutions.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["case_id", "artifact_id"],
            ["document_artifacts.case_id", "document_artifacts.id"],
            ondelete="CASCADE",
        ),
        CheckConstraint("observation <> ''", name="has_observation"),
        CheckConstraint(
            "authority_role IN ('official_registry','official_publication','issuer',"
            "'accreditation_body','supplier','third_party','buyer')",
            name="authority_role",
        ),
    )

    case_id: Mapped[UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    run_id: Mapped[UUID]
    supplier_id: Mapped[UUID]
    site_id: Mapped[UUID | None]
    assertion_tags: Mapped[list[Any]] = mapped_column(JSONB)
    source_version: Mapped[str]
    source_ref: Mapped[str]
    observation: Mapped[str]
    locator: Mapped[str]
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    origin_lineage: Mapped[str]
    self_reported: Mapped[bool]
    authority_role: Mapped[str]
    identity_resolution_id: Mapped[UUID]
    artifact_id: Mapped[UUID | None]
    content_hash: Mapped[str]
    replay: Mapped[bool] = mapped_column(default=False)


class Assessment(UUIDPrimaryKey, CreatedAt, Base):
    """Append-only: a migration trigger rejects UPDATE; history stays inspectable."""

    __tablename__ = "assessments"
    __table_args__ = (
        UniqueConstraint("case_id", "id"),
        UniqueConstraint("case_id", "claim_id", "run_id", "sequence"),
        ForeignKeyConstraint(
            ["case_id", "run_id", "revision_id"],
            [
                "verification_runs.case_id",
                "verification_runs.id",
                "verification_runs.revision_id",
            ],
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
        ForeignKeyConstraint(
            ["case_id", "claim_id"], ["claims.case_id", "claims.id"], ondelete="CASCADE"
        ),
        CheckConstraint("verdict IN ('proven','unproven','contradicted')", name="verdict"),
        CheckConstraint("sequence > 0", name="positive_sequence"),
    )

    case_id: Mapped[UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    run_id: Mapped[UUID]
    revision_id: Mapped[UUID]
    checklist_id: Mapped[UUID]
    claim_id: Mapped[UUID]
    sequence: Mapped[int]
    verdict: Mapped[str]
    reasoning: Mapped[str]
    criterion_results: Mapped[list[Any]] = mapped_column(JSONB)
    evidence_refs: Mapped[list[Any]] = mapped_column(JSONB)
    attempt_refs: Mapped[list[Any]] = mapped_column(JSONB)
    gaps: Mapped[list[Any]] = mapped_column(JSONB)
    policy_version: Mapped[str]


class EvidenceUse(UUIDPrimaryKey, Base):
    __tablename__ = "evidence_uses"
    __table_args__ = (
        UniqueConstraint("case_id", "assessment_id", "evidence_id", "criterion_id"),
        ForeignKeyConstraint(
            ["case_id", "assessment_id"],
            ["assessments.case_id", "assessments.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["case_id", "evidence_id"],
            ["evidence_records.case_id", "evidence_records.id"],
            ondelete="CASCADE",
        ),
        CheckConstraint("role IN ('supporting','refuting','context')", name="role"),
    )

    case_id: Mapped[UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    assessment_id: Mapped[UUID]
    evidence_id: Mapped[UUID]
    criterion_id: Mapped[str]
    role: Mapped[str]
    period_fit: Mapped[str]
    freshness_check_ref: Mapped[str | None]
