---
description: "Dependency-ordered implementation tasks for local-first Supplier Verification Core 002"
---

# Tasks: Supplier Verification Core (002)

**Generated**: 2026-10-17 | **Selected feature**: `specs/002-supplier-verification-core` | **Actual branch**: `main`

**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md), [data-model.md](data-model.md), [HTTP API](contracts/http-api.md), [evidence/country contract](contracts/evidence-and-country-pack.md), [conversation](contracts/conversation.md), [quickstart.md](quickstart.md), and constitution v1.0.0.

**Status**: Implementation in progress (2026-10-20): 73 of 102 tasks are complete and verified; see [implementation-progress.md](implementation-progress.md) for exact test results, the real-source acceptance record and what is still open. US1 (T021–T053) and most of US2 (T054–T069) are complete; T070 (US2 end-to-end), most of US3 (T072–T076, T078, T081–T092) and all of Phase 6 remain. No feature acceptance is claimed: SC-002 and SC-003 are unmeasured because no independent human audit labels or observed per-supplier timings exist yet.

**Tests**: Included because the spec explicitly requires acceptance tests for confirmation, evidence policy, private ownership, restart survival, revisions, PDF agreement and deletion (SC-004–014, plus the auditor/timing evaluation). Story test tasks precede their implementation. Establish a meaningful failing behavioral assertion with environment/real-record prerequisites present; missing data or import errors are not evidence of a correct red/green cycle.

## Format and path conventions

- Every task uses `- [ ] Tnnn [P?] [USn?] description`; story phases require their story label, setup/foundation/polish do not.
- Paths in task descriptions are repository-relative, rooted at `C:/Users/hp/Documents/Projects/SupplierSearch`. Code paths are planned outputs; linked design documents already exist.
- `[P]` identifies disjoint-file opportunities once the listed dependencies and phase barriers are satisfied. It does not waive prerequisites or authorize parallel edits to shared registries/migrations/CLI files.
- Model tasks quote the design's field lists (including optional `?` markers), constraints and lifecycle verbatim. Apply the global schema rules: “UUID primary keys, UTC instants, explicit foreign keys and schema-versioned structured fields are the defaults.” and “Every private child row carries `case_id`; composite foreign keys prevent links across cases.”
- Do not invent stricter field lengths, missing source values, a current-status timestamp from import time, or unsupported country coverage. Preserve source originals and explicit uncertainty.

## Non-negotiable implementation boundaries

- Real-world source records only: no demo supplier seeds, synthetic datasets, fake certificates/provider responses, invented citations or model-generated auditor ground truth. Genuine captured bytes/rows can be replayed with original URL/date/hash and an explicit replay label.
- Controlled restart/fault/clock/security conditions may exercise genuine records, but are disclosed and never presented as real official source facts. Missing real inputs remain visible and cannot be replaced to make a test pass.
- Local-first with zero required paid spend: local PostgreSQL, ordinary private files and installed local Ollama; optional eligible Gemini free tier. No required premium data API, billing-enabled fallback, AWS/LocalStack, Keycloak, hosting or cloud backup work.
- Scraping and source checks proceed automatically after buyer confirmation. Source denial/CAPTCHA/quota/missing data produces eligible free alternatives or unproven gaps; no buyer-performed portal task.
- Keep the shared proof/confirmation/owner/deletion rules. No003 discovery index,004 buyer drawing intake,005 sending,006 voice,007 monitoring or008 country implementation in002.

## Phase 1: Setup (Shared Infrastructure)

**Goal**: Initialize a working local-only development/test environment and a genuine-record provenance policy.

**Completion criterion**: Setup captures are actual records with hashes/source dates, not demo seed data. Missing niche samples are documented; at least a real supplier/official-source baseline is required before related behavioral tests can run.

- [X] T001 Initialize the Python3.14 src-layout package and lock compatible FastAPI/Pydantic2/SQLAlchemy2/Alembic1/psycopg3/LangGraph1/Postgres-checkpointer, pwdlib, HTTPX, document/OCR/report and optional free-model dependencies in `backend/pyproject.toml` and `backend/uv.lock`; verify wheels on this Windows machine, document justified supported-version changes and add no paid API/S3 dependency. Coverage: FR-032.
- [X] T002 [P] Initialize React19/Vite8/TypeScript on supported Node22.23.2 (Node24 compatible) with dev/build/test/test:e2e scripts, same-origin loopback API proxy and accessible base styling in `frontend/package.json`, `frontend/package-lock.json` and `frontend/vite.config.ts`; do not create demo suppliers or seeded dashboards. Coverage: FR-001, FR-002, FR-032.
- [X] T003 [P] Provide optional PostgreSQL17-only local Docker configuration with persistent volume and loopback binding in `infra/compose.yaml`; document native-Postgres compatibility and add no Keycloak, object-store, cloud or paid service. Coverage: FR-020, FR-032.
- [X] T004 [P] Define validated local-free settings and ignored secret/data/output paths in `.env.example`, `.gitignore` and `backend/src/verisource/config.py`; default paid spend to zero, local data/ledger roots outside frontend assets, one inference/4096-token context, and no automatic model download or cloud failover. Depends on T001. Coverage: FR-028, FR-031, FR-032.
- [X] T005 [P] Configure Python lint/type checks, pytest markers and disposable test-DB safety in `backend/pyproject.toml` and `backend/tests/conftest.py`; tests must refuse a developer's live DB and missing real-record data must never be replaced by generated fixtures. Depends on T001. Coverage: FR-032.
- [X] T006 [P] Define provenance-checked genuine capture/replay manifests and acquisition documentation in `tests/records/README.md`, `tests/records/manifest.schema.json` and `backend/tests/records.py`; require actual URL/publisher/rights/time/cutoff/hash/locator, distinguish live/replay/controlled conditions, and keep private/raw records ignored. Depends on T001. Coverage: FR-018, FR-027, FR-032, FR-033, SC-005, SC-014.
- [X] T007 Acquire permitted actual supplier/official/issuer document records from researched sources and a genuine buyer/public procurement request for acceptance use; write only actual capture manifests and original bytes under `.local/records/` and an acquisition/coverage log in `tests/records/acquisition.md`; record inaccessible/missing locked/scanned/contradicted samples rather than inventing records, order values or auditor labels. Depends on T006. Coverage: FR-009, FR-010, FR-011, FR-012, FR-013, FR-032, FR-033, SC-002, SC-007, SC-014.

**Checkpoint**: Local package/infrastructure definitions and genuine baseline record acquisition are ready.

## Phase 2: Foundational (Blocking Prerequisites)

**Goal**: Supply the common local identity, ownership, transaction, filesystem and durable scheduling infrastructure.

**Completion criterion**: Complete this phase before starting user stories. Account/schema/command tests must fail for the intended missing behavior before implementing it; not merely because the environment or required actual record is absent.

- [X] T008 Implement PostgreSQL engine/session handling, shared UUID/UTC mappings and Alembic scaffold in `backend/src/verisource/db/base.py`, `backend/src/verisource/db/session.py` and `backend/alembic.ini`; enforce “UUID primary keys, UTC instants, explicit foreign keys and schema-versioned structured fields are the defaults.” and “Every private child row carries `case_id`; composite foreign keys prevent links across cases.”; use one SQLAlchemy session per concurrent task. Depends on T001, T003, T004.
- [X] T009 [P] Implement local buyer/session persistence in `backend/src/verisource/db/models/identity.py` with fields, optional markers and constraints quoted below; no external IdP or refresh-token records. Depends on T008. BuyerAccount fields: “id, username_normalized, password_hash, display_name, created_at, disabled_at?”. Constraints: “Unique normalized username; maintained pwdlib Argon2 hash, operator-provisioned local accounts. No external identity server, teams or public registration.”. Session fields: “id_hash, buyer_id, created_at, last_seen_at, expires_at, revoked_at?, csrf_secret”. Constraints: “Raw cookie is opaque/random; store only its hash. Absolute8h/idle30min; explicit logout revokes. No cloud refresh credentials.”. Apply lifecycle nullability rules from data-model.md. Coverage: FR-028.
- [X] T010 [P] Implement shared case/revision/supplier/site/identity-resolution mappings in `backend/src/verisource/db/models/cases.py`; preserve source identifiers/addresses, immutable ownership and revision history, with fields/constraints quoted below. Depends on T008. Case fields: “id, owner_id, title, state, active_revision_id?, latest_snapshot_id?, version, write_generation, created_at, closed_at?, deleting_at?”. Constraints: “Owner immutable. Version for optimistic commands; generation fences workers. No TTL.”. Lifecycle: “draft → ready → active → assessed → closed. Owner reopen returns a closed case to ready; new confirmed revision/checklist selects later work without altering earlier snapshots. Any nondeleted state → deleting → deleted. Run state and latest snapshot are separately represented.”. RequirementRevision fields: “id, case_id, sequence, status, requirements_json, location_json, supplier_set_json, input_provenance, confirmed_at?, confirmed_by?, created_at”. Constraints: “Unique case+sequence. Draft editable; confirmed payload immutable. One active draft per case. Supplier set freezes the identifiers selected for that revision.”. Lifecycle: “draft → confirmed; confirmed payload never edited. A later draft can be abandoned without invalidating its confirmed predecessor.”. Supplier fields: “id, case_id, display_name, original_identifiers, normalized_identifiers, source_refs, created_at”. Constraints: “Case-local entity, not a global discovery index. Same-name/GST conflicts do not silently merge.”. SupplierSite fields: “id, case_id, supplier_id, raw_address, normalized_address, role, jurisdiction, identity_state, evidence_refs”. Constraints: “Role: registered_office/production_site/other/unknown. Keep office/factory distinctions and originals.”. IdentityResolution fields: “id, case_id, revision_id, supplier_id, candidate_record_ref, identifier_matches, discrepancies, proposed_score?, state, resolution_basis, resolved_by?, resolved_at?”. Constraints: “proposed/confirmed/ambiguous/rejected. A fuzzy score cannot confirm identity. A buyer-confirmed candidate remains subject to substantive proof criteria.”. Apply nullable pointers/timestamps and confirmation-pair constraints from data-model.md. Coverage: FR-003, FR-004, FR-005, FR-006, FR-015, FR-016, FR-020, FR-028, FR-029.
- [X] T011 [P] Implement durable work/event/checkpoint-reference mappings in `backend/src/verisource/db/models/work.py`; use library-managed checkpoint tables plus case/run mappings, not an in-memory saver, with fields/constraints quoted below. Depends on T008. WorkItem fields: “id, case_id, run_id?, task_id?, kind, state, operation_key, lease_owner?, lease_expires_at?, heartbeat_at?, fence, attempts, due_at, payload_refs”. Constraints: “Queued/leased/retry_wait/succeeded/failed/cancelled. Use SKIP LOCKED, lease60s, heartbeat15s, recovery scan30s; recheck generation at commit. Payload holds IDs, not copies of documents.”. CaseEvent fields: “id, case_id, sequence, type, revision_id?, run_id?, object_refs, public_payload, created_at, operation_key”. Constraints: “Unique case+sequence and operation key. Durable SSE reconnect cursor. Owner-authorized and no-store; purged with case.”. GraphCheckpoint fields: “thread_id, checkpoint_id, checkpoint_namespace, case_id mapping, run_id mapping, state_refs, created_at”. Constraints: “Library-managed schema plus app mapping. Thread unique per case/revision/run. Sync durability; records remain canonical across replay.”. Coverage: FR-020, FR-027, FR-030.
- [X] T012 Register foundational mappings and create/apply the first owned migration in `backend/src/verisource/db/models/__init__.py` and `backend/migrations/versions/0001_foundation.py`; validate composite ownership keys, actual DB round trips and case/revision FK creation order without deleting an existing developer database. Defer only forward FKs to later-story tables until their owning migration; add those constraints before exposing their story routes. Depends on T009, T010, T011. Exercise valid drafts and reject impossible null/state combinations.
- [X] T013 [P] Create the FastAPI app, health routes, owner-safe error envelope, structured redacted logging and correlation IDs in `backend/src/verisource/api/app.py`, `backend/src/verisource/api/errors.py` and `backend/src/verisource/observability.py`; expose no source/model secrets or private content through readiness errors. Depends on T008, T004. Coverage: FR-001, FR-028.
- [X] T014 [P] Write executable authentication/owner-boundary regression tests in `backend/tests/integration/test_local_auth.py` using provisioned local accounts and real case records where available; cover generic bad-login errors, CSRF/Origin/Host, logout/expiry and signed-out401 versus nonowner404; establish failing behavior before implementation. Depends on T012, T013, T007. Coverage: FR-028, SC-009.
- [X] T015 [P] Implement private filesystem storage and atomic hashing/write/read/delete/list in `backend/src/verisource/storage/filesystem.py`; generated case/UUID relative keys only, reject traversal/symlink/junction escapes, no frontend static/public URL, and preserve originals. Enforce certificate limits “Limits20MiB/50 PDF pages.” at the document boundary without treating bulk exports as certificate uploads. Depends on T004. Coverage: FR-010, FR-018, FR-020, FR-023, FR-028, FR-031, FR-032.
- [X] T016 Implement Argon2 local account provisioning, random hashed DB sessions, pre-auth CSRF and `/auth/csrf`, `/auth/login`, `/session`, `/auth/logout` in `backend/src/verisource/security/sessions.py` and `backend/src/verisource/api/auth.py`; use8h absolute/30min idle expiry, HttpOnly/SameSite cookies, explicit loopback-only Secure exception, login throttling and no default committed password. Depends on T014, T009, T013. Coverage: FR-028, SC-009.
- [X] T017 Centralize current-session, owner, deletion-state and same-case child authorization plus command Idempotency-Key/ETag handling in `backend/src/verisource/api/dependencies.py` and `backend/src/verisource/domain/commands.py`; preserve quoted contract “same key/different body is409” and “Reject concurrent stale edits rather than silently merge.”; no owner_id trusted from client/model. Depends on T016, T010. Coverage: FR-004, FR-008, FR-020, FR-028, FR-029, FR-031, SC-009, SC-010.
- [X] T018 [P] Implement the durable dispatcher, lease heartbeat/recovery, generation fences and separate API/worker process entry in `backend/src/verisource/orchestration/worker.py` and `backend/src/verisource/orchestration/jobs.py`; persist results before acknowledgement, use atomic domain/event/work intent and disclose uncertain external retries rather than exactly-once billing. Depends on T012, T013. Coverage: FR-020, FR-027, FR-030, FR-031, SC-006.
- [X] T019 [P] Implement typed API/error/CSRF/ETag/idempotency clients and local login/session view in `frontend/src/api/client.ts` and `frontend/src/app/Login.tsx`; clear private caches/streams on logout and handle owner-safe401/404/412 without demo fallback data. Depends on T002, T013. Coverage: FR-001, FR-028, SC-009.
- [X] T020 Provide `setup-local`, interactive `create-buyer` and zero-spend `preflight --profile local-free` entry points in `backend/src/verisource/operations/cli.py` and `backend/src/verisource/operations/preflight.py`; check local DB/checkpointer/files/ledger/model without demanding paid keys or creating sample business records. Depends on T016, T015, T018. Coverage: FR-020, FR-028, FR-031, FR-032, SC-014.

**Checkpoint**: Foundation complete; US1 may begin.

## Phase 3: User Story 1 — Confirm requirements and verify a known supplier list (P1)

**Goal**: Confirm actual typed requirements and a known supplier list; approve claims; automatically collect available free evidence/local official records and produce inspectable initial claim assessments.

**Independent Test**: Use a genuine buyer/public procurement request plus four actual suppliers (five for timing). Correct and confirm intake/checklist, exercise actual accessible and blocked sources without buyer portal actions, read certificates/imported official records and inspect real attempts/evidence/assessments. No discovery, email or rich US2 comparison is required. Available source gaps are an explicit result, not a fake success.

### Tests required by the specification

- [X] T021 [P] [US1] Write pre-implementation API contract tests for editable intake, case/messages/revisions, checklist confirmation, run admission and source/document actions in `backend/tests/contract/test_us1_workflow.py`; use genuine records/input, require both confirmation gates and at least one required claim, and reject stale/cross-case references. Depends on T020, T017, T019, T007. Coverage: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008, FR-028, SC-004, SC-009.
- [X] T022 [P] [US1] Write real-record integration tests in `backend/tests/integration/test_us1_collection.py` for permitted collection/local import, actual blocked-source replay, source-missing decisions, PDF/OCR limits and dependent-only locked-document waits; never fabricate HTTP/provider/certificate content and keep missing genuine samples explicit. Depends on T020, T017, T019, T007. Coverage: FR-009, FR-010, FR-011, FR-012, FR-013, FR-014, FR-027, FR-030, FR-032, FR-033, SC-005, SC-006, SC-012, SC-014.

### Implementation and integration

- [X] T023 [P] [US1] Implement message persistence in `backend/src/verisource/db/models/conversation.py` with quoted fields/constraints; interpretation text remains a draft and cannot authorize confirmation or work. Depends on T020, T021, T022. ConversationMessage fields: “id, case_id, revision_id?, actor, text, component_refs, sequence, created_at”. Constraints: “Monotonic case sequence. Model text cannot enact confirmations/approvals. Private content purged with case.”. Coverage: FR-001, FR-002, FR-004.
- [X] T024 [P] [US1] Implement checklist/claim/run/check-task mappings in `backend/src/verisource/db/models/verification.py` with quoted fields/constraints; preserve explicit proof criteria, required flags, acyclic same-revision children and actual run mode. Depends on T020, T021, T022. ChecklistVersion fields: “id, case_id, revision_id, sequence, status, confirmed_by?, confirmed_at?, policy_version”. Constraints: “Draft/editable then confirmed/immutable. Edits after confirmation create another version, preserving old criteria.”. Lifecycle: “draft → confirmed; modified criteria/required flags create a new draft version needing confirmation.”. Claim fields: “id, case_id, revision_id, checklist_id, supplier_id, site_id?, parent_claim_id?, type, assertion, relevant_period, required_for_shortlist, proof_criteria_json, processing_state”. Constraints: “Every confirmed claim has explicit criteria/entity/site/period. Parent and children share supplier/revision/checklist. No cycles. Required parent uses the same compound rules.”. Lifecycle: “proposed → confirmed → queued → checking → evaluated; waiting_input is orthogonal to the last assessment. After a new run, old verdict is historical until reassessed; do not relabel it as proof for changed requirements.”. VerificationRun fields: “id, case_id, revision_id, checklist_id, policy_version, country_pack_version, mode, state, requested_at, started_at?, initial_deadline, completed_at?, budgets_json, generation, idempotency_key”. Constraints: “Confirmed revision/checklist only. Live retrieval versus genuine-record replay is immutable/visible, with imported-source dates preserved. No synthetic/demo mode. New runs preserve history.”. Lifecycle: “queued → running → completed/completed_with_gaps, with cancelled/failed for orchestration failure. Individual tasks can wait on uploaded-document/identity actions while other tasks progress. Initial snapshot can exist while some tasks wait.”. CheckTask fields: “id, case_id, run_id, supplier_id, claim_ids, source_id, check_type, dependency_ids, state, operation_key, due_at, deadline_at, wait_action_id?”. Constraints: “Durable independent units. No cyclic dependencies; old-revision tasks cannot write new-revision results. At most one active operation key.”. Lifecycle: “queued → running → succeeded/no_evidence/failed; running → waiting_input only for permitted human-action types. Waiting → queued on valid resolution; any pending state → cancelled by owner closure/deletion or supersession policy. Source blockage itself is no_evidence after alternatives, never waiting for buyer scraping.”. Apply nullable confirmation pairs and terminal-state constraints from data-model.md. Coverage: FR-007, FR-008, FR-017, FR-026, FR-029.
- [X] T025 [P] [US1] Implement source/free-project/authorization/quota mappings in `backend/src/verisource/db/models/sources.py` with quoted fields/constraints; optional free-project policy must not create a premium-account prerequisite. Depends on T020, T021, T022. SourceDefinition fields: “id, version, provider_family, jurisdiction, claim_coverage, allowed_queries/hosts, access_mode, authority_roles, policy_checked_at, policy_refs, terms_version, capabilities”. Constraints: “Global non-case configuration; immutable version per run. No secret values. API/public-page/official-document/issuer adapter capabilities are distinct.”. ProviderAccount fields: “id, provider, secret_ref?, mode, enabled_capabilities, policy_refs, allowed_data_classes, quota_window?, limits?, verified_at”. Constraints: “Optional free Gemini/project configuration, not required for local inference or public sources. Paid mode disabled; no mandatory premium provider setup. Never infer unlimited free quota.”. SourceAuthorization fields: “id, case_id, supplier_id, provider_account_id, basis, authorization_evidence_ref, scope, effective_at, expires_at?, verified_by”. Constraints: “Required only where the provider requires it. Missing basis means consent_missing; it does not generate a buyer scraping task.”. BudgetReservation fields: “id, provider_account_id?, run_id, case_id, consumer, unit, reserved_amount, settled_amount?, cycle?, state, operation_key, expires_at”. Constraints: “Free request/token/concurrency quota reservations; global zero paid-spend policy. No tariff/account prerequisite for free pages or local files. Future features share actual project quota.”. Coverage: FR-011, FR-012, FR-014, FR-024, FR-027, FR-032.
- [X] T026 [P] [US1] Implement attempt/artifact/extraction mappings in `backend/src/verisource/db/models/artifacts.py` with quoted fields/constraints; preserve actual dispatch/retry/missing fields and private local file references. Depends on T020, T021, T022. CheckAttempt fields: “id, case_id, run_id, task_id, revision_id, supplier_id, claim_ids, source_version, kind, target, requested_at, started_at?, finished_at, request_dispatched, outcome, reason_code, http_status?, provider_request_id?, artifact_refs, retry_of?, operation_key”. Constraints: “Kind capability_check/remote_request/document_read/deadline_check. A local skip cannot claim a network dispatch. No-content attempts have no evidence excerpt. Preserve each actual retry and uncertain outcome.”. DocumentArtifact fields: “id, case_id, revision_id?, supplier_id?, origin, storage_key, sha256, media_type, byte_count, page_count?, collected_at, source_url?, source_attempt_id?, state”. Constraints: “Origin buyer_upload/source_fetch/source_import/generated_report. Generated case/UUID relative file keys under private app root; no client-supplied paths, traversal/junction escapes or frontend-static files. Atomic writes; preserve actual original file. Limits20MiB/50 PDF pages. Unsafe files quarantined.”. Extraction fields: “id, case_id, artifact_id, page_refs, method, fields, missing_fields, uncertainties, model_id?, prompt/schema_version, created_at, content_hash”. Constraints: “Text/OCR/model mapping remains distinct from original artifact. Missing dates/fields remain unknown; extracted certificates are not proof by themselves.”. Attempt outcome/reason validation: “Attempt outcomes: success, no_record, blocked, unavailable, timeout, transient_error, invalid_input, uncertain_outcome, skipped. Reasons distinguish not_configured, permission_unverified, consent_missing, budget_exhausted, quota_exhausted, not_supported, missing_identifier, captcha, locked_document, unsupported_language, too_large, malformed_document and deadline. `no_record` is not a contradiction. `request_dispatched=false` and a capability/deadline explanation must remain visible for work never sent externally.”. Coverage: FR-009, FR-010, FR-018, FR-027, FR-028, FR-032.
- [X] T027 [P] [US1] Implement evidence/use/assessment mappings in `backend/src/verisource/db/models/evidence.py` with quoted fields/constraints; store only retrieved observations and append assessments without allowing cross-case reference reuse. Depends on T020, T021, T022. EvidenceRecord fields: “id, case_id, run_id, supplier_id, site_id?, assertion_tags, source_version, source_url/document_ref, observation, page/locator, collected_at, issued_at?, expires_at?, effective_at?, origin_lineage, self_reported, authority_role, identity_resolution_id, artifact_id?, content_hash”. Constraints: “Must reference content actually retrieved/read. Repeated copies share lineage and cannot count as independent corroboration. No attempt outcome is disguised as evidence.”. EvidenceUse fields: “id, case_id, assessment_id, evidence_id, criterion_id, role, period_fit, freshness_check_ref”. Constraints: “supporting/refuting/context. Reuse requires current criterion/identity/freshness validation; no cross-case links.”. Assessment fields: “id, case_id, run_id, revision_id, checklist_id, claim_id, sequence, verdict, reasoning, criterion_results, evidence_refs, attempt_refs, gaps, policy_version, created_at”. Constraints: “Append-only; verdict exactly proven/unproven/contradicted. Assessment references must match case/supplier/assertion/site/period. Prior assessments remain inspectable.”. Coverage: FR-017, FR-018, FR-019, FR-026, FR-027, SC-005.
- [X] T028 [P] [US1] Implement real official-dataset/record/QCO mappings in `backend/src/verisource/db/models/datasets.py` with quoted fields/constraints; distinguish operator corpus, case copies, original cutoff and import time. Depends on T020, T021, T022. SourceDataset fields: “id, source_version, publisher, original_url, licence/attribution, obtained_at, publication/cutoff, coverage, local_storage_key, sha256, format, schema/import_version, state”. Constraints: “Actual legitimately acquired public/authorized CSV/XLSX/PDF/HTML. Global operator-only known-supplier source corpus, not a discovery index. Preserve original bytes and access restrictions; no demo rows.”. SourceDatasetRecord fields: “id, dataset_id, original_row/page_locator, normalized_identifiers, selected_business_fields, origin_hash”. Constraints: “Actual imported record linked to original row/page. Original cutoff governs historical claims; import date cannot refresh status. Exclude unnecessary personal fields from buyer views/free inference. Case EvidenceRecords reference attributed captured copies of actual selected records.”. QcoRecord fields: “id, source_document_id, order_number, standard_codes, product_scope, exclusions, issued/effective/amended_dates, supersedes_ref?, coverage_state, extracted_basis”. Constraints: “Versioned official-source observations. A stale/incomplete corpus or absent search hit cannot establish non-applicability.”. Coverage: FR-012, FR-013, FR-025, FR-033.
- [X] T029 [P] [US1] Implement dependent action persistence in `backend/src/verisource/db/models/actions.py` with quoted fields/constraints; manual portal/CAPTCHA tasks are not permitted. Depends on T020, T021, T022. HumanAction fields: “id, case_id, revision_id, run_id, affected_task_ids, type, requested_document_ref?, state, created_at, resolved_at?, resolution_ref?”. Constraints: “Core type supply_unlocked_document/resolve_identity. No manual portal/CAPTCHA/scraping task. Only dependent tasks wait.”. Coverage: FR-014, FR-020, FR-030.
- [X] T030 [US1] Register US1 mappings, add foundational forward FKs whose targets now exist and create/apply ordered migration `backend/migrations/versions/0002_verification_sources.py`; validate case/revision/run/checkpoint relationships and every entity constraint from `specs/002-supplier-verification-core/data-model.md`. Depends on T023, T024, T025, T026, T027, T028, T029.
- [X] T031 [P] [US1] Implement genuine-record capture and manifest validation in `backend/src/verisource/operations/capture.py` and `backend/src/verisource/sources/manifests.py`; record actual bytes/URL/publisher/rights/collection+publication dates/hash/locator, support labeled faithful replay, and reject absent/provenance-incomplete data instead of seeding substitutes. Depends on T030, T015, T006. Coverage: FR-009, FR-018, FR-027, FR-032, FR-033, SC-005, SC-014.
- [X] T032 [P] [US1] Implement owner-scoped case/message and draft requirement creation/edit/confirmation in `backend/src/verisource/domain/intake.py` and `backend/src/verisource/api/cases.py`; freeze chosen supplier identifiers/locations, preserve listing URLs without fetching IndiaMART and enforce “Missing values remain null/unknown; no default inferred capability.” and “Quantity must be positive when supplied, and radius includes unit/reference location.”. Depends on T030, T017. Coverage: FR-001, FR-003, FR-004, FR-005, FR-006, FR-028, SC-004, SC-009.
- [X] T033 [P] [US1] Define typed source/check/observation and country-pack registration contracts in `backend/src/verisource/country_packs/contracts.py` and `backend/src/verisource/country_packs/registry.py`; implement capabilities/plan_checks/normalize_identity/execute_check/interpret_regulation/warning_patterns without pack-owned verdict or owner overrides; unsupported coverage explicit. Depends on T030. Coverage: FR-024, FR-025, SC-008.
- [X] T034 [P] [US1] Implement source policy/robots and connection-time destination/redirect/subresource guards in `backend/src/verisource/sources/policy.py` and `backend/src/verisource/security/egress.py`; block private/link-local/metadata/credential URLs and prohibited hosts, treat robots allowance separately from reuse rights, and never solve CAPTCHAs or execute source instructions. Depends on T030, T013. Coverage: FR-009, FR-014, FR-018, FR-032, SC-012.
- [X] T035 [P] [US1] Implement digest-checked local `qwen3.5:4b` extraction in `backend/src/verisource/models/ollama.py` and Pydantic source-located output validation in `backend/src/verisource/models/schemas.py`; one inference/4096-token initial context with page chunking, preserve uncertainty/missing fields, no auto-download, cloud fallback or model-issued verdict/fetch command. Depends on T030, T004. Coverage: FR-003, FR-007, FR-010, FR-018, FR-032, SC-005, SC-014.
- [X] T036 [US1] Implement optional eligible free-tier Gemini extraction and actual project quota/data-class routing in `backend/src/verisource/models/gemini_free.py` and `backend/src/verisource/models/router.py`; keep private/unknown/personal input local, no billing-enabled/premium/Search fallback, no invented free RPM/RPD and bounded429 handling. Depends on T030, T004, T035. Coverage: FR-003, FR-007, FR-010, FR-032, SC-014.
- [X] T037 [P] [US1] Implement shared free request/token/concurrency reservations in `backend/src/verisource/sources/quotas.py`; enforce one active five-supplier batch, larger lists queued within case, global4/domain1/browser1 requests,20pages and5certificate PDFs/supplier, depth2,20s timeout, one transient retry and15min website deadline; no monetary tariff prerequisite for free pages/files. Depends on T030. Coverage: FR-009, FR-014, FR-027, FR-030, FR-032, SC-001, SC-012, SC-014.
- [X] T038 [P] [US1] Implement actual CSV/XLSX/PDF/HTML import, quarantine and exact-ID lookup in `backend/src/verisource/sources/imports.py` and `backend/src/verisource/operations/imports.py`; retain original manifests/rows/page locators, report genuine accepted/quarantined counts, distinguish historical cutoff/current status and avoid building003 discovery or inventing missing exports. Depends on T031, T028, T015. Coverage: FR-012, FR-013, FR-025, FR-033, SC-014.
- [X] T039 [P] [US1] Implement bounded HTTPX and eligible Playwright supplier-site traversal in `backend/src/verisource/sources/websites.py` and `backend/src/verisource/sources/browser.py`; capture product/process/photo-reference/address/certificate links as self-report with source/date/hash, recorded actual retries and no automatic IndiaMART visit. Depends on T034, T037, T031. Coverage: FR-005, FR-009, FR-014, FR-027, SC-012, SC-014.
- [X] T040 [P] [US1] Implement actual certificate text/OCR extraction and safe upload/download endpoints in `backend/src/verisource/documents/certificates.py` and `backend/src/verisource/api/documents.py`; extract number/issuer/standard/scope/site/expiry with page provenance, apply “Missing dates/fields remain unknown; extracted certificates are not proof by themselves.” and quoted artifact limits, and isolate unsafe parses from secrets/network. Depends on T026, T015, T035, T017. Coverage: FR-010, FR-018, FR-028, SC-005, SC-012.
- [X] T041 [P] [US1] Implement eligible free issuer/accreditation adapters in `backend/src/verisource/sources/issuers.py` using researched actual NABCB/issuer pages/client PDFs under per-source policy; record precise authority/scope/freshness, expose IAF unavailable without licensed access and require no Enterprise key or fabricated successful verification. Depends on T039, T033. Coverage: FR-011, FR-017, FR-018, FR-025, SC-005, SC-012, SC-014.
- [X] T042 [P] [US1] Implement India exact-ID/known-source lookup and available official QR follow-through in `backend/src/verisource/country_packs/india/registries.py`; follow only exact official QR links from real obtained certificates, keep GST syntax distinct from registry proof, preserve MCA/Udyam export cutoff, and report unavailable current checks without buyer lookup or paid route. Depends on T038, T039, T033. Coverage: FR-012, FR-014, FR-025, FR-033, SC-012, SC-014.
- [X] T043 [P] [US1] Implement versioned BIS order/amendment/effective-date ingestion and product applicability candidates in `backend/src/verisource/country_packs/india/bis.py`; preserve actual scope/exemptions/licence coverage and enforce “A stale/incomplete corpus or absent search hit cannot establish non-applicability.”; blocked current licence checks remain gaps. Depends on T038, T039, T033. Coverage: FR-013, FR-025, FR-033, SC-005, SC-014.
- [X] T044 [P] [US1] Implement supplier identifier/name/address matching and review service in `backend/src/verisource/country_packs/india/identity.py`; use foundational IdentityResolution records, preserve raw/normalized values, office/factory roles and shared-ID conflicts; fuzzy similarity alone establishes neither identity nor contradiction. Depends on T030, T033. Coverage: FR-015, FR-016, FR-019, FR-025, SC-005, SC-007.
- [X] T045 [US1] Implement standard separated claims, editable custom criteria/required flags and immutable checklist confirmation in `backend/src/verisource/domain/claims.py` and `backend/src/verisource/api/checklists.py`; cover all six proof-policy families, site/period/subclaims, enforce “At least one required claim must be selected before run admission, avoiding vacuous qualification.” and never generate claims from draft input. Depends on T032, T035, T036, T024. Coverage: FR-004, FR-007, FR-008, FR-017, FR-026.
- [X] T046 [US1] Implement shared criterion/admissibility/compound assessment policy in `backend/src/verisource/domain/evidence_policy.py`; validate actual reference ownership, entity/site/period/authority/freshness/independent lineage and conflicts for legal, manufacturer, capability, certificate, regulatory and capacity assertions; enforce “criterion_results records satisfied/refuted/insufficient plus actual references and reasoning.” semantically without trusting schema-valid model claims. Depends on T027, T044, T045. Coverage: FR-017, FR-018, FR-019, FR-026, SC-002, SC-005.
- [X] T047 [US1] Implement confirmed-run graph orchestration, atomic start intent, parallel independent checks, synchronous Postgres checkpoints, deadline assessments and cancel/read routes in `backend/src/verisource/orchestration/graph.py` and `backend/src/verisource/api/runs.py`; bind every result to case/run/revision/checklist/generation, preserve actual capability/no-content attempts and never wait for buyer scraping. Depends on T018, T045, T046, T039, T040, T041, T042, T043, T037. Coverage: FR-008, FR-009, FR-010, FR-011, FR-012, FR-013, FR-014, FR-020, FR-026, FR-027, FR-030, SC-001, SC-005, SC-006, SC-012.
- [X] T048 [US1] Implement uploaded-document/identity action read/resolve in `backend/src/verisource/domain/actions.py` and `backend/src/verisource/api/actions.py`; validate same-case replacement/resolution with ETag, resume only dependent checks, retain unrelated results, and do not unlock/bypass downloaded source documents. Depends on T047, T029, T040, T044. Coverage: FR-014, FR-020, FR-030, SC-006, SC-012.
- [X] T049 [US1] Implement durable case-local SSE and ordered message/event reads in `backend/src/verisource/api/events.py`; transactional sequence/operation IDs, Last-Event-ID replay/reset, deduplication, owner/deletion checks before each event and at least15s, and no reconnect-triggered commands or private cache leaks. Depends on T047, T017, T011, T023. Coverage: FR-001, FR-002, FR-018, FR-020, FR-028, FR-030, SC-006, SC-009, SC-012.
- [X] T050 [US1] Wire real `capture-source`, `import-source` and model/source preflight into `backend/src/verisource/operations/cli.py`; accept local manifest paths only in operator tooling, require no paid key and emit honest missing-download/schema/permission/coverage states without seeding data. Depends on T031, T038, T035, T036, T043. Coverage: FR-032, FR-033, SC-014.
- [X] T051 [US1] Implement actual case list/conversation, editable entire intake/supplier/location review and checklist confirmation in `frontend/src/app/CaseWorkspace.tsx`, `frontend/src/components/RequirementReview.tsx` and `frontend/src/components/ClaimChecklist.tsx`; preserve original/proposed values, missing fields, required flags, no auto-confirmation and no demo fallback. Depends on T032, T045, T019. Coverage: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008, SC-004.
- [X] T052 [US1] Implement real event reconnect/progress, attempt summary and dependent document/identity actions in `frontend/src/api/events.ts`, `frontend/src/components/CollectionProgress.tsx` and `frontend/src/components/HumanAction.tsx`; show live/replay/cutoff/source gaps separately, no portal/payment prompts, and available assessed claims before rich US2 comparison. Depends on T049, T048, T051. Coverage: FR-002, FR-014, FR-018, FR-027, FR-030, SC-012, SC-014.
- [X] T053 [US1] Run the real known-supplier journey and local-source/model integration through `tests/e2e/verify_known_suppliers.spec.ts` and `backend/tests/acceptance/test_us1_real_run.py`; verify confirmation/source/ownership contracts and actual evidence/attempt outputs, record code failures versus genuine missing-source data gaps in `.local/acceptance/core002/us1/`, and do not mark unperformed live checks passed. Depends on T021, T022, T047, T048, T052, T050. Coverage: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008, FR-009, FR-010, FR-011, FR-012, FR-013, FR-014, FR-015, FR-016, FR-017, FR-018, FR-019, FR-024, FR-025, FR-026, FR-027, FR-028, FR-030, FR-032, FR-033, SC-004, SC-005, SC-006, SC-012, SC-014.

**Checkpoint**: US1's real known-supplier verification journey is usable without later features. This is the first MVP, not full002 acceptance.

## Phase 4: User Story 2 — Inspect evidence and make a supplier decision (P2)

**Goal**: Inspect supplier-by-claim evidence, conflicts and immutable snapshots; recommend an eligible shortlist and preserve the buyer's final decision.

**Independent Test**: Starting from genuine stored US1 records, expand every evaluated cell into real reasoning/source dates/attempts/subclaims, inspect actual identity/source conflicts, verify required-claim eligibility and explicit empty results, and select/reject against a stable snapshot. Missing natural verdict/auditor samples remain untested, never invented.

### Tests required by the specification

- [X] T054 [P] [US2] Write real-record snapshot/evidence/attempt/decision API contracts in `backend/tests/contract/test_us2_assessments.py`; verify owner-scoped reads, exact criterion/reference/cutoff fields, partial snapshots, same-case decisions, empty qualified results and immutable historical snapshots before adding the routes. Depends on T053. Coverage: FR-017, FR-018, FR-019, FR-021, FR-022, FR-026, FR-028, SC-005, SC-009, SC-011.
- [X] T055 [P] [US2] Write criterion/compound/lineage/freshness/identity/required-claim tests in `backend/tests/integration/test_us2_proof_and_shortlist.py` against the acquired actual records; distinguish deliberately invalid references/attack conditions from genuine evidence, require no fake official status or invented auditor label, and report unavailable natural cases. Depends on T053. Coverage: FR-015, FR-016, FR-017, FR-018, FR-019, FR-022, FR-026, SC-002, SC-005, SC-007, SC-011.
- [X] T056 [P] [US2] Write interaction tests in `frontend/src/components/__tests__/EvidenceMatrix.test.tsx` using actual US1 response captures; verify accessible cell/subclaim expansion, originals/dates/source attempts, processing-versus-verdict labels and separate qualified/follow-up/excluded/empty views without fabricated data. Depends on T053. Coverage: FR-002, FR-018, FR-019, FR-021, FR-022, SC-005, SC-011.

### Implementation and integration

- [X] T057 [P] [US2] Implement immutable assessment snapshot and explicit buyer decision mappings in `backend/src/verisource/db/models/assessments.py` with quoted fields/constraints; snapshots preserve actual partial coverage and decisions cannot alter verdicts. Depends on T053, T054, T055, T056. AssessmentSnapshot fields: “id, case_id, run_id, revision_id, checklist_id, event_cutoff, assessment_ids, supplier_processing_states, pending_action_refs, coverage_summary, qualified_ids, follow_up_ids, excluded_reasons, created_at, content_hash”. Constraints: “Immutable materialization of report/table content. Lists derived under the same policy. Snapshot can be partial but every included evaluated claim has a verdict and truthful references.”. SupplierDecision fields: “id, case_id, snapshot_id, supplier_id?, decision, buyer_id, reason?, created_at”. Constraints: “select/reject/no_selection, explicit buyer command. Does not rewrite verdicts or represent automatic supplier approval.”. Coverage: FR-021, FR-022, FR-026.
- [X] T058 [US2] Register snapshot/decision mappings, add Case.latest_snapshot foreign key and apply `backend/migrations/versions/0003_assessments.py`; enforce same-case snapshot/assessment/supplier references, immutable identity and no mutable-PDF query assumptions. Depends on T057.
- [X] T059 [P] [US2] Implement owner-scoped original/normalized evidence and actual-attempt read models/routes in `backend/src/verisource/domain/evidence_queries.py` and `backend/src/verisource/api/evidence.py`; preserve both conflicting records, entity/site/period roles, dates, criterion reasoning and no-content missing reasons. Depends on T058, T017. Coverage: FR-015, FR-016, FR-018, FR-019, FR-021, FR-027, FR-028, SC-005, SC-009.
- [X] T060 [P] [US2] Implement deterministic qualification/follow-up/exclusion policy in `backend/src/verisource/domain/shortlist.py`; enforce “A supplier is qualified only if every buyer-required claim is proven.”, “Contradicted required claims exclude both lists but remain in the matrix.” and “Optional claim outcomes remain visible.”; never relax criteria to fill the list. Depends on T058, T046. Coverage: FR-017, FR-022, FR-026, SC-011.
- [X] T061 [P] [US2] Implement the four real-evidence manufacturer/trader review-pattern families in `backend/src/verisource/country_packs/india/warnings.py`; preserve actual references and never treat business-activity/site/catalogue/capacity-headcount indicators alone as proof/refutation; missing real pattern examples stay unverified. Depends on T058, T044, T059. Coverage: FR-019, FR-025, SC-007.
- [X] T062 [US2] Implement transactional snapshot assembly/publication in `backend/src/verisource/domain/snapshots.py`; freeze revision/checklist/run/policy/event cutoff, actual assessment IDs, truthful pending/skipped coverage and lists; every evaluated claim has its permitted verdict/references and later arrivals create later snapshots. Depends on T060, T059, T058. Coverage: FR-017, FR-018, FR-019, FR-021, FR-022, FR-026, SC-005, SC-011.
- [X] T063 [US2] Expose paginated immutable snapshot reads and explicit snapshot-bound buyer decision commands in `backend/src/verisource/api/assessments.py`; enforce Idempotency-Key/ETag/same-case authorization, actor/time and no silent approval/contact. Depends on T062, T017. Coverage: FR-021, FR-022, FR-028, SC-009, SC-011.
- [X] T064 [US2] Connect initial/deadline/updated snapshot publication and warning references to independent run completion in `backend/src/verisource/orchestration/assessment_publication.py`; a blocked supplier cannot hold all snapshots, closed/deleted generations cannot publish, and source gaps stay explicit. Depends on T062, T061, T047, T049. Coverage: FR-019, FR-020, FR-021, FR-022, FR-026, FR-030, SC-001, SC-005, SC-012.
- [X] T065 [US2] Build supplier-by-claim evidence matrix and accessible expanded evidence/subclaim inspection in `frontend/src/components/EvidenceMatrix.tsx` and `frontend/src/components/EvidenceDetails.tsx`; bind immutable snapshot ID, show three verdicts plus separate processing states, actual citations/attempts/originals/dates/lineage and visible conflicts. Depends on T059, T063, T056. Coverage: FR-002, FR-015, FR-016, FR-017, FR-018, FR-019, FR-021, SC-005.
- [X] T066 [US2] Build qualified/follow-up/excluded reasons and explicit buyer select/reject/no-selection controls in `frontend/src/components/Shortlist.tsx` and `frontend/src/components/SupplierDecision.tsx`; show no-qualified-supplier state, required flags, evidence gaps and snapshot reference without fabricated fallback cards. Depends on T065, T063. Coverage: FR-002, FR-022, SC-011.
- [X] T067 [US2] Integrate immutable snapshot selection, warning indicators and actual current/history context in `frontend/src/features/cases/AssessmentReview.tsx`; background completion must not silently change the snapshot the buyer is inspecting or deciding against. Depends on T066, T064. Coverage: FR-019, FR-021, FR-022, FR-026, SC-005, SC-011.
- [X] T068 [P] [US2] Implement real manifest/auditor-label validation, criterion agreement/confusion counts and `evaluate` CLI backend in `backend/src/verisource/operations/evaluation.py`; require actual independent labels, all claim/verdict classes and30 suppliers for SC-002, distinguish missing inputs/unmeasured criteria from passing, and never substitute model-generated ground truth. Depends on T062, T031. Use the same 30 real suppliers across six five-supplier cases as SC-002. Record active intervals for intake, corrections, confirmations, evidence review and decision/report actions; divide shared case time equally across evaluated suppliers and never double-count overlapping intervals. Report all 30 per-supplier totals and the maximum; every total must be under one hour. Separately record unattended collection and excluded actual waits. Missing any supplier timing leaves SC-003 unmeasured; a five-supplier timing run or average alone cannot pass it. The estimated manual baseline remains unverified. Coverage: FR-017, FR-018, FR-026, FR-032, SC-002, SC-003, SC-005, SC-007, SC-011, SC-014.
- [X] T069 [US2] Wire real-record `evaluate --manifest ... --profile local-free --output ...` into `backend/src/verisource/operations/cli.py`; persist dated protected results with live/replay/source limitations and individual unmet criteria rather than returning a false comprehensive pass. Depends on T068, T050. Coverage: FR-032, SC-002, SC-003, SC-014.
- [ ] T070 [US2] Validate comparison, evidence expansion, buyer choice and empty shortlist end to end in `tests/e2e/review_evidence.spec.ts` and record actual outputs under `.local/acceptance/core002/us2/`; repeat from stored genuine US1 records without requiring discovery/email or inventing unavailable verdict examples. Depends on T054, T055, T067, T069. Coverage: FR-002, FR-015, FR-016, FR-017, FR-018, FR-019, FR-021, FR-022, FR-026, FR-028, SC-005, SC-007, SC-009, SC-011.

**Checkpoint**: US2 comparison/decision works with real persisted US1 data; export/resume extensions remain US3.

## Phase 5: User Story 3 — Resume a case and share its report (P3)

**Goal**: Resume the same durable case, reconfirm later requirement revisions, close with gaps, export the selected snapshot and perform owner-controlled local retention/deletion/restore.

**Independent Test**: With actual records, interrupt/restart collection and an actual pending document/identity action; change real requirements and finish old work; compare all PDF pages to the chosen snapshot; delete during writes and restore offline. Preserve all committed undeleted state and unrelated cases, and prevent deleted/old-revision result resurrection.

### Tests required by the specification

- [X] T071 [P] [US3] Write revision/history/close/reopen contract tests in `backend/tests/contract/test_us3_lifecycle.py` using actual requirements/records; cover reconfirmation, checklist versioning, immutable closed snapshots, owner controls and late old-revision work before implementation. Depends on T070. Coverage: FR-020, FR-026, FR-028, FR-029, SC-006, SC-009, SC-010.
- [ ] T072 [P] [US3] Write process-kill/restart/duplicate-delivery integration tests in `backend/tests/integration/test_us3_restart.py`; use real stored state, actual pending actions and disclosed clock/fault conditions at domain-commit/checkpoint/ack boundaries, checking zero loss of committed records and no duplicate evidence. Depends on T070. Coverage: FR-020, FR-026, FR-027, FR-029, FR-030, SC-006, SC-010, SC-012.
- [ ] T073 [P] [US3] Write PDF snapshot/authorization tests in `backend/tests/integration/test_us3_reports.py` using actual US2 snapshots; require revision/list/reason/citation/attempt/date equality, a distinct later-snapshot report, owner reauthorization and legible long/Unicode data. Depends on T070. Assert null hash/artifact/generated time until ready, then require all three. Coverage: FR-018, FR-021, FR-022, FR-023, FR-028, SC-005, SC-009, SC-011.
- [ ] T074 [P] [US3] Write local retention/delete/managed-snapshot/offline-restore integration tests in `backend/tests/integration/test_us3_deletion.py`; use actual case files, disclose90day/1year clock advancement, exercise in-flight writes, missing ledger, physical snapshot-content purge and other-case/public-corpus preservation without synthetic evidence. Depends on T070. Offline restore must remove all restored login sessions and pre-auth bootstrap state before traffic/workers and require fresh sign-in. Old cookies and CSRF tokens must fail, including sessions logged out or expired after snapshot capture; fresh owner login must succeed. Physically remove each affected managed snapshot, or verify a sanitized reconstruction and physically remove its original before completion. Metadata invalidation alone is insufficient; inspect actual DB dumps, checkpoint copies, blobs and temporary archives for residual private content. Preserve other cases in active storage and independently acquired public corpus. Coverage: FR-020, FR-028, FR-031, SC-006, SC-009, SC-013.

### Implementation and integration

- [ ] T075 [P] [US3] Implement report persistence in `backend/src/verisource/db/models/reports.py` with quoted fields/constraints; retain renderer version for unique snapshot retry identity and private file reference only. Depends on T070, T071, T072, T073, T074. Report fields: “id, case_id, revision_id, snapshot_id, state, artifact_id?, content_hash?, generated_at?, error?”. Constraints: “Generating/ready/failed. Unique snapshot+renderer_version for retry reuse. PDF and JSON table derive from the same snapshot.”. Lifecycle: “generating → ready/failed. A later snapshot creates a separate report, not an overwritten PDF.”. Apply Report nullability rules from data-model.md. Coverage: FR-023.
- [ ] T076 [P] [US3] Implement metadata-only deletion request and app-managed snapshot mappings in `backend/src/verisource/db/models/deletion.py` with quoted fields/constraints; no cloud expiry/SLA or automatic live-case TTL; last_retry_at is nullable before retries. Depends on T070, T071, T072, T073, T074. DeletionRequest fields: “id, case_uuid, owner_id, accepted_at, state, active_purge_completed_at?, managed_snapshots_purged_at?, error_category?, last_retry_at?”. Constraints: “Tracking metadata only; no copied case content. Owner can poll after content is inaccessible. No cloud backup expiry promise.”. Lifecycle: “accepted → purging → completed after active files/rows/checkpoints/managed snapshots are verified purged; retries retain revoked access. Local ledger is outside content restoration.”. LocalSnapshot fields: “id, created_at, manifest_path, case_uuid_set, file_hash_manifest, deletion_sequence, state”. Constraints: “Explicit optional operator snapshot of local DB/files/checkpoints; default last3 only. Before deletion completion purge or invalidate every managed snapshot containing the case. Same-disk snapshot is not a disk-failure guarantee.”. Coverage: FR-031.
- [X] T077 [P] [US3] Implement append/fsync local deletion journal with verified sequence/generation replay in `backend/src/verisource/storage/deletion_ledger.py`, using quoted DeletionLedgerEntry shape/constraints; store outside snapshot restore, never duplicate owner identity/content, and fail closed if the required ledger cannot be reconciled. Depends on T070, T015, T071, T072, T073, T074. DeletionLedgerEntry fields: “sequence, random_case_uuid, write_generation, accepted_at, active_purge_completed_at?, managed_snapshots_purged_at?, reconciliation_state”. Constraints: “Append/fsync a local tombstone journal outside managed snapshot restore directories. No owner identity/input/evidence/title. Persist before completion, keep minimal entries to prevent stale restore resurrection.”. Coverage: FR-031, SC-013.
- [ ] T078 [US3] Register report/deletion/snapshot mappings and apply `backend/migrations/versions/0004_reports_deletion.py`; map journal entries to filesystem records rather than restoring them with case DB content, and verify all cross-case report references. Depends on T075, T076, T077.
- [X] T079 [US3] Implement same-case draft revision creation, checklist reconfirmation, prior history and explicit recheck semantics in `backend/src/verisource/domain/revisions.py`; copying confirmed values creates a draft, evidence reuse revalidates freshness/criteria and late prior-run completion remains historical. Depends on T078, T045, T046. Coverage: FR-004, FR-008, FR-020, FR-026, FR-029, SC-010.
- [X] T080 [US3] Implement explicit close-with-gaps/reopen behavior in `backend/src/verisource/domain/lifecycle.py` and revision/close/reopen routes in `backend/src/verisource/api/cases.py`; freeze chosen closed snapshot, cancel/fence pending work, preserve actual attempts and require owner action for later assessment. Depends on T079, T017, T062. Coverage: FR-020, FR-026, FR-028, FR-029, FR-030, SC-006, SC-010.
- [ ] T081 [US3] Implement authoritative case rehydration/startup recovery and pending-action reconstruction in `backend/src/verisource/operations/recovery.py`; reconcile canonical results versus separate graph checkpoint commits, reclaim leases without duplicate domain effects, and enforce deleted/closed generation checks before redispatch/final write. Depends on T080, T018, T048, T077. Coverage: FR-020, FR-026, FR-027, FR-029, FR-030, FR-031, SC-006, SC-010, SC-013.
- [ ] T082 [P] [US3] Implement private same-snapshot ReportLab PDF rendering with licensed bundled Unicode fonts in `backend/src/verisource/reports/pdf.py` and `backend/src/verisource/reports/fonts/`; include actual verdicts/subclaims/reasons/citations/attempts/dates/qualified and follow-up lists/gaps, explicit empty result and live/replay/cutoff labels; preserve snapshot hash/identity. Depends on T078, T062, T015. Coverage: FR-018, FR-021, FR-022, FR-023, FR-032, SC-005, SC-011.
- [ ] T083 [US3] Implement idempotent report generation jobs, ready/failed states and owner-checked metadata/content routes in `backend/src/verisource/reports/service.py` and `backend/src/verisource/api/reports.py`; never query mutable latest assessments during PDF generation, return409 before ready and use no-store attachment streaming with revocation checks. Depends on T082, T018, T017. Coverage: FR-023, FR-028, SC-005, SC-009, SC-011.
- [ ] T084 [P] [US3] Implement consistent explicit local snapshot creation, manifest hashes and last3 managed retention in `backend/src/verisource/operations/snapshots.py`; quiesce DB/checkpoint/file writes and distinguish optional backup rotation from live-case expiry, with no cloud service or disk-failure guarantee. Depends on T078, T077, T015. Coverage: FR-020, FR-031, FR-032, SC-013.
- [ ] T085 [US3] Implement owner DELETE admission and metadata-only deletion polling in `backend/src/verisource/domain/deletion.py` and `backend/src/verisource/api/deletions.py`; atomically increment generation/mark deleting, revoke all content/streams immediately, cancel jobs, append durable tombstone, return202 while purge pending and never claim completion early. Depends on T078, T077, T017, T081. Coverage: FR-028, FR-031, SC-009, SC-013.
- [ ] T086 [US3] Implement restart-safe purge/retry in `backend/src/verisource/operations/purge.py`; quiesce/fence in-flight writes and remove case rows/checkpoints/temp/files/orphans plus every affected managed snapshot before completion, preserving other cases and independent public-source corpus; a stopped laptop cannot claim purge done. Depends on T085, T084, T083. Physically remove each affected managed snapshot, or verify a sanitized reconstruction and physically remove its original before completion. Metadata invalidation alone is insufficient; inspect actual DB dumps, checkpoint copies, blobs and temporary archives for residual private content. Preserve other cases in active storage and independently acquired public corpus. Coverage: FR-020, FR-028, FR-031, SC-006, SC-009, SC-013.
- [ ] T087 [US3] Implement isolated offline restore and current-ledger reconciliation in `backend/src/verisource/operations/restore.py`; reject missing/inconsistent tombstones, purge restored deleted content/jobs before app access, verify hashes and preserve current unaffected cases rather than operating on the live developer DB during drills. Depends on T084, T086, T081. Offline restore must remove all restored login sessions and pre-auth bootstrap state before traffic/workers and require fresh sign-in. Old cookies and CSRF tokens must fail, including sessions logged out or expired after snapshot capture; fresh owner login must succeed. Coverage: FR-020, FR-031, SC-006, SC-013.
- [ ] T088 [US3] Wire `snapshot-local --retain 3`, `restore-drill --offline --output ...` and purge status into `backend/src/verisource/operations/cli.py`; report actual consistent snapshot/restore outcomes and managed-copy limits without claiming erase of arbitrary user-made copies or forensic SSD contents. Depends on T087, T069. Coverage: FR-031, FR-032, SC-013.
- [ ] T089 [US3] Implement owner case re-entry/reconnect, revision/checklist/assessment history, actual requirement edits and explicit close/reopen in `frontend/src/features/cases/CaseHistory.tsx`; reconfirm changed fields, keep older results visibly historical, and preserve pending uploaded-document actions after browser/service restart. Depends on T080, T081, T067. Coverage: FR-002, FR-020, FR-026, FR-029, FR-030, SC-006, SC-010.
- [ ] T090 [US3] Implement snapshot-bound export request/progress/ready/error controls and authenticated downloads in `frontend/src/components/ReportExport.tsx`; keep selected revision/snapshot stable and allow exports with explicit gaps without outreach. Depends on T083, T089. Coverage: FR-002, FR-023, FR-028, SC-005, SC-009, SC-011.
- [ ] T091 [US3] Implement explicit owner deletion and metadata-only local purge tracking in `frontend/src/components/DeleteCase.tsx`; explain retention until deletion, clear local private cache/streams immediately, show pending/retrying/completed accurately and disclose unmanaged copies without cloud-expiry promises. Depends on T086, T089. Coverage: FR-028, FR-031, SC-009, SC-013.
- [ ] T092 [US3] Run resume/revise/report/close/delete/offline-restore journeys in `tests/e2e/resume_report_delete.spec.ts` and `backend/tests/acceptance/test_us3_lifecycle.py`; render every actual PDF page to `.local/acceptance/core002/pdf-pages/`, inspect/fix clipping and verify snapshot content/ownership, recording real results/data gaps under `.local/acceptance/core002/us3/`. Depends on T071, T072, T073, T074, T090, T091, T088. Coverage: FR-020, FR-023, FR-026, FR-028, FR-029, FR-030, FR-031, SC-005, SC-006, SC-009, SC-010, SC-011, SC-013.

**Checkpoint**: All three story behaviors integrate; final real-data measurements/security/readiness still require Phase6.

## Phase 6: Polish & Cross-Cutting Validation

**Goal**: Verify the complete feature against real records, exact source coverage, local resources and the constitution, then document actual readiness.

**Completion criterion**: Run commands and checks after the stories integrate. A missing real source, document class, independent label or measurement is an explicit unmet validation prerequisite; leave its validation unchecked and do not declare acceptance based on a report merely listing the gap.

- [ ] T093 [P] Verify the complete two-owner/signed-out/privacy and egress/CSRF/path/injection matrix in `backend/tests/integration/test_security_boundaries.py`; cover every final nested/content/stream route, logout/expiry and deletion races using genuine records with clearly labeled attack/control conditions, not fabricated official evidence. Depends on T092. Cover restored-cookie/CSRF rejection and fresh-login owner isolation. Coverage: FR-014, FR-018, FR-028, FR-031, FR-032, SC-005, SC-009, SC-013, SC-014.
- [ ] T094 [P] Validate all shared country/extension envelopes with attributable real India/second-jurisdiction records in `backend/tests/contract/test_country_boundary.py`; confirm unsupported coverage and shared policy/storage invariants, with no synthetic pack, actual008 implementation, outreach send or003 discovery. Depends on T092. Coverage: FR-024, FR-025, FR-026, SC-008.
- [ ] T095 [P] Implement and run the real-manifest `benchmark-model` workflow in `backend/src/verisource/operations/model_benchmark.py`; use actual allowed source excerpts/pages and human-checked fields, record installed digest/cold-load/context/RAM/VRAM/latency/errors under `.local/acceptance/model/`, and make no quality claim from synthetic prompts or file size. Depends on T092, T068. Coverage: FR-010, FR-032, SC-014.
- [ ] T096 [P] Implement local five-real-supplier report latency and full30-supplier active-buyer-time measurement in `backend/src/verisource/operations/benchmark.py`; include queue/retries/model/report time, explicitly separate actual excluded waits/live versus real replay/larger lists, and record host/pages/tokens/free quotas and SC-001/003/004 results without inventing a manual baseline. Depends on T092. Use the same 30 real suppliers across six five-supplier cases as SC-002. Record active intervals for intake, corrections, confirmations, evidence review and decision/report actions; divide shared case time equally across evaluated suppliers and never double-count overlapping intervals. Report all 30 per-supplier totals and the maximum; every total must be under one hour. Separately record unattended collection and excluded actual waits. Missing any supplier timing leaves SC-003 unmeasured; a five-supplier timing run or average alone cannot pass it. The estimated manual baseline remains unverified. Coverage: FR-020, FR-030, FR-032, SC-001, SC-003, SC-004, SC-014.
- [ ] T097 [P] Acquire/validate the30-real-supplier evaluation and independent human-auditor labels through `tests/records/audit-manifest.schema.json` and `.local/records/audit/`; cover all standard claims/three verdicts and real warning families, preserve source/cutoff/rights and label disagreement, and explicitly leave missing records/labels/classes unverified rather than auto-label or synthesize them. Depends on T092, T068. Require observed per-supplier active-time intervals for the same30 suppliers and expose missing timing independently of auditor labels. Coverage: FR-017, FR-018, FR-025, FR-026, FR-032, SC-002, SC-003, SC-007.
- [ ] T098 [P] Run keyboard/focus/table-header/contrast/non-color-state checks across supported browsers and responsive layouts in `tests/e2e/accessibility.spec.ts` and `frontend/src/app/styles.css`; use actual records for empty/loading/error/progress/history/delete screens and fix only observed UI issues against the conversation contract. Depends on T092. Coverage: FR-001, FR-002, FR-021, FR-023, FR-028, SC-004, SC-005, SC-009, SC-011.
- [ ] T099 [P] Provide tested native-local startup/stop/preflight instructions and maintained PowerShell launch helper in `scripts/start-local.ps1` and `README.md`; preserve optional Postgres-only Docker, loopback binding, secure secret prompts/data exclusions, no paid/S3/hosting setup and no seeded demo command. Depends on T092. Coverage: FR-020, FR-028, FR-032, FR-033, SC-014.
- [ ] T100 Wire `benchmark-model` and five-supplier `benchmark` into `backend/src/verisource/operations/cli.py` and verify every command declared by `specs/002-supplier-verification-core/quickstart.md` resolves with honest unavailable/missing-input statuses and no model download or paid fallback. Depends on T095, T096, T088. Coverage: FR-032, SC-001, SC-003, SC-014.
- [ ] T101 Run actual complete local tests/build/e2e, live supplier+official-source retrieval/import and available auditor evaluation; write the dated coverage/status report to `specs/002-supplier-verification-core/acceptance-report.md` with protected raw results in `.local/acceptance/core002/`; distinguish passed/failed/missing-real-data/unmeasured/live/replay/controlled conditions for every SC and never check unperformed acceptance as passed. Depends on T093, T094, T100, T097, T098, T099. Coverage: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008, FR-009, FR-010, FR-011, FR-012, FR-013, FR-014, FR-015, FR-016, FR-017, FR-018, FR-019, FR-020, FR-021, FR-022, FR-023, FR-024, FR-025, FR-026, FR-027, FR-028, FR-029, FR-030, FR-031, FR-032, FR-033, SC-001, SC-002, SC-003, SC-004, SC-005, SC-006, SC-007, SC-008, SC-009, SC-010, SC-011, SC-012, SC-013, SC-014.
- [ ] T102 Reconcile actual implementation paths/commands/constraints and measured limitations in `specs/002-supplier-verification-core/quickstart.md`, `specs/002-supplier-verification-core/plan.md` and `specs/README.md`; preserve frozen001, report constitutional compliance and leave unmet real-source/model/auditor criteria visible before declaring002 implemented. Depends on T101. Coverage: FR-032, SC-001, SC-002, SC-003, SC-004, SC-005, SC-006, SC-007, SC-008, SC-009, SC-010, SC-011, SC-012, SC-013, SC-014.

**Checkpoint**: Acceptance report records actual executed results and remaining failures/data gaps. Only verified required outcomes justify declaring002 complete.

## Dependencies & Execution Order

### Phase and story graph

```text
Phase1 Setup (T001–T007)
  -> Phase2 Foundation (T008–T020)
      -> US1 / P1 (T021–T053)
          -> US2 / P2 (T054–T070)
              -> US3 / P3 (T071–T092)
                  -> Phase6 validation (T093–T102)
```

Stories are separate testable increments with real data, but their implementation dependencies are deliberate: US2 consumes US1 evidence; US3 consumes both durable US1 state and US2 snapshots. Do not claim all stories can start independently after foundation. Their independent tests isolate each increment once predecessors exist, without discovery/outreach or fabricated input.

Within each phase follow listed dependencies: tests before covered behavior; models before integration migrations; permission/storage/quota checks before collection; confirmed criteria and actual evidence before publication; immutable snapshot before report/decision; deletion fencing/ledger before purge; current-ledger reconciliation before restored traffic.

Migrations, mapping registration, shared CLI routing and case lifecycle files are serialized. The foundational migration can defer only pointers to tables introduced later; the owning story migration must install those forward foreign keys before its routes become usable.

### Implementation task dependency index

| Task | Required earlier tasks |
|---|---|
| T001 | Phase barrier / no additional task dependency |
| T002 | Phase barrier / no additional task dependency |
| T003 | Phase barrier / no additional task dependency |
| T004 | T001 |
| T005 | T001 |
| T006 | T001 |
| T007 | T006 |
| T008 | T001, T003, T004 |
| T009 | T008 |
| T010 | T008 |
| T011 | T008 |
| T012 | T009, T010, T011 |
| T013 | T008, T004 |
| T014 | T012, T013, T007 |
| T015 | T004 |
| T016 | T014, T009, T013 |
| T017 | T016, T010 |
| T018 | T012, T013 |
| T019 | T002, T013 |
| T020 | T016, T015, T018 |
| T021 | T020, T017, T019, T007 |
| T022 | T020, T017, T019, T007 |
| T023 | T020, T021, T022 |
| T024 | T020, T021, T022 |
| T025 | T020, T021, T022 |
| T026 | T020, T021, T022 |
| T027 | T020, T021, T022 |
| T028 | T020, T021, T022 |
| T029 | T020, T021, T022 |
| T030 | T023, T024, T025, T026, T027, T028, T029 |
| T031 | T030, T015, T006 |
| T032 | T030, T017 |
| T033 | T030 |
| T034 | T030, T013 |
| T035 | T030, T004 |
| T036 | T030, T004, T035 |
| T037 | T030 |
| T038 | T031, T028, T015 |
| T039 | T034, T037, T031 |
| T040 | T026, T015, T035, T017 |
| T041 | T039, T033 |
| T042 | T038, T039, T033 |
| T043 | T038, T039, T033 |
| T044 | T030, T033 |
| T045 | T032, T035, T036, T024 |
| T046 | T027, T044, T045 |
| T047 | T018, T045, T046, T039, T040, T041, T042, T043, T037 |
| T048 | T047, T029, T040, T044 |
| T049 | T047, T017, T011, T023 |
| T050 | T031, T038, T035, T036, T043 |
| T051 | T032, T045, T019 |
| T052 | T049, T048, T051 |
| T053 | T021, T022, T047, T048, T052, T050 |
| T054 | T053 |
| T055 | T053 |
| T056 | T053 |
| T057 | T053, T054, T055, T056 |
| T058 | T057 |
| T059 | T058, T017 |
| T060 | T058, T046 |
| T061 | T058, T044, T059 |
| T062 | T060, T059, T058 |
| T063 | T062, T017 |
| T064 | T062, T061, T047, T049 |
| T065 | T059, T063, T056 |
| T066 | T065, T063 |
| T067 | T066, T064 |
| T068 | T062, T031 |
| T069 | T068, T050 |
| T070 | T054, T055, T067, T069 |
| T071 | T070 |
| T072 | T070 |
| T073 | T070 |
| T074 | T070 |
| T075 | T070, T071, T072, T073, T074 |
| T076 | T070, T071, T072, T073, T074 |
| T077 | T070, T015, T071, T072, T073, T074 |
| T078 | T075, T076, T077 |
| T079 | T078, T045, T046 |
| T080 | T079, T017, T062 |
| T081 | T080, T018, T048, T077 |
| T082 | T078, T062, T015 |
| T083 | T082, T018, T017 |
| T084 | T078, T077, T015 |
| T085 | T078, T077, T017, T081 |
| T086 | T085, T084, T083 |
| T087 | T084, T086, T081 |
| T088 | T087, T069 |
| T089 | T080, T081, T067 |
| T090 | T083, T089 |
| T091 | T086, T089 |
| T092 | T071, T072, T073, T074, T090, T091, T088 |
| T093 | T092 |
| T094 | T092 |
| T095 | T092, T068 |
| T096 | T092 |
| T097 | T092, T068 |
| T098 | T092 |
| T099 | T092 |
| T100 | T095, T096, T088 |
| T101 | T093, T094, T100, T097, T098, T099 |
| T102 | T101 |

## Parallel Execution Examples

Examples are optional future developer scheduling; no agents or implementation were launched by this generation pass. Use two members on disjoint files after the named gate; integrate each slice before moving on.

### User Story 1

- After foundation, write T021 and T022 concurrently against the genuine acquired corpus.
- After foundation and the US1 test-definition tasks, model files T023, T024, T025, T026, T027, T028 and T029 can be divided across developers, then serialize T030.
- After the source contracts/migration, one developer handles egress/source collection while the other handles local extraction; optional free-Gemini routing waits for the shared local schema (T035 before T036).

### User Story 2

- After US1 checkpoint, write T054, T055 and T056 in separate test files.
- After T058, T059 and T060 are independent service files. Snapshot assembly waits for both.
- After their APIs exist, divide matrix inspection from evaluation tooling (T065 and T068); do not race shared CLI registration.

### User Story 3

- After US2 checkpoint, T071, T072, T073 and T074 can be written independently.
- Model/journal outputs T075, T076 and T077 are disjoint; serialize T078 after all three.
- After migration, T082 and T084 can progress independently; purge waits for the deletion fence and snapshot handling, and restore waits for purge.

## Requirement and Acceptance Traceability

This table names specific implementation/validation tasks rather than counting a final catch-all report as coverage.

| Requirement | Owning tasks |
|---|---|
| FR-001 | T002, T013, T019, T021, T023, T032, T049, T051, T053, T098 |
| FR-002 | T002, T021, T023, T049, T051, T052, T053, T056, T065, T066, T070, T089, T090, T098 |
| FR-003 | T010, T021, T032, T035, T036, T051, T053 |
| FR-004 | T010, T017, T021, T023, T032, T045, T051, T053, T079 |
| FR-005 | T010, T021, T032, T039, T051, T053 |
| FR-006 | T010, T021, T032, T051, T053 |
| FR-007 | T021, T024, T035, T036, T045, T051, T053 |
| FR-008 | T017, T021, T024, T045, T047, T051, T053, T079 |
| FR-009 | T007, T022, T026, T031, T034, T037, T039, T047, T053 |
| FR-010 | T007, T015, T022, T026, T035, T036, T040, T047, T053, T095 |
| FR-011 | T007, T022, T025, T041, T047, T053 |
| FR-012 | T007, T022, T025, T028, T038, T042, T047, T053 |
| FR-013 | T007, T022, T028, T038, T043, T047, T053 |
| FR-014 | T022, T025, T029, T034, T037, T039, T042, T047, T048, T052, T053, T093 |
| FR-015 | T010, T044, T053, T055, T059, T065, T070 |
| FR-016 | T010, T044, T053, T055, T059, T065, T070 |
| FR-017 | T024, T027, T041, T045, T046, T053, T054, T055, T060, T062, T065, T068, T070, T097 |
| FR-018 | T006, T015, T026, T027, T031, T034, T035, T040, T041, T046, T049, T052, T053, T054, T055, T056, T059, T062, T065, T068, T070, T073, T082, T093, T097 |
| FR-019 | T027, T044, T046, T053, T054, T055, T056, T059, T061, T062, T064, T065, T067, T070 |
| FR-020 | T003, T010, T011, T015, T017, T018, T020, T029, T047, T048, T049, T064, T071, T072, T074, T079, T080, T081, T084, T086, T087, T089, T092, T096, T099 |
| FR-021 | T054, T056, T057, T059, T062, T063, T064, T065, T067, T070, T073, T082, T098 |
| FR-022 | T054, T055, T056, T057, T060, T062, T063, T064, T066, T067, T070, T073, T082 |
| FR-023 | T015, T073, T075, T082, T083, T090, T092, T098 |
| FR-024 | T025, T033, T053, T094 |
| FR-025 | T028, T033, T038, T041, T042, T043, T044, T053, T061, T094, T097 |
| FR-026 | T024, T027, T045, T046, T047, T053, T054, T055, T057, T060, T062, T064, T067, T068, T070, T071, T072, T079, T080, T081, T089, T092, T094, T097 |
| FR-027 | T006, T011, T018, T022, T025, T026, T027, T031, T037, T039, T047, T052, T053, T059, T072, T081 |
| FR-028 | T004, T009, T010, T013, T014, T015, T016, T017, T019, T020, T021, T026, T032, T040, T049, T053, T054, T059, T063, T070, T071, T073, T074, T080, T083, T085, T086, T090, T091, T092, T093, T098, T099 |
| FR-029 | T010, T017, T024, T071, T072, T079, T080, T081, T089, T092 |
| FR-030 | T011, T018, T022, T029, T037, T047, T048, T049, T052, T053, T064, T072, T080, T081, T089, T092, T096 |
| FR-031 | T004, T015, T017, T018, T020, T074, T076, T077, T081, T084, T085, T086, T087, T088, T091, T092, T093 |
| FR-032 | T001, T002, T003, T004, T005, T006, T007, T015, T020, T022, T025, T026, T031, T034, T035, T036, T037, T050, T053, T068, T069, T082, T084, T088, T093, T095, T096, T097, T099, T100, T102 |
| FR-033 | T006, T007, T022, T028, T031, T038, T042, T043, T050, T053, T099 |

| Success criterion | Implementation / measurement tasks |
|---|---|
| SC-001 | T037, T047, T064, T096, T100 |
| SC-002 | T007, T046, T055, T068, T069, T097 |
| SC-003 | T068, T069, T096, T097, T100 |
| SC-004 | T021, T032, T051, T053, T096, T098 |
| SC-005 | T006, T022, T027, T031, T035, T040, T041, T043, T044, T046, T047, T053, T054, T055, T056, T059, T062, T064, T065, T067, T068, T070, T073, T082, T083, T090, T092, T093, T098 |
| SC-006 | T018, T022, T047, T048, T049, T053, T071, T072, T074, T080, T081, T086, T087, T089, T092 |
| SC-007 | T007, T044, T055, T061, T068, T070, T097 |
| SC-008 | T033, T094 |
| SC-009 | T014, T016, T017, T019, T021, T032, T049, T054, T059, T063, T070, T071, T073, T074, T083, T085, T086, T090, T091, T092, T093, T098 |
| SC-010 | T017, T071, T072, T079, T080, T081, T089, T092 |
| SC-011 | T054, T055, T056, T060, T062, T063, T066, T067, T068, T070, T073, T082, T083, T090, T092, T098 |
| SC-012 | T022, T034, T037, T039, T040, T041, T042, T047, T048, T049, T052, T053, T064, T072 |
| SC-013 | T074, T077, T081, T084, T085, T086, T087, T088, T091, T092, T093 |
| SC-014 | T006, T007, T020, T022, T031, T035, T036, T037, T038, T039, T041, T042, T043, T050, T052, T053, T068, T069, T093, T095, T096, T099, T100 |

## Implementation Strategy

### MVP first

Complete setup, foundation and US1: actual buyer requirements/known suppliers -> correction and explicit confirmation -> confirmed proof checklist -> unattended eligible collection/local export lookup -> genuine evidence/attempt-backed initial assessments. Review this working local increment before expanding the interface. MVP includes owner isolation, conservative proof, durable work and zero paid-service prerequisites; it does not imply the full report/lifecycle feature or30-supplier auditor criterion has passed.

### Incremental delivery

Add US2's expandable immutable evidence comparison and qualified/follow-up lists with explicit buyer choice. Then add US3's history/revision/resume/export/retention/delete/restore journeys. Run the final security, real-record model/timing and independent human audit checks. Larger lists stay in the same case with queued batches; no benchmark claim extends beyond measured workload.

### Real-data and acceptance gates

Minimum real-source acquisition is required for meaningful behavioral checks. Some specialist natural cases (locked PDFs, qualifying contradictions, warning patterns, cross-country records) or independent auditor labels may remain unavailable. Record those dependencies, continue unrelated buildable tasks and leave their required validation unverified. Never create a fake record, silently skip it as a pass or declare the whole feature accepted from partial output.

The exact local CLI commands are in [quickstart.md](quickstart.md). Acquire source policy and actual data before external collection; neither API purchases nor hosting are prerequisites. The requested policy is a functional boundary, not a temporary demo mode.

## Completion Summary

| Scope | Tasks |
|---|---|
| Phase1 | 7 |
| Phase2 | 13 |
| Phase3 / US1 | 33 |
| Phase4 / US2 | 17 |
| Phase5 / US3 | 22 |
| Phase6 | 10 |
| Total | 102 |
| Marked parallel | 59 |

T001–T020 are complete (20/102); T012 now passes. US1 starts at T021 and82 tasks remain unchecked. The2026-10-19 `$speckit-analyze` review found47/47 requirements covered and no remaining critical issues; implementation has started. See implementation-progress.md for executed checks and outstanding prerequisites. Task completion and recorded source/test evidence must stay consistent; source access and acceptance targets are not claims of implemented behavior.

