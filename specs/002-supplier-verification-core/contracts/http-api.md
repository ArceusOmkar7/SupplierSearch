# HTTP API Contract — Core v1

**Date**: 2026-10-17 | **Base**: `/api/v1` | **Related**: [data model](../data-model.md), [conversation](conversation.md), [evidence contract](evidence-and-country-pack.md)

This is the normative design contract. Implementation must expose corresponding Pydantic/OpenAPI schemas and contract tests; no endpoints exist from this document alone. JSON uses snake_case, UUID strings and ISO8601 UTC timestamps. Content negotiation is JSON except SSE/file routes. All private requests use the current same-origin session; browser clients never send an owner_id.

## Authentication, authorization and errors

- Operator-provisioned local username/password accounts, maintained pwdlib Argon2 hashing and generic login failures with rate limiting. No external identity provider, cloud account or public registration/reset service required.
- Opaque HttpOnly/SameSite=Lax session cookie. Secure required except explicit loopback-only local-development profile. Absolute8h/idle30min expiry; pre-auth CSRF bootstrap plus Origin/Host checks protect login and authenticated mutations. No localStorage tokens. Offline restore must remove all restored login sessions and pre-auth bootstrap state before traffic/workers and require fresh sign-in. Old cookies and CSRF tokens must fail, including sessions logged out or expired after snapshot capture; fresh owner login must succeed.
- Every case/nested ID, event stream, document/report read and download is owner checked with current deletion/session state. Authenticated nonowner, unknown and deleted case-content references return the same404 shape; signed-out private requests return401. Never disclose another case through validation errors.
- Responses containing private metadata/content use `Cache-Control: no-store`. No public/presigned object download URL is returned. Content streams are proxied with current authorization and safe Content-Disposition.
- Errors: `{"error":{"code":"stale_version","message":"Reload the current revision before confirming.","request_id":"uuid","details":{}}}`. Details are owner-safe, not stack traces/provider credentials.
- Codes:400 malformed request;401 unauthenticated/expired session or invalid credentials;403 CSRF/origin rejection;404 inaccessible resource;409 invalid state/idempotency collision;412 stale If-Match;413 file too large;415 unsupported type;422 field validation;429 login/admission/free-quota limit;503 unavailable local dependency. Source failures usually become recorded check outcomes, not blanket case API errors.
- Commands that mutate drafts, confirm, start/cancel runs, select, close/reopen or delete require `Idempotency-Key`. Same actor+case+operation+key+body replays the original response; same key/different body is409. Durable domain effects additionally use operation keys. Deleted-resource retries never re-create a case.
- Owner-authored mutable resources expose ETag; PATCH and state-transition commands require `If-Match` for the relevant resource. Worker events do not change draft ETags. Immutable revisions/checklists/snapshots cannot be PATCHed. Reject concurrent stale edits rather than silently merge.
- Collections use opaque cursor pagination: `{"items":[],"next_cursor":null}`; page limit default25/max100. ID enumeration never bypasses ownership.

Lifecycle-dependent null fields follow the [data-model nullability rules](../data-model.md#nullability-and-lifecycle-constraints). API schemas and persistence checks must agree on null drafts, unpublished pointers and not-yet-ready report metadata.

## Route inventory

All paths below are under `/api/v1`; `{case}` always selects an owner-scoped case.

| Method / path | Request / precondition | Success |
|---|---|---|
| GET `/auth/csrf` | Loopback/same-origin bootstrap, no private content |200 pre-auth CSRF token and protected bootstrap cookie |
| POST `/auth/login` | username, password, CSRF and Origin/Host checks; rate limited |200 opaque local session cookie;401 generic invalid credentials |
| GET `/session` | Current session |200 buyer display details, CSRF token, expiry;401 otherwise |
| POST `/auth/logout` | Current CSRF; revoke local session |204, clear cookie; subsequent private reads401 |
| GET `/health/live` | Public, no source/config secrets |200 minimal process state |
| GET `/health/ready` | Public minimal status only |200/503 dependency availability, no private details |
| GET `/cases` | Owner session, cursor |200 only own undeleted case summaries |
| POST `/cases` | title?, initial_text?, supplied supplier identifiers? |201 case+draft revision+ETags; interpretation remains draft |
| GET `/cases/{case}` | Owner, undeleted |200 summary/current revision/run/snapshot refs, case ETag |
| PATCH `/cases/{case}` | title only; case ETag |200 changed title; requirements use revisions |
| GET `/cases/{case}/messages` | Cursor |200 ordered messages/components |
| POST `/cases/{case}/messages` | text, client_message_id, revision_id? |202 accepted interpretation job/message; cannot confirm/start/select |
| GET `/cases/{case}/revisions` | Cursor |200 revision summaries/history |
| POST `/cases/{case}/revisions` | based_on_revision_id?, reason?; case ETag |201 new draft within case; prior confirmed values unchanged |
| GET `/cases/{case}/revisions/{revision}` | Same-case reference |200 full draft/confirmed requirement payload+ETag |
| PATCH `/cases/{case}/revisions/{revision}` | draft only; revision ETag; editable fields/supplier set |200 updated draft+new ETag |
| POST `/cases/{case}/revisions/{revision}/confirm` | draft ETag; explicit buyer action, complete required fields |200 immutable confirmed revision; actor/time recorded |
| POST `/cases/{case}/revisions/{revision}/claims` | confirmed revision; Idempotency-Key |202 proposed checklist generation; store proposed criteria only |
| GET `/cases/{case}/checklists/{checklist}` | Same case/revision |200 claims/required flags/criteria+ETag |
| PATCH `/cases/{case}/checklists/{checklist}` | draft ETag; add/remove/edit claims, required flags, criteria |200 draft; confirmed checklist edits require a new version |
| POST `/cases/{case}/checklists` | based_on_checklist_id, revision_id |201 draft checklist version preserving earlier one |
| POST `/cases/{case}/checklists/{checklist}/confirm` | draft ETag; each claim has criteria/entity/period; at least1 required |200 immutable checklist confirmation |
| POST `/cases/{case}/runs` | case ETag; confirmed revision_id/checklist_id, mode |202 run+state/source capability summary; queued jobs persisted atomically |
| GET `/cases/{case}/runs/{run}` | Same case |200 progress/coverage, budget decision and snapshot refs |
| POST `/cases/{case}/runs/{run}/cancel` | run ETag |202 cancellation; actual attempts/history remain |
| GET `/cases/{case}/snapshots` | Cursor, optional run/revision filter |200 immutable snapshot summaries |
| GET `/cases/{case}/snapshots/{snapshot}` | Same case |200 full matrix/eligibility/gaps/pending actions |
| GET `/cases/{case}/evidence/{evidence}` | Same case |200 observation, original source/date/lineage and artifact refs |
| GET `/cases/{case}/attempts/{attempt}` | Same case |200 actual action, dispatch status, outcome and failure/missing reason |
| POST `/cases/{case}/documents` | multipart file+supplier_id+revision_id; supported PDF, max20MiB/50pages |202 artifact quarantined/queued for scan/extraction; no signed upload URL |
| GET `/cases/{case}/documents/{document}` | Same case |200 document metadata/extraction status |
| GET `/cases/{case}/documents/{document}/content` | Same case, scan permitted |200 private attachment bytes; Range support reauthorizes each request |
| GET `/cases/{case}/actions` | Pending/history filter |200 permitted buyer actions, never manual scraping tasks |
| POST `/cases/{case}/actions/{action}/resolve` | action ETag; replacement_document_id or identity_resolution |202 dependent work queued; unrelated work unaffected |
| POST `/cases/{case}/reports` | snapshot_id; immutable same-case snapshot |202 report metadata; idempotent per snapshot+renderer version |
| GET `/cases/{case}/reports/{report}` | Same case |200 generating/ready/failed, snapshot/revision refs |
| GET `/cases/{case}/reports/{report}/content` | Ready report, current owner session |200 PDF attachment bytes;409 if not ready |
| POST `/cases/{case}/decisions` | case ETag; snapshot_id, supplier_id?, select/reject/no_selection, reason? |201 explicit buyer decision; verdicts unchanged |
| POST `/cases/{case}/close` | case ETag; snapshot_id; owner may close with gaps |200 closed at frozen snapshot; cancel pending work; no outreach requirement |
| POST `/cases/{case}/reopen` | case ETag; reason; owner action |200 ready for explicit revision/recheck; earlier closed snapshot unchanged |
| DELETE `/cases/{case}` | case ETag; explicit owner action |202 deletion_request_id; content inaccessible immediately |
| GET `/deletions/{deletion_request}` | Original owner session |200 metadata-only active/managed-snapshot purge state;404 other owner |
| GET `/cases/{case}/events` | SSE, optional Last-Event-ID |200 ordered authorized events; replay/reconnect below |

No source credential, provider consent assertion, arbitrary fetch URL, SQL, supplier message/send, discovery or monitoring endpoint is exposed. Operator source setup uses deployment secrets/preflight tooling outside this buyer API.

## Canonical payload schemas

These are type definitions, not seeded example suppliers, generated evidence or demo payloads. Application values come from actual buyer input and attributable real source records.

| Payload | Required fields / semantics |
|---|---|
| RequirementRevision | UUID id/case_id, integer sequence, draft/confirmed status, actual requirements, location, supplier identifiers, field provenance, optional confirmed_at. Requirements include part/material/process/quantity+unit+period/certifications and genuine missing-field markers. Draft fields remain editable; explicit confirmation is required. |
| Claim | UUID id/revision_id/checklist_id/supplier_id, optional site/parent, type/assertion/relevant_period, buyer-confirmed required_for_shortlist, explicit proof_criteria, processing_state. Certificate validity/accreditation/scope/site and required capability dimensions are separately evaluable. |
| Assessment | UUID claim/revision/run references, exactly proven/unproven/contradicted, reasoning, criterion_results, actual evidence_ids/attempt_ids, gaps and policy_version. Proven/contradicted require admissible retrieved evidence. Source absence/timeout/no-record alone cannot contradict. |
| CheckAttempt | kind, source/target, actual action times, request_dispatched, outcome/reason, optional real HTTP/provider identifier and actual artifacts. Local missing-source decisions have no invented HTTP status/quotation. Each real retry is retained. |
| Snapshot | id/revision/run/checklist, created_at/event_cutoff/content_hash, claims/assessments, supplier states, source coverage, pending actions, qualified/follow_up lists and exclusion reasons. Real-record replay/cutoff limitations must be visible. |
| Report | snapshot/revision IDs, renderer_version, generating/ready/failed state, optional generated_at/content_hash. Render from exactly that immutable snapshot; a later snapshot is a new report. |
| DeletionStatus | id, accepted_at, purging/completed state, optional active_purge_completed_at/managed_snapshots_purged_at, retrying. No original case text, documents or evidence. |

Current source URL/collection date and original publication/cutoff/issue/expiry dates remain distinct. Local-import records never inherit a current-status timestamp from their import time. Real captured-response replay is explicitly labeled; application and tests must not invent official success/no-record/invalid-certificate results.

Deletion202 means access revoked and purge queued, not that every local file is already removed. Completion requires local rows/checkpoints/files/temp and all affected app-managed snapshots purged plus a durable local tombstone. Arbitrary user-made external copies and previously downloaded files are not recalled or represented as erased. Restore reconciles the retained local ledger before access/workers. Physically remove each affected managed snapshot, or verify a sanitized reconstruction and physically remove its original before completion. Metadata invalidation alone is insufficient; inspect actual DB dumps, checkpoint copies, blobs and temporary archives for residual private content. Preserve other cases in active storage and independently acquired public corpus.

Free source collection and local inference require no paid keys. Optional Gemini free-tier calls obey actual project quota and data restrictions; private/unknown-classification input stays local. Operator-only real export imports use local tools and manifests, not an arbitrary file-path/provider-credential endpoint in the buyer API.

## Event and race semantics

SSE event names: message.created, revision.updated, revision.confirmed, checklist.ready, checklist.confirmed, run.queued, run.progress, check.completed, action.required, action.resolved, snapshot.ready, report.ready, case.closed and case.deleting. Event body has case-local monotonic sequence, case/revision/run references, event type, timestamp and owner-safe component/ref payload. It never exposes secrets/raw provider payloads.

Persist event with the domain transaction. `Last-Event-ID` resumes case-local sequence. If a cursor is no longer replayable, emit a reset instruction to refetch current authorized state. Client deduplicates by case+sequence. Browser reconnects do not dispatch work or repeat confirmation. Revalidate session/ownership/deletion before every event and at least every15seconds; revoke/close unauthorized streams.

Worker completion checks case state, generation and run/revision before commit. Late results remain historical for their original revision; they never replace another revision's assessments. Closed snapshots do not change from asynchronous arrival. Deletion fences database/file writes, waits for in-flight cleanup and sweeps orphan files and affected managed snapshots before completion.
