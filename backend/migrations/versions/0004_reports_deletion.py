"""reports deletion

Revision ID: 0004_reports_deletion
Revises: 0003_assessments
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004_reports_deletion"
down_revision = "0003_assessments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # An earlier revision's run may finish late while the newer revision's run starts.
    op.drop_index("uq_run_one_active_per_case", table_name="verification_runs")
    op.create_index(
        "uq_run_one_active_per_revision",
        "verification_runs",
        ["case_id", "revision_id"],
        unique=True,
        postgresql_where=sa.text("state IN ('queued','running')"),
    )
    op.create_table(
        "local_snapshots",
        sa.Column("manifest_path", sa.String(), nullable=False),
        sa.Column("case_uuid_set", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("file_hash_manifest", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("deletion_sequence", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("state IN ('valid','purged')", name=op.f("ck_local_snapshots_state")),
        sa.CheckConstraint("deletion_sequence >= 0", name=op.f("ck_local_snapshots_sequence")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_local_snapshots")),
    )
    op.create_table(
        "deletion_requests",
        sa.Column("case_uuid", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("active_purge_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("managed_snapshots_purged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_category", sa.String(), nullable=True),
        sa.Column("last_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("write_generation", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "(state = 'completed') = (active_purge_completed_at IS NOT NULL AND managed_snapshots_purged_at IS NOT NULL)",
            name=op.f("ck_deletion_requests_completion_requires_both_purges"),
        ),
        sa.CheckConstraint(
            "state IN ('accepted','purging','completed')", name=op.f("ck_deletion_requests_state")
        ),
        sa.CheckConstraint(
            "managed_snapshots_purged_at IS NULL OR active_purge_completed_at IS NOT NULL",
            name=op.f("ck_deletion_requests_snapshots_after_active"),
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["buyer_accounts.id"],
            name=op.f("fk_deletion_requests_owner_id_buyer_accounts"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_deletion_requests")),
    )
    op.create_index(
        op.f("ix_deletion_requests_case_uuid"), "deletion_requests", ["case_uuid"], unique=False
    )
    op.create_index(
        op.f("ix_deletion_requests_owner_id"), "deletion_requests", ["owner_id"], unique=False
    )
    op.create_table(
        "reports",
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("revision_id", sa.Uuid(), nullable=False),
        sa.Column("snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("renderer_version", sa.String(), nullable=False),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("artifact_id", sa.Uuid(), nullable=True),
        sa.Column("content_hash", sa.String(), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(state = 'failed') = (error IS NOT NULL)",
            name=op.f("ck_reports_error_only_on_failure"),
        ),
        sa.CheckConstraint(
            "(state = 'ready' AND artifact_id IS NOT NULL AND content_hash IS NOT NULL AND generated_at IS NOT NULL) OR (state <> 'ready' AND artifact_id IS NULL AND content_hash IS NULL AND generated_at IS NULL)",
            name=op.f("ck_reports_ready_bindings"),
        ),
        sa.CheckConstraint(
            "state IN ('generating','ready','failed')", name=op.f("ck_reports_state")
        ),
        sa.ForeignKeyConstraint(
            ["case_id", "artifact_id"],
            ["document_artifacts.case_id", "document_artifacts.id"],
            name=op.f("fk_reports_case_id_document_artifacts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["case_id", "revision_id"],
            ["requirement_revisions.case_id", "requirement_revisions.id"],
            name=op.f("fk_reports_case_id_requirement_revisions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["case_id", "snapshot_id"],
            ["assessment_snapshots.case_id", "assessment_snapshots.id"],
            name=op.f("fk_reports_case_id_assessment_snapshots"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["case_id"], ["cases.id"], name=op.f("fk_reports_case_id_cases"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reports")),
        sa.UniqueConstraint("case_id", "id", name=op.f("uq_reports_case_id_id")),
        sa.UniqueConstraint(
            "case_id",
            "snapshot_id",
            "renderer_version",
            name=op.f("uq_reports_case_id_snapshot_id_renderer_version"),
        ),
    )
    op.create_index(op.f("ix_reports_case_id"), "reports", ["case_id"], unique=False)


def downgrade() -> None:
    op.drop_index("uq_run_one_active_per_revision", table_name="verification_runs")
    op.create_index(
        "uq_run_one_active_per_case",
        "verification_runs",
        ["case_id"],
        unique=True,
        postgresql_where=sa.text("state IN ('queued','running')"),
    )
    op.drop_index(op.f("ix_reports_case_id"), table_name="reports")
    op.drop_table("reports")
    op.drop_index(op.f("ix_deletion_requests_owner_id"), table_name="deletion_requests")
    op.drop_index(op.f("ix_deletion_requests_case_uuid"), table_name="deletion_requests")
    op.drop_table("deletion_requests")
    op.drop_table("local_snapshots")
