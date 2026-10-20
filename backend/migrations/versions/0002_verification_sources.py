"""verification sources

Revision ID: 0002_verification_sources
Revises: 0001_foundation
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002_verification_sources"
down_revision = "0001_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "provider_accounts",
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("secret_ref", sa.String(), nullable=True),
        sa.Column("mode", sa.String(), nullable=False),
        sa.Column("enabled_capabilities", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("policy_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("allowed_data_classes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("quota_window", sa.String(), nullable=True),
        sa.Column("limits", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint("mode = 'free'", name=op.f("ck_provider_accounts_free_only")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_provider_accounts")),
    )
    op.create_table(
        "source_datasets",
        sa.Column("source_version", sa.String(), nullable=False),
        sa.Column("publisher", sa.String(), nullable=False),
        sa.Column("original_url", sa.String(), nullable=False),
        sa.Column("licence_attribution", sa.String(), nullable=False),
        sa.Column("obtained_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("publication_cutoff", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cutoff_unknown_reason", sa.String(), nullable=True),
        sa.Column("coverage", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("local_storage_key", sa.String(), nullable=False),
        sa.Column("sha256", sa.String(), nullable=False),
        sa.Column("format", sa.String(), nullable=False),
        sa.Column("schema_version", sa.String(), nullable=False),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("imported_count", sa.Integer(), nullable=False),
        sa.Column("quarantined_count", sa.Integer(), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "format IN ('csv','xlsx','pdf','html')", name=op.f("ck_source_datasets_format")
        ),
        sa.CheckConstraint(
            "state IN ('imported','quarantined','failed')", name=op.f("ck_source_datasets_state")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_source_datasets")),
        sa.UniqueConstraint(
            "sha256", "schema_version", name=op.f("uq_source_datasets_sha256_schema_version")
        ),
    )
    op.create_table(
        "source_definitions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("provider_family", sa.String(), nullable=False),
        sa.Column("jurisdiction", sa.String(), nullable=False),
        sa.Column("claim_coverage", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("allowed_hosts", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("access_mode", sa.String(), nullable=False),
        sa.Column("authority_roles", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("policy_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("policy_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("terms_version", sa.String(), nullable=True),
        sa.Column("capabilities", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "access_mode IN ('public_page','official_document','local_export','issuer_page','buyer_document','free_api')",
            name=op.f("ck_source_definitions_access_mode"),
        ),
        sa.PrimaryKeyConstraint("id", "version", name=op.f("pk_source_definitions")),
    )
    op.create_table(
        "case_creation_receipts",
        sa.Column("buyer_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(), nullable=False),
        sa.Column("body_hash", sa.String(), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["buyer_id"],
            ["buyer_accounts.id"],
            name=op.f("fk_case_creation_receipts_buyer_id_buyer_accounts"),
        ),
        sa.PrimaryKeyConstraint(
            "buyer_id", "idempotency_key", name=op.f("pk_case_creation_receipts")
        ),
    )
    op.create_table(
        "qco_records",
        sa.Column("source_document_id", sa.Uuid(), nullable=False),
        sa.Column("order_number", sa.String(), nullable=False),
        sa.Column("standard_codes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("product_scope", sa.String(), nullable=False),
        sa.Column("exclusions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("issued_on", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_on", sa.DateTime(timezone=True), nullable=True),
        sa.Column("amended_on", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("supersedes_ref", sa.String(), nullable=True),
        sa.Column("coverage_state", sa.String(), nullable=False),
        sa.Column("extracted_basis", sa.String(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "coverage_state IN ('complete','partial','stale')", name=op.f("ck_qco_records_coverage")
        ),
        sa.ForeignKeyConstraint(
            ["source_document_id"],
            ["source_datasets.id"],
            name=op.f("fk_qco_records_source_document_id_source_datasets"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_qco_records")),
    )
    op.create_index(
        op.f("ix_qco_records_source_document_id"),
        "qco_records",
        ["source_document_id"],
        unique=False,
    )
    op.create_table(
        "source_dataset_records",
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.Column("locator", sa.String(), nullable=False),
        sa.Column(
            "normalized_identifiers", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "selected_business_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("origin_hash", sa.String(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["source_datasets.id"],
            name=op.f("fk_source_dataset_records_dataset_id_source_datasets"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_source_dataset_records")),
        sa.UniqueConstraint(
            "dataset_id", "locator", name=op.f("uq_source_dataset_records_dataset_id_locator")
        ),
    )
    op.create_index(
        op.f("ix_source_dataset_records_dataset_id"),
        "source_dataset_records",
        ["dataset_id"],
        unique=False,
    )
    op.create_index(
        "ix_source_dataset_records_identifiers",
        "source_dataset_records",
        ["normalized_identifiers"],
        unique=False,
        postgresql_using="gin",
    )
    op.create_table(
        "checklist_versions",
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("revision_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("confirmed_by", sa.Uuid(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("policy_version", sa.String(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(status = 'confirmed' AND confirmed_at IS NOT NULL AND confirmed_by IS NOT NULL) OR (status = 'draft' AND confirmed_at IS NULL AND confirmed_by IS NULL)",
            name=op.f("ck_checklist_versions_confirmation_pair"),
        ),
        sa.CheckConstraint(
            "status IN ('draft','confirmed')", name=op.f("ck_checklist_versions_status")
        ),
        sa.CheckConstraint("sequence > 0", name=op.f("ck_checklist_versions_positive_sequence")),
        sa.ForeignKeyConstraint(
            ["case_id", "revision_id"],
            ["requirement_revisions.case_id", "requirement_revisions.id"],
            name=op.f("fk_checklist_versions_case_id_requirement_revisions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["cases.id"],
            name=op.f("fk_checklist_versions_case_id_cases"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["confirmed_by"],
            ["buyer_accounts.id"],
            name=op.f("fk_checklist_versions_confirmed_by_buyer_accounts"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_checklist_versions")),
        sa.UniqueConstraint(
            "case_id",
            "id",
            "revision_id",
            name=op.f("uq_checklist_versions_case_id_id_revision_id"),
        ),
        sa.UniqueConstraint("case_id", "id", name=op.f("uq_checklist_versions_case_id_id")),
        sa.UniqueConstraint(
            "case_id",
            "revision_id",
            "sequence",
            name=op.f("uq_checklist_versions_case_id_revision_id_sequence"),
        ),
    )
    op.create_index(
        op.f("ix_checklist_versions_case_id"), "checklist_versions", ["case_id"], unique=False
    )
    op.create_index(
        "uq_checklist_active_draft",
        "checklist_versions",
        ["case_id", "revision_id"],
        unique=True,
        postgresql_where=sa.text("status = 'draft'"),
    )
    op.create_table(
        "conversation_messages",
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("revision_id", sa.Uuid(), nullable=True),
        sa.Column("actor", sa.String(), nullable=False),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column("component_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("client_message_id", sa.String(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "actor IN ('buyer','assistant','system')", name=op.f("ck_conversation_messages_actor")
        ),
        sa.CheckConstraint("sequence > 0", name=op.f("ck_conversation_messages_positive_sequence")),
        sa.ForeignKeyConstraint(
            ["case_id", "revision_id"],
            ["requirement_revisions.case_id", "requirement_revisions.id"],
            name=op.f("fk_conversation_messages_case_id_requirement_revisions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["cases.id"],
            name=op.f("fk_conversation_messages_case_id_cases"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_conversation_messages")),
        sa.UniqueConstraint(
            "case_id",
            "client_message_id",
            name=op.f("uq_conversation_messages_case_id_client_message_id"),
        ),
        sa.UniqueConstraint("case_id", "id", name=op.f("uq_conversation_messages_case_id_id")),
        sa.UniqueConstraint(
            "case_id", "sequence", name=op.f("uq_conversation_messages_case_id_sequence")
        ),
    )
    op.create_index(
        op.f("ix_conversation_messages_case_id"), "conversation_messages", ["case_id"], unique=False
    )
    op.create_table(
        "source_authorizations",
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("supplier_id", sa.Uuid(), nullable=False),
        sa.Column("provider_account_id", sa.Uuid(), nullable=False),
        sa.Column("basis", sa.String(), nullable=False),
        sa.Column("authorization_evidence_ref", sa.String(), nullable=False),
        sa.Column("scope", sa.String(), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_by", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["case_id", "supplier_id"],
            ["suppliers.case_id", "suppliers.id"],
            name=op.f("fk_source_authorizations_case_id_suppliers"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["cases.id"],
            name=op.f("fk_source_authorizations_case_id_cases"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["provider_account_id"],
            ["provider_accounts.id"],
            name=op.f("fk_source_authorizations_provider_account_id_provider_accounts"),
        ),
        sa.ForeignKeyConstraint(
            ["verified_by"],
            ["buyer_accounts.id"],
            name=op.f("fk_source_authorizations_verified_by_buyer_accounts"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_source_authorizations")),
        sa.UniqueConstraint("case_id", "id", name=op.f("uq_source_authorizations_case_id_id")),
    )
    op.create_index(
        op.f("ix_source_authorizations_case_id"), "source_authorizations", ["case_id"], unique=False
    )
    op.create_table(
        "claims",
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("revision_id", sa.Uuid(), nullable=False),
        sa.Column("checklist_id", sa.Uuid(), nullable=False),
        sa.Column("supplier_id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=True),
        sa.Column("parent_claim_id", sa.Uuid(), nullable=True),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("assertion", sa.String(), nullable=False),
        sa.Column("relevant_period", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("required_for_shortlist", sa.Boolean(), nullable=False),
        sa.Column("proof_criteria_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("processing_state", sa.String(), nullable=False),
        sa.Column("waiting_input", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "jsonb_typeof(proof_criteria_json) = 'object'", name=op.f("ck_claims_criteria_object")
        ),
        sa.CheckConstraint(
            "processing_state IN ('proposed','confirmed','queued','checking','evaluated')",
            name=op.f("ck_claims_processing_state"),
        ),
        sa.CheckConstraint(
            "type IN ('legal_existence','manufacturer','part_capability','certificate','regulatory','capacity')",
            name=op.f("ck_claims_type"),
        ),
        sa.CheckConstraint(
            "parent_claim_id IS NULL OR parent_claim_id <> id",
            name=op.f("ck_claims_no_self_parent"),
        ),
        sa.ForeignKeyConstraint(
            ["case_id", "checklist_id", "revision_id"],
            [
                "checklist_versions.case_id",
                "checklist_versions.id",
                "checklist_versions.revision_id",
            ],
            name=op.f("fk_claims_case_id_checklist_versions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["case_id", "checklist_id", "supplier_id", "parent_claim_id"],
            ["claims.case_id", "claims.checklist_id", "claims.supplier_id", "claims.id"],
            name=op.f("fk_claims_case_id_claims"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["case_id", "site_id"],
            ["supplier_sites.case_id", "supplier_sites.id"],
            name=op.f("fk_claims_case_id_supplier_sites"),
        ),
        sa.ForeignKeyConstraint(
            ["case_id", "supplier_id"],
            ["suppliers.case_id", "suppliers.id"],
            name=op.f("fk_claims_case_id_suppliers"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["case_id"], ["cases.id"], name=op.f("fk_claims_case_id_cases"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_claims")),
        sa.UniqueConstraint(
            "case_id",
            "checklist_id",
            "supplier_id",
            "id",
            name=op.f("uq_claims_case_id_checklist_id_supplier_id_id"),
        ),
        sa.UniqueConstraint("case_id", "id", name=op.f("uq_claims_case_id_id")),
    )
    op.create_index(op.f("ix_claims_case_id"), "claims", ["case_id"], unique=False)
    op.create_table(
        "verification_runs",
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("revision_id", sa.Uuid(), nullable=False),
        sa.Column("checklist_id", sa.Uuid(), nullable=False),
        sa.Column("policy_version", sa.String(), nullable=False),
        sa.Column("country_pack_version", sa.String(), nullable=False),
        sa.Column("mode", sa.String(), nullable=False),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("initial_deadline", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("budgets_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "(state IN ('completed','completed_with_gaps','cancelled','failed')) = (completed_at IS NOT NULL)",
            name=op.f("ck_verification_runs_terminal_completion"),
        ),
        sa.CheckConstraint("mode IN ('live','replay')", name=op.f("ck_verification_runs_mode")),
        sa.CheckConstraint(
            "state <> 'queued' OR started_at IS NULL",
            name=op.f("ck_verification_runs_queued_not_started"),
        ),
        sa.CheckConstraint(
            "state IN ('queued','running','completed','completed_with_gaps','cancelled','failed')",
            name=op.f("ck_verification_runs_state"),
        ),
        sa.CheckConstraint("generation > 0", name=op.f("ck_verification_runs_positive_generation")),
        sa.ForeignKeyConstraint(
            ["case_id", "checklist_id", "revision_id"],
            [
                "checklist_versions.case_id",
                "checklist_versions.id",
                "checklist_versions.revision_id",
            ],
            name=op.f("fk_verification_runs_case_id_checklist_versions"),
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["cases.id"],
            name=op.f("fk_verification_runs_case_id_cases"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_verification_runs")),
        sa.UniqueConstraint(
            "case_id", "id", "revision_id", name=op.f("uq_verification_runs_case_id_id_revision_id")
        ),
        sa.UniqueConstraint("case_id", "id", name=op.f("uq_verification_runs_case_id_id")),
        sa.UniqueConstraint(
            "case_id", "idempotency_key", name=op.f("uq_verification_runs_case_id_idempotency_key")
        ),
    )
    op.create_index(
        op.f("ix_verification_runs_case_id"), "verification_runs", ["case_id"], unique=False
    )
    op.create_index(
        "uq_run_one_active_per_case",
        "verification_runs",
        ["case_id"],
        unique=True,
        postgresql_where=sa.text("state IN ('queued','running')"),
    )
    op.create_table(
        "assessments",
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("revision_id", sa.Uuid(), nullable=False),
        sa.Column("checklist_id", sa.Uuid(), nullable=False),
        sa.Column("claim_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("verdict", sa.String(), nullable=False),
        sa.Column("reasoning", sa.String(), nullable=False),
        sa.Column("criterion_results", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("evidence_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("attempt_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("gaps", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("policy_version", sa.String(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "verdict IN ('proven','unproven','contradicted')", name=op.f("ck_assessments_verdict")
        ),
        sa.CheckConstraint("sequence > 0", name=op.f("ck_assessments_positive_sequence")),
        sa.ForeignKeyConstraint(
            ["case_id", "checklist_id", "revision_id"],
            [
                "checklist_versions.case_id",
                "checklist_versions.id",
                "checklist_versions.revision_id",
            ],
            name=op.f("fk_assessments_case_id_checklist_versions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["case_id", "claim_id"],
            ["claims.case_id", "claims.id"],
            name=op.f("fk_assessments_case_id_claims"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["case_id", "run_id", "revision_id"],
            ["verification_runs.case_id", "verification_runs.id", "verification_runs.revision_id"],
            name=op.f("fk_assessments_case_id_verification_runs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["case_id"], ["cases.id"], name=op.f("fk_assessments_case_id_cases"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assessments")),
        sa.UniqueConstraint(
            "case_id",
            "claim_id",
            "run_id",
            "sequence",
            name=op.f("uq_assessments_case_id_claim_id_run_id_sequence"),
        ),
        sa.UniqueConstraint("case_id", "id", name=op.f("uq_assessments_case_id_id")),
    )
    op.create_index(op.f("ix_assessments_case_id"), "assessments", ["case_id"], unique=False)
    op.create_table(
        "budget_reservations",
        sa.Column("provider_account_id", sa.Uuid(), nullable=True),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("consumer", sa.String(), nullable=False),
        sa.Column("unit", sa.String(), nullable=False),
        sa.Column("reserved_amount", sa.Integer(), nullable=False),
        sa.Column("settled_amount", sa.Integer(), nullable=True),
        sa.Column("cycle", sa.String(), nullable=True),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("operation_key", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "state IN ('reserved','settled','released','expired')",
            name=op.f("ck_budget_reservations_state"),
        ),
        sa.CheckConstraint(
            "reserved_amount >= 0 AND (settled_amount IS NULL OR settled_amount >= 0)",
            name=op.f("ck_budget_reservations_non_negative"),
        ),
        sa.ForeignKeyConstraint(
            ["case_id", "run_id"],
            ["verification_runs.case_id", "verification_runs.id"],
            name=op.f("fk_budget_reservations_case_id_verification_runs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["cases.id"],
            name=op.f("fk_budget_reservations_case_id_cases"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["provider_account_id"],
            ["provider_accounts.id"],
            name=op.f("fk_budget_reservations_provider_account_id_provider_accounts"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_budget_reservations")),
        sa.UniqueConstraint(
            "case_id", "operation_key", name=op.f("uq_budget_reservations_case_id_operation_key")
        ),
    )
    op.create_index(
        op.f("ix_budget_reservations_case_id"), "budget_reservations", ["case_id"], unique=False
    )
    op.create_table(
        "check_tasks",
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("supplier_id", sa.Uuid(), nullable=False),
        sa.Column("claim_ids", postgresql.ARRAY(sa.UUID()), nullable=False),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("check_type", sa.String(), nullable=False),
        sa.Column("dependency_ids", postgresql.ARRAY(sa.UUID()), nullable=False),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("operation_key", sa.String(), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("wait_action_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "state IN ('queued','running','succeeded','no_evidence','failed','waiting_input','cancelled')",
            name=op.f("ck_check_tasks_state"),
        ),
        sa.CheckConstraint(
            "NOT (id = ANY(dependency_ids))", name=op.f("ck_check_tasks_no_self_dependency")
        ),
        sa.ForeignKeyConstraint(
            ["case_id", "run_id"],
            ["verification_runs.case_id", "verification_runs.id"],
            name=op.f("fk_check_tasks_case_id_verification_runs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["case_id", "supplier_id"],
            ["suppliers.case_id", "suppliers.id"],
            name=op.f("fk_check_tasks_case_id_suppliers"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["case_id"], ["cases.id"], name=op.f("fk_check_tasks_case_id_cases"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_check_tasks")),
        sa.UniqueConstraint("case_id", "id", name=op.f("uq_check_tasks_case_id_id")),
        sa.UniqueConstraint(
            "case_id", "operation_key", name=op.f("uq_check_tasks_case_id_operation_key")
        ),
    )
    op.create_index(op.f("ix_check_tasks_case_id"), "check_tasks", ["case_id"], unique=False)
    op.create_index(op.f("ix_check_tasks_run_id"), "check_tasks", ["run_id"], unique=False)
    op.create_table(
        "check_attempts",
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("revision_id", sa.Uuid(), nullable=False),
        sa.Column("supplier_id", sa.Uuid(), nullable=False),
        sa.Column("claim_ids", postgresql.ARRAY(sa.UUID()), nullable=False),
        sa.Column("source_version", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("target", sa.String(), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_dispatched", sa.Boolean(), nullable=False),
        sa.Column("outcome", sa.String(), nullable=False),
        sa.Column("reason_code", sa.String(), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("provider_request_id", sa.String(), nullable=True),
        sa.Column("artifact_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("retry_of", sa.Uuid(), nullable=True),
        sa.Column("operation_key", sa.String(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "kind = 'remote_request' OR NOT request_dispatched",
            name=op.f("ck_check_attempts_local_kind"),
        ),
        sa.CheckConstraint(
            "kind IN ('capability_check','remote_request','document_read','deadline_check')",
            name=op.f("ck_check_attempts_kind"),
        ),
        sa.CheckConstraint(
            "outcome <> 'skipped' OR NOT request_dispatched",
            name=op.f("ck_check_attempts_skip_not_sent"),
        ),
        sa.CheckConstraint(
            "outcome = 'success' OR jsonb_array_length(artifact_refs) = 0 OR outcome IN ('uncertain_outcome','no_record')",
            name=op.f("ck_check_attempts_no_content_no_artifacts"),
        ),
        sa.CheckConstraint(
            "outcome IN ('success','no_record','blocked','unavailable','timeout','transient_error','invalid_input','uncertain_outcome','skipped')",
            name=op.f("ck_check_attempts_outcome"),
        ),
        sa.CheckConstraint(
            "outcome NOT IN ('blocked','skipped','invalid_input') OR reason_code IS NOT NULL",
            name=op.f("ck_check_attempts_reason_required"),
        ),
        sa.CheckConstraint(
            "reason_code IS NULL OR reason_code IN ('not_configured','permission_unverified','consent_missing','budget_exhausted','quota_exhausted','not_supported','missing_identifier','captcha','locked_document','unsupported_language','too_large','malformed_document','deadline','robots_disallowed','ocr_unavailable')",
            name=op.f("ck_check_attempts_reason"),
        ),
        sa.CheckConstraint(
            "finished_at >= requested_at", name=op.f("ck_check_attempts_ordered_times")
        ),
        sa.CheckConstraint(
            "http_status IS NULL OR request_dispatched",
            name=op.f("ck_check_attempts_status_needs_dispatch"),
        ),
        sa.ForeignKeyConstraint(
            ["case_id", "retry_of"],
            ["check_attempts.case_id", "check_attempts.id"],
            name=op.f("fk_check_attempts_case_id_check_attempts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["case_id", "revision_id"],
            ["requirement_revisions.case_id", "requirement_revisions.id"],
            name=op.f("fk_check_attempts_case_id_requirement_revisions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["case_id", "run_id"],
            ["verification_runs.case_id", "verification_runs.id"],
            name=op.f("fk_check_attempts_case_id_verification_runs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["case_id", "supplier_id"],
            ["suppliers.case_id", "suppliers.id"],
            name=op.f("fk_check_attempts_case_id_suppliers"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["case_id", "task_id"],
            ["check_tasks.case_id", "check_tasks.id"],
            name=op.f("fk_check_attempts_case_id_check_tasks"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["cases.id"],
            name=op.f("fk_check_attempts_case_id_cases"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_check_attempts")),
        sa.UniqueConstraint("case_id", "id", name=op.f("uq_check_attempts_case_id_id")),
        sa.UniqueConstraint(
            "case_id", "operation_key", name=op.f("uq_check_attempts_case_id_operation_key")
        ),
    )
    op.create_index(op.f("ix_check_attempts_case_id"), "check_attempts", ["case_id"], unique=False)
    op.create_index(op.f("ix_check_attempts_run_id"), "check_attempts", ["run_id"], unique=False)
    op.create_table(
        "document_artifacts",
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("revision_id", sa.Uuid(), nullable=True),
        sa.Column("supplier_id", sa.Uuid(), nullable=True),
        sa.Column("origin", sa.String(), nullable=False),
        sa.Column("storage_key", sa.String(), nullable=False),
        sa.Column("sha256", sa.String(), nullable=False),
        sa.Column("media_type", sa.String(), nullable=False),
        sa.Column("byte_count", sa.Integer(), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_url", sa.String(), nullable=True),
        sa.Column("source_attempt_id", sa.Uuid(), nullable=True),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("state_reason", sa.String(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "origin IN ('buyer_upload','source_fetch','source_import','generated_report')",
            name=op.f("ck_document_artifacts_origin"),
        ),
        sa.CheckConstraint(
            "state IN ('queued','extracted','quarantined','failed','ready')",
            name=op.f("ck_document_artifacts_state"),
        ),
        sa.CheckConstraint(
            "byte_count >= 0 AND (page_count IS NULL OR page_count > 0)",
            name=op.f("ck_document_artifacts_sizes"),
        ),
        sa.ForeignKeyConstraint(
            ["case_id", "revision_id"],
            ["requirement_revisions.case_id", "requirement_revisions.id"],
            name=op.f("fk_document_artifacts_case_id_requirement_revisions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["case_id", "source_attempt_id"],
            ["check_attempts.case_id", "check_attempts.id"],
            name=op.f("fk_document_artifacts_case_id_check_attempts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["case_id", "supplier_id"],
            ["suppliers.case_id", "suppliers.id"],
            name=op.f("fk_document_artifacts_case_id_suppliers"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["cases.id"],
            name=op.f("fk_document_artifacts_case_id_cases"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_artifacts")),
        sa.UniqueConstraint("case_id", "id", name=op.f("uq_document_artifacts_case_id_id")),
        sa.UniqueConstraint("storage_key", name=op.f("uq_document_artifacts_storage_key")),
    )
    op.create_index(
        op.f("ix_document_artifacts_case_id"), "document_artifacts", ["case_id"], unique=False
    )
    op.create_table(
        "evidence_records",
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("supplier_id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=True),
        sa.Column("assertion_tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_version", sa.String(), nullable=False),
        sa.Column("source_ref", sa.String(), nullable=False),
        sa.Column("observation", sa.String(), nullable=False),
        sa.Column("locator", sa.String(), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("origin_lineage", sa.String(), nullable=False),
        sa.Column("self_reported", sa.Boolean(), nullable=False),
        sa.Column("authority_role", sa.String(), nullable=False),
        sa.Column("identity_resolution_id", sa.Uuid(), nullable=False),
        sa.Column("artifact_id", sa.Uuid(), nullable=True),
        sa.Column("content_hash", sa.String(), nullable=False),
        sa.Column("replay", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "authority_role IN ('official_registry','official_publication','issuer','accreditation_body','supplier','third_party','buyer')",
            name=op.f("ck_evidence_records_authority_role"),
        ),
        sa.CheckConstraint("observation <> ''", name=op.f("ck_evidence_records_has_observation")),
        sa.ForeignKeyConstraint(
            ["case_id", "artifact_id"],
            ["document_artifacts.case_id", "document_artifacts.id"],
            name=op.f("fk_evidence_records_case_id_document_artifacts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["case_id", "identity_resolution_id"],
            ["identity_resolutions.case_id", "identity_resolutions.id"],
            name=op.f("fk_evidence_records_case_id_identity_resolutions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["case_id", "run_id"],
            ["verification_runs.case_id", "verification_runs.id"],
            name=op.f("fk_evidence_records_case_id_verification_runs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["case_id", "site_id"],
            ["supplier_sites.case_id", "supplier_sites.id"],
            name=op.f("fk_evidence_records_case_id_supplier_sites"),
        ),
        sa.ForeignKeyConstraint(
            ["case_id", "supplier_id"],
            ["suppliers.case_id", "suppliers.id"],
            name=op.f("fk_evidence_records_case_id_suppliers"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["cases.id"],
            name=op.f("fk_evidence_records_case_id_cases"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_evidence_records")),
        sa.UniqueConstraint("case_id", "id", name=op.f("uq_evidence_records_case_id_id")),
    )
    op.create_index(
        op.f("ix_evidence_records_case_id"), "evidence_records", ["case_id"], unique=False
    )
    op.create_table(
        "extractions",
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("artifact_id", sa.Uuid(), nullable=False),
        sa.Column("page_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("method", sa.String(), nullable=False),
        sa.Column("fields", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("missing_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("uncertainties", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("model_id", sa.String(), nullable=True),
        sa.Column("schema_version", sa.String(), nullable=False),
        sa.Column("content_hash", sa.String(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "method IN ('text','ocr','model','rule')", name=op.f("ck_extractions_method")
        ),
        sa.ForeignKeyConstraint(
            ["case_id", "artifact_id"],
            ["document_artifacts.case_id", "document_artifacts.id"],
            name=op.f("fk_extractions_case_id_document_artifacts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["case_id"], ["cases.id"], name=op.f("fk_extractions_case_id_cases"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_extractions")),
        sa.UniqueConstraint("case_id", "id", name=op.f("uq_extractions_case_id_id")),
    )
    op.create_index(op.f("ix_extractions_case_id"), "extractions", ["case_id"], unique=False)
    op.create_table(
        "human_actions",
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("revision_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("affected_task_ids", postgresql.ARRAY(sa.UUID()), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("requested_document_ref", sa.Uuid(), nullable=True),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_ref", sa.String(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(state = 'resolved') = (resolved_at IS NOT NULL AND resolution_ref IS NOT NULL)",
            name=op.f("ck_human_actions_resolution_pair"),
        ),
        sa.CheckConstraint(
            "state IN ('pending','resolved','cancelled')", name=op.f("ck_human_actions_state")
        ),
        sa.CheckConstraint(
            "type IN ('supply_unlocked_document','resolve_identity')",
            name=op.f("ck_human_actions_type"),
        ),
        sa.ForeignKeyConstraint(
            ["case_id", "requested_document_ref"],
            ["document_artifacts.case_id", "document_artifacts.id"],
            name=op.f("fk_human_actions_case_id_document_artifacts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["case_id", "revision_id"],
            ["requirement_revisions.case_id", "requirement_revisions.id"],
            name=op.f("fk_human_actions_case_id_requirement_revisions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["case_id", "run_id"],
            ["verification_runs.case_id", "verification_runs.id"],
            name=op.f("fk_human_actions_case_id_verification_runs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["cases.id"],
            name=op.f("fk_human_actions_case_id_cases"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_human_actions")),
        sa.UniqueConstraint("case_id", "id", name=op.f("uq_human_actions_case_id_id")),
    )
    op.create_index(op.f("ix_human_actions_case_id"), "human_actions", ["case_id"], unique=False)
    op.create_table(
        "evidence_uses",
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("assessment_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_id", sa.Uuid(), nullable=False),
        sa.Column("criterion_id", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("period_fit", sa.String(), nullable=False),
        sa.Column("freshness_check_ref", sa.String(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "role IN ('supporting','refuting','context')", name=op.f("ck_evidence_uses_role")
        ),
        sa.ForeignKeyConstraint(
            ["case_id", "assessment_id"],
            ["assessments.case_id", "assessments.id"],
            name=op.f("fk_evidence_uses_case_id_assessments"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["case_id", "evidence_id"],
            ["evidence_records.case_id", "evidence_records.id"],
            name=op.f("fk_evidence_uses_case_id_evidence_records"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["cases.id"],
            name=op.f("fk_evidence_uses_case_id_cases"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_evidence_uses")),
        sa.UniqueConstraint(
            "case_id",
            "assessment_id",
            "evidence_id",
            "criterion_id",
            name=op.f("uq_evidence_uses_case_id_assessment_id_evidence_id_criterion_id"),
        ),
    )
    op.create_index(op.f("ix_evidence_uses_case_id"), "evidence_uses", ["case_id"], unique=False)
    op.create_foreign_key(
        op.f("fk_case_events_case_id_verification_runs"),
        "case_events",
        "verification_runs",
        ["case_id", "run_id"],
        ["case_id", "id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        op.f("fk_graph_checkpoint_refs_case_id_verification_runs"),
        "graph_checkpoint_refs",
        "verification_runs",
        ["case_id", "run_id"],
        ["case_id", "id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        op.f("fk_work_items_case_id_check_tasks"),
        "work_items",
        "check_tasks",
        ["case_id", "task_id"],
        ["case_id", "id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        op.f("fk_work_items_case_id_verification_runs"),
        "work_items",
        "verification_runs",
        ["case_id", "run_id"],
        ["case_id", "id"],
        ondelete="CASCADE",
    )
    # human_actions is created after check_tasks, so the circular reference is added last.
    op.create_foreign_key(
        "fk_check_tasks_wait_action",
        "check_tasks",
        "human_actions",
        ["case_id", "wait_action_id"],
        ["case_id", "id"],
    )
    # Assessments are append-only history; deletion stays possible for case purge.
    op.execute("""
        CREATE FUNCTION reject_assessment_update() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'assessments are append-only';
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER assessments_append_only BEFORE UPDATE ON assessments
        FOR EACH ROW EXECUTE FUNCTION reject_assessment_update()
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER assessments_append_only ON assessments")
    op.execute("DROP FUNCTION reject_assessment_update()")
    op.drop_constraint("fk_check_tasks_wait_action", "check_tasks", type_="foreignkey")
    op.drop_constraint(
        op.f("fk_work_items_case_id_verification_runs"), "work_items", type_="foreignkey"
    )
    op.drop_constraint(op.f("fk_work_items_case_id_check_tasks"), "work_items", type_="foreignkey")
    op.drop_constraint(
        op.f("fk_graph_checkpoint_refs_case_id_verification_runs"),
        "graph_checkpoint_refs",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_case_events_case_id_verification_runs"), "case_events", type_="foreignkey"
    )
    op.drop_index(op.f("ix_evidence_uses_case_id"), table_name="evidence_uses")
    op.drop_table("evidence_uses")
    op.drop_index(op.f("ix_human_actions_case_id"), table_name="human_actions")
    op.drop_table("human_actions")
    op.drop_index(op.f("ix_extractions_case_id"), table_name="extractions")
    op.drop_table("extractions")
    op.drop_index(op.f("ix_evidence_records_case_id"), table_name="evidence_records")
    op.drop_table("evidence_records")
    op.drop_index(op.f("ix_document_artifacts_case_id"), table_name="document_artifacts")
    op.drop_table("document_artifacts")
    op.drop_index(op.f("ix_check_attempts_run_id"), table_name="check_attempts")
    op.drop_index(op.f("ix_check_attempts_case_id"), table_name="check_attempts")
    op.drop_table("check_attempts")
    op.drop_index(op.f("ix_check_tasks_run_id"), table_name="check_tasks")
    op.drop_index(op.f("ix_check_tasks_case_id"), table_name="check_tasks")
    op.drop_table("check_tasks")
    op.drop_index(op.f("ix_budget_reservations_case_id"), table_name="budget_reservations")
    op.drop_table("budget_reservations")
    op.drop_index(op.f("ix_assessments_case_id"), table_name="assessments")
    op.drop_table("assessments")
    op.drop_index(
        "uq_run_one_active_per_case",
        table_name="verification_runs",
        postgresql_where=sa.text("state IN ('queued','running')"),
    )
    op.drop_index(op.f("ix_verification_runs_case_id"), table_name="verification_runs")
    op.drop_table("verification_runs")
    op.drop_index(op.f("ix_claims_case_id"), table_name="claims")
    op.drop_table("claims")
    op.drop_index(op.f("ix_source_authorizations_case_id"), table_name="source_authorizations")
    op.drop_table("source_authorizations")
    op.drop_index(op.f("ix_conversation_messages_case_id"), table_name="conversation_messages")
    op.drop_table("conversation_messages")
    op.drop_index(
        "uq_checklist_active_draft",
        table_name="checklist_versions",
        postgresql_where=sa.text("status = 'draft'"),
    )
    op.drop_index(op.f("ix_checklist_versions_case_id"), table_name="checklist_versions")
    op.drop_table("checklist_versions")
    op.drop_index(
        "ix_source_dataset_records_identifiers",
        table_name="source_dataset_records",
        postgresql_using="gin",
    )
    op.drop_index(op.f("ix_source_dataset_records_dataset_id"), table_name="source_dataset_records")
    op.drop_table("source_dataset_records")
    op.drop_index(op.f("ix_qco_records_source_document_id"), table_name="qco_records")
    op.drop_table("qco_records")
    op.drop_table("case_creation_receipts")
    op.drop_table("source_definitions")
    op.drop_table("source_datasets")
    op.drop_table("provider_accounts")
    # ### end Alembic commands ###
