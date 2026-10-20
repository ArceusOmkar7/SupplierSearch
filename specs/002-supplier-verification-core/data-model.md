# Data Model: Supplier Verification Core

**Date**: 2026-10-17 | **Authority**: [spec.md](spec.md) | **Design**: [plan.md](plan.md)

This is a logical schema for migrations in the implementation phase. UUID primary keys, UTC instants, explicit foreign keys and schema-versioned structured fields are the defaults. User-facing times may be localized. Original source values remain alongside normalization. Every private child row carries `case_id`; composite foreign keys prevent links across cases. Ownership is derived from the case, never accepted from an API body.

## Nullability and lifecycle constraints

`?` means database NULL and explicit JSON null are permitted; it does not permit invented timestamps, actors, pointers or hashes. Unmarked fields are required. Empty reference collections use empty arrays, not null. State-dependent constraints apply on each transaction:

- Session.revoked_at is null until revocation. Restore removes all restored sessions and pre-auth bootstrap state before traffic; no saved cookie or CSRF token survives restore, even if logout/revocation happened after snapshot capture. Require fresh sign-in, including for deletion-status polling.
- Case.active_revision_id and latest_snapshot_id are null until confirmation/publication. closed_at is set only while closed and cleared on explicit reopen; deleting_at is null until deletion admission. Prior closure remains in events/history.
- RequirementRevision and ChecklistVersion confirmed_at/confirmed_by are both null in drafts and both required when confirmed. No placeholder buyer or time is stored.
- VerificationRun.started_at is null while queued; initial_deadline is computed at admission, not null. completed_at is null until a terminal state. CheckAttempt.finished_at/outcome are required because attempts are persisted on completion; in-flight dispatch intent lives in durable work.
- Report.content_hash, artifact_id and generated_at are null until ready, when all three are required and bind the immutable rendered bytes. error is null except on failure; generating/failed reports cannot expose a ready download. Report starts in generating when its request is accepted; requested describes the command, not a separate persisted state.
- DeletionRequest.last_retry_at is null before a retry. Completion timestamps remain null until verified active and managed-snapshot content purge respectively. No snapshot containing deleted content may remain merely marked invalid.

Migrations and API schemas must enforce these rules; contract/integration tests exercise valid drafts, transitions and rejected impossible states.

## Identity and case aggregate

| Entity | Principal fields | Constraints / relationships |
|---|---|---|
| BuyerAccount | id, username_normalized, password_hash, display_name, created_at, disabled_at? | Unique normalized username; maintained pwdlib Argon2 hash, operator-provisioned local accounts. No external identity server, teams or public registration. |
| Session | id_hash, buyer_id, created_at, last_seen_at, expires_at, revoked_at?, csrf_secret | Raw cookie is opaque/random; store only its hash. Absolute8h/idle30min; explicit logout revokes. No cloud refresh credentials. |
| Case | id, owner_id, title, state, active_revision_id?, latest_snapshot_id?, version, write_generation, created_at, closed_at?, deleting_at? | Owner immutable. Version for optimistic commands; generation fences workers. No TTL. |
| RequirementRevision | id, case_id, sequence, status, requirements_json, location_json, supplier_set_json, input_provenance, confirmed_at?, confirmed_by?, created_at | Unique case+sequence. Draft editable; confirmed payload immutable. One active draft per case. Supplier set freezes the identifiers selected for that revision. |
| ConversationMessage | id, case_id, revision_id?, actor, text, component_refs, sequence, created_at | Monotonic case sequence. Model text cannot enact confirmations/approvals. Private content purged with case. |
| Supplier | id, case_id, display_name, original_identifiers, normalized_identifiers, source_refs, created_at | Case-local entity, not a global discovery index. Same-name/GST conflicts do not silently merge. |
| SupplierSite | id, case_id, supplier_id, raw_address, normalized_address, role, jurisdiction, identity_state, evidence_refs | Role: registered_office/production_site/other/unknown. Keep office/factory distinctions and originals. |
| IdentityResolution | id, case_id, revision_id, supplier_id, candidate_record_ref, identifier_matches, discrepancies, proposed_score?, state, resolution_basis, resolved_by?, resolved_at? | proposed/confirmed/ambiguous/rejected. A fuzzy score cannot confirm identity. A buyer-confirmed candidate remains subject to substantive proof criteria. |

`requirements_json` includes part description, materials, processes, quantity+unit+period, required certifications, optional tolerance/standard fields, missing-field markers and field provenance. Missing values remain null/unknown; no default inferred capability. Quantity must be positive when supplied, and radius includes unit/reference location. Confirmed fields must satisfy the buyer's stated required input. Unsupported countries are explicit coverage states, not silently mapped to India.

Supplier identifiers are typed: name, website, GSTIN, Udyam URN, CIN/LLPIN, certificate number or pasted listing URL. Syntax checks reject malformed identifiers without inferring nonexistence. IndiaMART links remain opaque identifier text and cannot seed collection. Additional supplier/site associations do not change the frozen supplier set of an earlier revision.

## Claims, runs and assessments

| Entity | Principal fields | Constraints / relationships |
|---|---|---|
| ChecklistVersion | id, case_id, revision_id, sequence, status, confirmed_by?, confirmed_at?, policy_version | Draft/editable then confirmed/immutable. Edits after confirmation create another version, preserving old criteria. |
| Claim | id, case_id, revision_id, checklist_id, supplier_id, site_id?, parent_claim_id?, type, assertion, relevant_period, required_for_shortlist, proof_criteria_json, processing_state | Every confirmed claim has explicit criteria/entity/site/period. Parent and children share supplier/revision/checklist. No cycles. Required parent uses the same compound rules. |
| VerificationRun | id, case_id, revision_id, checklist_id, policy_version, country_pack_version, mode, state, requested_at, started_at?, initial_deadline, completed_at?, budgets_json, generation, idempotency_key | Confirmed revision/checklist only. Live retrieval versus genuine-record replay is immutable/visible, with imported-source dates preserved. No synthetic/demo mode. New runs preserve history. |
| CheckTask | id, case_id, run_id, supplier_id, claim_ids, source_id, check_type, dependency_ids, state, operation_key, due_at, deadline_at, wait_action_id? | Durable independent units. No cyclic dependencies; old-revision tasks cannot write new-revision results. At most one active operation key. |
| Assessment | id, case_id, run_id, revision_id, checklist_id, claim_id, sequence, verdict, reasoning, criterion_results, evidence_refs, attempt_refs, gaps, policy_version, created_at | Append-only; verdict exactly proven/unproven/contradicted. Assessment references must match case/supplier/assertion/site/period. Prior assessments remain inspectable. |
| AssessmentSnapshot | id, case_id, run_id, revision_id, checklist_id, event_cutoff, assessment_ids, supplier_processing_states, pending_action_refs, coverage_summary, qualified_ids, follow_up_ids, excluded_reasons, created_at, content_hash | Immutable materialization of report/table content. Lists derived under the same policy. Snapshot can be partial but every included evaluated claim has a verdict and truthful references. |
| SupplierDecision | id, case_id, snapshot_id, supplier_id?, decision, buyer_id, reason?, created_at | select/reject/no_selection, explicit buyer command. Does not rewrite verdicts or represent automatic supplier approval. |

Proof criteria are structured: criterion ID, assertion/subclaim, required evidence class, authority, independent corroboration, identity/site/period constraints and explicit missing-evidence condition. `criterion_results` records satisfied/refuted/insufficient plus actual references and reasoning. Semantic extraction proposals are not trusted just because their JSON is valid; shared policy validates admissibility and abstains when ambiguous.

Required-for-shortlist flags are buyer confirmed. At least one required claim must be selected before run admission, avoiding vacuous qualification. A compound claim is proven only when all required subclaims are proven; direct qualifying refutation of a required subclaim yields contradicted; otherwise unproven. A supplier is qualified only if every buyer-required claim is proven. Unproven required claims with no contradicted required claim form a separate follow-up candidate. Contradicted required claims exclude both lists but remain in the matrix. Optional claim outcomes remain visible.

## Sources, attempts and artifacts

| Entity | Principal fields | Constraints / relationships |
|---|---|---|
| SourceDefinition | id, version, provider_family, jurisdiction, claim_coverage, allowed_queries/hosts, access_mode, authority_roles, policy_checked_at, policy_refs, terms_version, capabilities | Global non-case configuration; immutable version per run. No secret values. API/public-page/official-document/issuer adapter capabilities are distinct. |
| ProviderAccount | id, provider, secret_ref?, mode, enabled_capabilities, policy_refs, allowed_data_classes, quota_window?, limits?, verified_at | Optional free Gemini/project configuration, not required for local inference or public sources. Paid mode disabled; no mandatory premium provider setup. Never infer unlimited free quota. |
| SourceAuthorization | id, case_id, supplier_id, provider_account_id, basis, authorization_evidence_ref, scope, effective_at, expires_at?, verified_by | Required only where the provider requires it. Missing basis means consent_missing; it does not generate a buyer scraping task. |
| BudgetReservation | id, provider_account_id?, run_id, case_id, consumer, unit, reserved_amount, settled_amount?, cycle?, state, operation_key, expires_at | Free request/token/concurrency quota reservations; global zero paid-spend policy. No tariff/account prerequisite for free pages or local files. Future features share actual project quota. |
| CheckAttempt | id, case_id, run_id, task_id, revision_id, supplier_id, claim_ids, source_version, kind, target, requested_at, started_at?, finished_at, request_dispatched, outcome, reason_code, http_status?, provider_request_id?, artifact_refs, retry_of?, operation_key | Kind capability_check/remote_request/document_read/deadline_check. A local skip cannot claim a network dispatch. No-content attempts have no evidence excerpt. Preserve each actual retry and uncertain outcome. |
| DocumentArtifact | id, case_id, revision_id?, supplier_id?, origin, storage_key, sha256, media_type, byte_count, page_count?, collected_at, source_url?, source_attempt_id?, state | Origin buyer_upload/source_fetch/source_import/generated_report. Generated case/UUID relative file keys under private app root; no client-supplied paths, traversal/junction escapes or frontend-static files. Atomic writes; preserve actual original file. Limits20MiB/50 PDF pages. Unsafe files quarantined. |
| Extraction | id, case_id, artifact_id, page_refs, method, fields, missing_fields, uncertainties, model_id?, prompt/schema_version, created_at, content_hash | Text/OCR/model mapping remains distinct from original artifact. Missing dates/fields remain unknown; extracted certificates are not proof by themselves. |
| EvidenceRecord | id, case_id, run_id, supplier_id, site_id?, assertion_tags, source_version, source_url/document_ref, observation, page/locator, collected_at, issued_at?, expires_at?, effective_at?, origin_lineage, self_reported, authority_role, identity_resolution_id, artifact_id?, content_hash | Must reference content actually retrieved/read. Repeated copies share lineage and cannot count as independent corroboration. No attempt outcome is disguised as evidence. |
| EvidenceUse | id, case_id, assessment_id, evidence_id, criterion_id, role, period_fit, freshness_check_ref | supporting/refuting/context. Reuse requires current criterion/identity/freshness validation; no cross-case links. |
| QcoRecord | id, source_document_id, order_number, standard_codes, product_scope, exclusions, issued/effective/amended_dates, supersedes_ref?, coverage_state, extracted_basis | Versioned official-source observations. A stale/incomplete corpus or absent search hit cannot establish non-applicability. |
| SourceDataset | id, source_version, publisher, original_url, licence/attribution, obtained_at, publication/cutoff, coverage, local_storage_key, sha256, format, schema/import_version, state | Actual legitimately acquired public/authorized CSV/XLSX/PDF/HTML. Global operator-only known-supplier source corpus, not a discovery index. Preserve original bytes and access restrictions; no demo rows. |
| SourceDatasetRecord | id, dataset_id, original_row/page_locator, normalized_identifiers, selected_business_fields, origin_hash | Actual imported record linked to original row/page. Original cutoff governs historical claims; import date cannot refresh status. Exclude unnecessary personal fields from buyer views/free inference. Case EvidenceRecords reference attributed captured copies of actual selected records. |

Source configuration and real import corpus are operator-level; case-linked observations/evidence remain private. Store optional API keys in ignored protected local configuration, never payloads/file names/logs. Free sources require no paid tariff/credential; source reuse policy must support retained case evidence. Actual bulk files/rows are never replaced by synthetic records. A buyer cannot download a global source corpus through a case reference. Deleting one case removes its copies/history, not independently acquired public corpus files or another case's evidence.

Attempt outcomes: success, no_record, blocked, unavailable, timeout, transient_error, invalid_input, uncertain_outcome, skipped. Reasons distinguish not_configured, permission_unverified, consent_missing, budget_exhausted, quota_exhausted, not_supported, missing_identifier, captcha, locked_document, unsupported_language, too_large, malformed_document and deadline. `no_record` is not a contradiction. `request_dispatched=false` and a capability/deadline explanation must remain visible for work never sent externally.

## Durable jobs, events and human actions

| Entity | Principal fields | Constraints / relationships |
|---|---|---|
| HumanAction | id, case_id, revision_id, run_id, affected_task_ids, type, requested_document_ref?, state, created_at, resolved_at?, resolution_ref? | Core type supply_unlocked_document/resolve_identity. No manual portal/CAPTCHA/scraping task. Only dependent tasks wait. |
| WorkItem | id, case_id, run_id?, task_id?, kind, state, operation_key, lease_owner?, lease_expires_at?, heartbeat_at?, fence, attempts, due_at, payload_refs | Queued/leased/retry_wait/succeeded/failed/cancelled. Use SKIP LOCKED, lease60s, heartbeat15s, recovery scan30s; recheck generation at commit. Payload holds IDs, not copies of documents. |
| CaseEvent | id, case_id, sequence, type, revision_id?, run_id?, object_refs, public_payload, created_at, operation_key | Unique case+sequence and operation key. Durable SSE reconnect cursor. Owner-authorized and no-store; purged with case. |
| GraphCheckpoint | thread_id, checkpoint_id, checkpoint_namespace, case_id mapping, run_id mapping, state_refs, created_at | Library-managed schema plus app mapping. Thread unique per case/revision/run. Sync durability; records remain canonical across replay. |
| Report | id, case_id, revision_id, snapshot_id, state, artifact_id?, content_hash?, generated_at?, error? | Generating/ready/failed. Unique snapshot+renderer_version for retry reuse. PDF and JSON table derive from the same snapshot. |

Confirm/start commands commit domain changes, event and work intent in one Postgres transaction. Worker/provider calls occur outside that transaction. Domain result commits precede acknowledging work; checkpoint replay first checks stable operation keys. Source retries may repeat a real external read; no exactly-once network/billing claim. Concurrent jobs use separate database sessions.

## Retention and deletion

| Entity | Principal fields | Constraints / relationships |
|---|---|---|
| DeletionRequest | id, case_uuid, owner_id, accepted_at, state, active_purge_completed_at?, managed_snapshots_purged_at?, error_category?, last_retry_at? | Tracking metadata only; no copied case content. Owner can poll after content is inaccessible. No cloud backup expiry promise. |
| DeletionLedgerEntry | sequence, random_case_uuid, write_generation, accepted_at, active_purge_completed_at?, managed_snapshots_purged_at?, reconciliation_state | Append/fsync a local tombstone journal outside managed snapshot restore directories. No owner identity/input/evidence/title. Persist before completion, keep minimal entries to prevent stale restore resurrection. |
| LocalSnapshot | id, created_at, manifest_path, case_uuid_set, file_hash_manifest, deletion_sequence, state | Explicit optional operator snapshot of local DB/files/checkpoints; default last3 only. Physically remove each affected managed snapshot, or verify a sanitized reconstruction and physically remove its original before completion. Metadata invalidation alone is insufficient; inspect actual DB dumps, checkpoint copies, blobs and temporary archives for residual private content. Preserve other cases in active storage and independently acquired public corpus. Same-disk snapshot is not a disk-failure guarantee. |

On accepted deletion, increment generation and mark deleting atomically before revoking streams, cancelling work and queuing purge. Return202 and deny all further case-content routes. Append/fsync the local ledger and retry safely if unavailable; completion requires ledger durability and verified purge. Delete case rows/checkpoints/files/temp and affected managed snapshots; quiesce in-flight uploads and sweep orphan paths. Other cases' active content and independent public corpus remain intact.

Failure remains deletion_pending/retrying with access revoked; a stopped laptop cannot claim completed purge until work resumes. Local snapshots are optional and affected managed copies are removed before completion, not held for a cloud expiry window. Restore offline, reconcile current local ledger and purge restored deleted records/jobs before access/workers. Offline restore must remove all restored login sessions and pre-auth bootstrap state before traffic/workers and require fresh sign-in. Old cookies and CSRF tokens must fail, including sessions logged out or expired after snapshot capture; fresh owner login must succeed. Missing ledger fails closed. Active undeleted data has no age-based expiry. Untracked user copies and forensic disk erasure are outside application guarantees.

## State transitions

- **Case**: draft → ready → active → assessed → closed. Owner reopen returns a closed case to ready; new confirmed revision/checklist selects later work without altering earlier snapshots. Any nondeleted state → deleting → deleted. Run state and latest snapshot are separately represented.
- **RequirementRevision**: draft → confirmed; confirmed payload never edited. A later draft can be abandoned without invalidating its confirmed predecessor.
- **ChecklistVersion**: draft → confirmed; modified criteria/required flags create a new draft version needing confirmation.
- **Run**: queued → running → completed/completed_with_gaps, with cancelled/failed for orchestration failure. Individual tasks can wait on uploaded-document/identity actions while other tasks progress. Initial snapshot can exist while some tasks wait.
- **CheckTask**: queued → running → succeeded/no_evidence/failed; running → waiting_input only for permitted human-action types. Waiting → queued on valid resolution; any pending state → cancelled by owner closure/deletion or supersession policy. Source blockage itself is no_evidence after alternatives, never waiting for buyer scraping.
- **Claim processing**: proposed → confirmed → queued → checking → evaluated; waiting_input is orthogonal to the last assessment. After a new run, old verdict is historical until reassessed; do not relabel it as proof for changed requirements.
- **Report**: generating → ready/failed. A later snapshot creates a separate report, not an overwritten PDF.
- **DeletionRequest**: accepted → purging → completed after active files/rows/checkpoints/managed snapshots are verified purged; retries retain revoked access. Local ledger is outside content restoration.

## Persistence and validation invariants

1. Owner and case UUID are never inferred from an untrusted model response. Every nested ID must resolve within the authorized case.
2. Unique normalized local username, case+revision sequence, case+event sequence and stable operation keys enforce identity/order/idempotency.
3. No claims are generated from draft requirements; no collection begins before the selected checklist is confirmed.
4. Every evaluated claim has exactly one of the three verdicts per assessment. Proven/contradicted require retrieved admissible evidence; no-content unproven references actual local/remote/document checks and reasons.
5. An ambiguous entity/site/source period remains unproven. Differing office/factory addresses and fuzzy similarity alone establish neither proof nor contradiction.
6. Check results, model extractions and PDF jobs carry run/revision/checklist IDs. Late completion cannot overwrite another revision or deleted generation.
7. Immutable snapshots bind a PDF and visible table, including lists, gaps, dates, required flags and pending work.
8. Cross-case deduplication/merging is absent. Copying authorized evidence into another case creates an independent case-scoped artifact with attribution and revalidated freshness/rights.
9. Deleted content is fenced at read, dispatch, commit and object cleanup boundaries; a successful restore cannot resurrect it.
10. Free project quotas use atomic reservations; application limits never masquerade as provider quota. Paid spending is disabled by default, and local files/public sources need no tariff setup.
11. Source data is genuine, attributed and dated. Real-record replay is labeled; no source truth or expected verdict is fabricated. Free inference receives only eligible data; private/unknown-classification inputs remain local.
