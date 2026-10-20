"""Actual attempts, private file artifacts and extractions; attempts are never evidence."""

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
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from verisource.db.base import Base, CreatedAt, UUIDPrimaryKey

ATTEMPT_OUTCOMES = (
    "success",
    "no_record",
    "blocked",
    "unavailable",
    "timeout",
    "transient_error",
    "invalid_input",
    "uncertain_outcome",
    "skipped",
)
REASON_CODES = (
    "not_configured",
    "permission_unverified",
    "consent_missing",
    "budget_exhausted",
    "quota_exhausted",
    "not_supported",
    "missing_identifier",
    "captcha",
    "locked_document",
    "unsupported_language",
    "too_large",
    "malformed_document",
    "deadline",
    "robots_disallowed",
    "ocr_unavailable",
)


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN (" + ",".join(f"'{value}'" for value in values) + ")"


class CheckAttempt(UUIDPrimaryKey, Base):
    __tablename__ = "check_attempts"
    __table_args__ = (
        UniqueConstraint("case_id", "id"),
        UniqueConstraint("case_id", "operation_key"),
        ForeignKeyConstraint(
            ["case_id", "run_id"],
            ["verification_runs.case_id", "verification_runs.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["case_id", "task_id"], ["check_tasks.case_id", "check_tasks.id"], ondelete="CASCADE"
        ),
        ForeignKeyConstraint(
            ["case_id", "revision_id"],
            ["requirement_revisions.case_id", "requirement_revisions.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["case_id", "supplier_id"], ["suppliers.case_id", "suppliers.id"], ondelete="CASCADE"
        ),
        ForeignKeyConstraint(
            ["case_id", "retry_of"],
            ["check_attempts.case_id", "check_attempts.id"],
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "kind IN ('capability_check','remote_request','document_read','deadline_check')",
            name="kind",
        ),
        CheckConstraint(_in("outcome", ATTEMPT_OUTCOMES), name="outcome"),
        CheckConstraint(
            "reason_code IS NULL OR " + _in("reason_code", REASON_CODES), name="reason"
        ),
        CheckConstraint("finished_at >= requested_at", name="ordered_times"),
        # A local skip or capability/deadline/document decision cannot claim a dispatch.
        CheckConstraint("kind = 'remote_request' OR NOT request_dispatched", name="local_kind"),
        CheckConstraint("outcome <> 'skipped' OR NOT request_dispatched", name="skip_not_sent"),
        CheckConstraint(
            "outcome NOT IN ('blocked','skipped','invalid_input') OR reason_code IS NOT NULL",
            name="reason_required",
        ),
        CheckConstraint("http_status IS NULL OR request_dispatched", name="status_needs_dispatch"),
        CheckConstraint(
            "outcome = 'success' OR jsonb_array_length(artifact_refs) = 0 OR outcome IN "
            "('uncertain_outcome','no_record')",
            name="no_content_no_artifacts",
        ),
    )

    case_id: Mapped[UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    run_id: Mapped[UUID] = mapped_column(index=True)
    task_id: Mapped[UUID]
    revision_id: Mapped[UUID]
    supplier_id: Mapped[UUID]
    claim_ids: Mapped[list[UUID]] = mapped_column(ARRAY(PG_UUID(as_uuid=True)))
    source_version: Mapped[str]
    kind: Mapped[str]
    target: Mapped[str]
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    request_dispatched: Mapped[bool]
    outcome: Mapped[str]
    reason_code: Mapped[str | None]
    http_status: Mapped[int | None]
    provider_request_id: Mapped[str | None]
    artifact_refs: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    retry_of: Mapped[UUID | None]
    operation_key: Mapped[str]


class DocumentArtifact(UUIDPrimaryKey, Base):
    __tablename__ = "document_artifacts"
    __table_args__ = (
        UniqueConstraint("case_id", "id"),
        UniqueConstraint("storage_key"),
        ForeignKeyConstraint(
            ["case_id", "revision_id"],
            ["requirement_revisions.case_id", "requirement_revisions.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["case_id", "supplier_id"], ["suppliers.case_id", "suppliers.id"], ondelete="CASCADE"
        ),
        ForeignKeyConstraint(
            ["case_id", "source_attempt_id"],
            ["check_attempts.case_id", "check_attempts.id"],
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "origin IN ('buyer_upload','source_fetch','source_import','generated_report')",
            name="origin",
        ),
        CheckConstraint(
            "state IN ('queued','extracted','quarantined','failed','ready')", name="state"
        ),
        CheckConstraint("byte_count >= 0 AND (page_count IS NULL OR page_count > 0)", name="sizes"),
    )

    case_id: Mapped[UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    revision_id: Mapped[UUID | None]
    supplier_id: Mapped[UUID | None]
    origin: Mapped[str]
    storage_key: Mapped[str]
    sha256: Mapped[str]
    media_type: Mapped[str]
    byte_count: Mapped[int]
    page_count: Mapped[int | None]
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_url: Mapped[str | None]
    source_attempt_id: Mapped[UUID | None]
    state: Mapped[str]
    state_reason: Mapped[str | None]


class Extraction(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "extractions"
    __table_args__ = (
        UniqueConstraint("case_id", "id"),
        ForeignKeyConstraint(
            ["case_id", "artifact_id"],
            ["document_artifacts.case_id", "document_artifacts.id"],
            ondelete="CASCADE",
        ),
        CheckConstraint("method IN ('text','ocr','model','rule')", name="method"),
    )

    case_id: Mapped[UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    artifact_id: Mapped[UUID]
    page_refs: Mapped[list[Any]] = mapped_column(JSONB)
    method: Mapped[str]
    fields: Mapped[dict[str, Any]] = mapped_column(JSONB)
    missing_fields: Mapped[list[Any]] = mapped_column(JSONB)
    uncertainties: Mapped[list[Any]] = mapped_column(JSONB)
    model_id: Mapped[str | None]
    schema_version: Mapped[str]
    content_hash: Mapped[str]
