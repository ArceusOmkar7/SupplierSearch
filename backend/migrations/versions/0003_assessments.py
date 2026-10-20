"""assessments

Revision ID: 0003_assessments
Revises: 0002_verification_sources
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003_assessments"
down_revision = "0002_verification_sources"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assessment_snapshots",
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("revision_id", sa.Uuid(), nullable=False),
        sa.Column("checklist_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("trigger", sa.String(), nullable=False),
        sa.Column("event_cutoff", sa.Integer(), nullable=False),
        sa.Column("assessment_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "supplier_processing_states", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("pending_action_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("coverage_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("qualified_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("follow_up_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("excluded_reasons", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("content_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("content_hash", sa.String(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "trigger IN ('initial','deadline','updated','completed')",
            name=op.f("ck_assessment_snapshots_trigger"),
        ),
        sa.CheckConstraint("event_cutoff >= 0", name=op.f("ck_assessment_snapshots_cutoff")),
        sa.CheckConstraint("sequence > 0", name=op.f("ck_assessment_snapshots_positive_sequence")),
        sa.ForeignKeyConstraint(
            ["case_id", "checklist_id", "revision_id"],
            [
                "checklist_versions.case_id",
                "checklist_versions.id",
                "checklist_versions.revision_id",
            ],
            name=op.f("fk_assessment_snapshots_case_id_checklist_versions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["case_id", "run_id", "revision_id"],
            ["verification_runs.case_id", "verification_runs.id", "verification_runs.revision_id"],
            name=op.f("fk_assessment_snapshots_case_id_verification_runs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["cases.id"],
            name=op.f("fk_assessment_snapshots_case_id_cases"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assessment_snapshots")),
        sa.UniqueConstraint("case_id", "id", name=op.f("uq_assessment_snapshots_case_id_id")),
        sa.UniqueConstraint(
            "case_id",
            "run_id",
            "content_hash",
            name=op.f("uq_assessment_snapshots_case_id_run_id_content_hash"),
        ),
        sa.UniqueConstraint(
            "case_id",
            "run_id",
            "sequence",
            name=op.f("uq_assessment_snapshots_case_id_run_id_sequence"),
        ),
    )
    op.create_index(
        op.f("ix_assessment_snapshots_case_id"), "assessment_snapshots", ["case_id"], unique=False
    )
    op.create_index(
        "ix_snapshots_case_created", "assessment_snapshots", ["case_id", "created_at"], unique=False
    )
    op.create_table(
        "supplier_decisions",
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("supplier_id", sa.Uuid(), nullable=True),
        sa.Column("decision", sa.String(), nullable=False),
        sa.Column("buyer_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column("operation_key", sa.String(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(decision = 'no_selection') = (supplier_id IS NULL)",
            name=op.f("ck_supplier_decisions_supplier_matches_decision"),
        ),
        sa.CheckConstraint(
            "decision IN ('select','reject','no_selection')",
            name=op.f("ck_supplier_decisions_decision"),
        ),
        sa.ForeignKeyConstraint(
            ["buyer_id"],
            ["buyer_accounts.id"],
            name=op.f("fk_supplier_decisions_buyer_id_buyer_accounts"),
        ),
        sa.ForeignKeyConstraint(
            ["case_id", "snapshot_id"],
            ["assessment_snapshots.case_id", "assessment_snapshots.id"],
            name=op.f("fk_supplier_decisions_case_id_assessment_snapshots"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["case_id", "supplier_id"],
            ["suppliers.case_id", "suppliers.id"],
            name=op.f("fk_supplier_decisions_case_id_suppliers"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["cases.id"],
            name=op.f("fk_supplier_decisions_case_id_cases"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_supplier_decisions")),
        sa.UniqueConstraint("case_id", "id", name=op.f("uq_supplier_decisions_case_id_id")),
    )
    op.create_index(
        op.f("ix_supplier_decisions_case_id"), "supplier_decisions", ["case_id"], unique=False
    )
    op.create_foreign_key(
        "fk_cases_latest_snapshot",
        "cases",
        "assessment_snapshots",
        ["id", "latest_snapshot_id"],
        ["case_id", "id"],
    )
    # Snapshots are immutable materializations: no UPDATE after publication.
    op.execute("""
        CREATE FUNCTION reject_snapshot_update() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'assessment snapshots are immutable';
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER snapshots_immutable BEFORE UPDATE ON assessment_snapshots
        FOR EACH ROW EXECUTE FUNCTION reject_snapshot_update()
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER snapshots_immutable ON assessment_snapshots")
    op.execute("DROP FUNCTION reject_snapshot_update()")
    op.drop_constraint("fk_cases_latest_snapshot", "cases", type_="foreignkey")
    op.drop_index(op.f("ix_supplier_decisions_case_id"), table_name="supplier_decisions")
    op.drop_table("supplier_decisions")
    op.drop_index("ix_snapshots_case_created", table_name="assessment_snapshots")
    op.drop_index(op.f("ix_assessment_snapshots_case_id"), table_name="assessment_snapshots")
    op.drop_table("assessment_snapshots")
    # ### end Alembic commands ###
