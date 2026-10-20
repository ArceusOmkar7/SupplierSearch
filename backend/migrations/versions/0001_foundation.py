"""Create the owned local verification foundation (no business seed data)."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_foundation"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "buyer_accounts",
        sa.Column("username_normalized", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_buyer_accounts")),
        sa.UniqueConstraint(
            "username_normalized", name=op.f("uq_buyer_accounts_username_normalized")
        ),
    )
    op.create_table(
        "cases",
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("active_revision_id", sa.Uuid(), nullable=True),
        sa.Column("latest_snapshot_id", sa.Uuid(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("write_generation", sa.Integer(), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleting_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(state = 'closed') = (closed_at IS NOT NULL)", name=op.f("ck_cases_closed_time")
        ),
        sa.CheckConstraint(
            "(state = 'deleting') = (deleting_at IS NOT NULL)", name=op.f("ck_cases_deleting_time")
        ),
        sa.CheckConstraint(
            "state IN ('draft','ready','active','assessed','closed','deleting')",
            name=op.f("ck_cases_state"),
        ),
        sa.CheckConstraint(
            "version > 0 AND write_generation > 0", name=op.f("ck_cases_positive_versions")
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["buyer_accounts.id"], name=op.f("fk_cases_owner_id_buyer_accounts")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cases")),
    )
    op.create_table(
        "login_sessions",
        sa.Column("id_hash", sa.String(), nullable=False),
        sa.Column("buyer_id", sa.Uuid(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("csrf_secret", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "expires_at > created_at", name=op.f("ck_login_sessions_positive_lifetime")
        ),
        sa.CheckConstraint(
            "last_seen_at >= created_at", name=op.f("ck_login_sessions_valid_last_seen")
        ),
        sa.ForeignKeyConstraint(
            ["buyer_id"],
            ["buyer_accounts.id"],
            name=op.f("fk_login_sessions_buyer_id_buyer_accounts"),
        ),
        sa.PrimaryKeyConstraint("id_hash", name=op.f("pk_login_sessions")),
    )
    op.create_table(
        "graph_checkpoint_refs",
        sa.Column("thread_id", sa.String(), nullable=False),
        sa.Column("checkpoint_namespace", sa.String(), nullable=False),
        sa.Column("checkpoint_id", sa.String(), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("state_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["cases.id"],
            name=op.f("fk_graph_checkpoint_refs_case_id_cases"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "thread_id",
            "checkpoint_namespace",
            "checkpoint_id",
            name=op.f("pk_graph_checkpoint_refs"),
        ),
        sa.UniqueConstraint(
            "case_id",
            "thread_id",
            "checkpoint_namespace",
            "checkpoint_id",
            name=op.f(
                "uq_graph_checkpoint_refs_case_id_thread_id_checkpoint_namespace_checkpoint_id"
            ),
        ),
    )
    op.create_table(
        "requirement_revisions",
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("requirements_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("location_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("supplier_set_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("input_provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_by", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(status = 'confirmed' AND confirmed_at IS NOT NULL AND confirmed_by IS NOT NULL) OR (status <> 'confirmed' AND confirmed_at IS NULL AND confirmed_by IS NULL)",
            name=op.f("ck_requirement_revisions_confirmation_pair"),
        ),
        sa.CheckConstraint(
            "status IN ('draft','confirmed','abandoned')",
            name=op.f("ck_requirement_revisions_status"),
        ),
        sa.CheckConstraint("sequence > 0", name=op.f("ck_requirement_revisions_positive_sequence")),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["cases.id"],
            name=op.f("fk_requirement_revisions_case_id_cases"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["confirmed_by"],
            ["buyer_accounts.id"],
            name=op.f("fk_requirement_revisions_confirmed_by_buyer_accounts"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_requirement_revisions")),
        sa.UniqueConstraint("case_id", "id", name=op.f("uq_requirement_revisions_case_id_id")),
        sa.UniqueConstraint(
            "case_id", "sequence", name=op.f("uq_requirement_revisions_case_id_sequence")
        ),
    )
    op.create_table(
        "suppliers",
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("original_identifiers", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "normalized_identifiers", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("source_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["case_id"], ["cases.id"], name=op.f("fk_suppliers_case_id_cases"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_suppliers")),
        sa.UniqueConstraint("case_id", "id", name=op.f("uq_suppliers_case_id_id")),
    )
    op.create_table(
        "work_items",
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=True),
        sa.Column("task_id", sa.Uuid(), nullable=True),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("operation_key", sa.String(), nullable=False),
        sa.Column("lease_owner", sa.String(), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fence", sa.Integer(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "state <> 'leased' OR (lease_owner IS NOT NULL AND lease_expires_at IS NOT NULL AND heartbeat_at IS NOT NULL)",
            name=op.f("ck_work_items_leased_fields"),
        ),
        sa.CheckConstraint(
            "state IN ('queued','leased','retry_wait','succeeded','failed','cancelled')",
            name=op.f("ck_work_items_state"),
        ),
        sa.CheckConstraint("fence > 0 AND attempts >= 0", name=op.f("ck_work_items_lease_counts")),
        sa.ForeignKeyConstraint(
            ["case_id"], ["cases.id"], name=op.f("fk_work_items_case_id_cases"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_work_items")),
        sa.UniqueConstraint("case_id", "id", name=op.f("uq_work_items_case_id_id")),
        sa.UniqueConstraint(
            "case_id", "operation_key", name=op.f("uq_work_items_case_id_operation_key")
        ),
    )
    op.create_table(
        "case_events",
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("revision_id", sa.Uuid(), nullable=True),
        sa.Column("run_id", sa.Uuid(), nullable=True),
        sa.Column("object_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("public_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("operation_key", sa.String(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("sequence > 0", name=op.f("ck_case_events_positive_sequence")),
        sa.ForeignKeyConstraint(
            ["case_id", "revision_id"],
            ["requirement_revisions.case_id", "requirement_revisions.id"],
            name=op.f("fk_case_events_case_id_requirement_revisions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["case_id"], ["cases.id"], name=op.f("fk_case_events_case_id_cases"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_case_events")),
        sa.UniqueConstraint(
            "case_id", "operation_key", name=op.f("uq_case_events_case_id_operation_key")
        ),
        sa.UniqueConstraint("case_id", "sequence", name=op.f("uq_case_events_case_id_sequence")),
    )
    op.create_table(
        "identity_resolutions",
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("revision_id", sa.Uuid(), nullable=False),
        sa.Column("supplier_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_record_ref", sa.String(), nullable=False),
        sa.Column("identifier_matches", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("discrepancies", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("proposed_score", sa.Float(), nullable=True),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("resolution_basis", sa.String(), nullable=False),
        sa.Column("resolved_by", sa.Uuid(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "state <> 'confirmed' OR (resolved_at IS NOT NULL AND resolution_basis <> '')",
            name=op.f("ck_identity_resolutions_confirmed_basis"),
        ),
        sa.CheckConstraint(
            "state IN ('proposed','confirmed','ambiguous','rejected')",
            name=op.f("ck_identity_resolutions_state"),
        ),
        sa.ForeignKeyConstraint(
            ["case_id", "revision_id"],
            ["requirement_revisions.case_id", "requirement_revisions.id"],
            name=op.f("fk_identity_resolutions_case_id_requirement_revisions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["case_id", "supplier_id"],
            ["suppliers.case_id", "suppliers.id"],
            name=op.f("fk_identity_resolutions_case_id_suppliers"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["cases.id"],
            name=op.f("fk_identity_resolutions_case_id_cases"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["resolved_by"],
            ["buyer_accounts.id"],
            name=op.f("fk_identity_resolutions_resolved_by_buyer_accounts"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_identity_resolutions")),
        sa.UniqueConstraint("case_id", "id", name=op.f("uq_identity_resolutions_case_id_id")),
    )
    op.create_table(
        "supplier_sites",
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("supplier_id", sa.Uuid(), nullable=False),
        sa.Column("raw_address", sa.String(), nullable=False),
        sa.Column("normalized_address", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("jurisdiction", sa.String(), nullable=False),
        sa.Column("identity_state", sa.String(), nullable=False),
        sa.Column("evidence_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "role IN ('registered_office','production_site','other','unknown')",
            name=op.f("ck_supplier_sites_role"),
        ),
        sa.ForeignKeyConstraint(
            ["case_id", "supplier_id"],
            ["suppliers.case_id", "suppliers.id"],
            name=op.f("fk_supplier_sites_case_id_suppliers"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["cases.id"],
            name=op.f("fk_supplier_sites_case_id_cases"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_supplier_sites")),
        sa.UniqueConstraint("case_id", "id", name=op.f("uq_supplier_sites_case_id_id")),
    )
    op.create_index(op.f("ix_cases_owner_id"), "cases", ["owner_id"], unique=False)
    op.create_index(
        op.f("ix_login_sessions_buyer_id"), "login_sessions", ["buyer_id"], unique=False
    )
    op.create_index(
        op.f("ix_graph_checkpoint_refs_case_id"), "graph_checkpoint_refs", ["case_id"], unique=False
    )
    op.create_index(
        op.f("ix_requirement_revisions_case_id"), "requirement_revisions", ["case_id"], unique=False
    )
    op.create_index(
        "uq_revision_active_draft",
        "requirement_revisions",
        ["case_id"],
        unique=True,
        postgresql_where=sa.text("status = 'draft'"),
    )
    op.create_index(op.f("ix_suppliers_case_id"), "suppliers", ["case_id"], unique=False)
    op.create_index(op.f("ix_work_items_case_id"), "work_items", ["case_id"], unique=False)
    op.create_index(op.f("ix_work_items_due_at"), "work_items", ["due_at"], unique=False)
    op.create_index(op.f("ix_case_events_case_id"), "case_events", ["case_id"], unique=False)
    op.create_index(
        op.f("ix_identity_resolutions_case_id"), "identity_resolutions", ["case_id"], unique=False
    )
    op.create_index(op.f("ix_supplier_sites_case_id"), "supplier_sites", ["case_id"], unique=False)
    op.create_foreign_key(
        "fk_cases_active_revision",
        "cases",
        "requirement_revisions",
        ["id", "active_revision_id"],
        ["case_id", "id"],
    )
    op.execute(
        "\n        CREATE FUNCTION protect_case_owner() RETURNS trigger LANGUAGE plpgsql AS $$\n        BEGIN\n            IF NEW.owner_id IS DISTINCT FROM OLD.owner_id THEN\n                RAISE EXCEPTION 'Case ownership is immutable';\n            END IF;\n            RETURN NEW;\n        END $$;\n        CREATE TRIGGER immutable_case_owner BEFORE UPDATE ON cases\n        FOR EACH ROW EXECUTE FUNCTION protect_case_owner();\n    "
    )
    op.execute(
        "\n        CREATE FUNCTION protect_confirmed_revision() RETURNS trigger LANGUAGE plpgsql AS $$\n        BEGIN\n            IF OLD.status = 'confirmed' AND NEW IS DISTINCT FROM OLD THEN\n                RAISE EXCEPTION 'Confirmed revisions are immutable';\n            END IF;\n            RETURN NEW;\n        END $$;\n        CREATE TRIGGER immutable_confirmed_revision BEFORE UPDATE ON requirement_revisions\n        FOR EACH ROW EXECUTE FUNCTION protect_confirmed_revision();\n    "
    )


def downgrade() -> None:
    op.drop_constraint("fk_cases_active_revision", "cases", type_="foreignkey")
    op.drop_table("supplier_sites")
    op.drop_table("identity_resolutions")
    op.drop_table("case_events")
    op.drop_table("work_items")
    op.drop_table("suppliers")
    op.drop_table("requirement_revisions")
    op.drop_table("graph_checkpoint_refs")
    op.drop_table("login_sessions")
    op.drop_table("cases")
    op.drop_table("buyer_accounts")
    op.execute("DROP FUNCTION protect_confirmed_revision()")
    op.execute("DROP FUNCTION protect_case_owner()")
