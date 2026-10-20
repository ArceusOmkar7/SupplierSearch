# Implementation Plan: Local-First Supplier Verification Core

**Branch**: `main` (actual checkout) | **Revised**: 2026-10-19 | **Spec**: [spec.md](spec.md)

**Feature directory**: `specs/002-supplier-verification-core`, selected by `.specify/feature.json`. The setup script's feature/branch label differs from actual Git branch `main`; no branch was created. Directory selection governs scope.

**Status**: Research/design revised to the user's free-first, local-first, real-data-only instructions. The 102-task list passed the2026-10-19 consistency review with no critical findings. 73 of 102 tasks are complete and verified as of 2026-10-20 (US1 and most of US2 done; US3 and Phase 6 mostly open). Current measured results, the real-source acceptance record and open items are in [implementation-progress.md](implementation-progress.md); no success criterion is claimed passed. These decisions supersede the earlier paid-Gemini/API/S3 plan.

## Summary

Build and run the real product on the user's laptop before selecting hosting. Use actual supplier websites, eligible issuer records, official public documents and legitimate government exports for automatic evidence collection/local lookup. Use installed local inference and optional eligible Gemini free tier. Store files on local disk. No paid API/model, AWS S3, LocalStack, hosted database, identity service or cloud backup is required to build, run or validate the local prototype.

Preserve private buyer accounts, editable confirmed intake, claim confirmation, immutable requirement revisions, durable work/history, conservative evidence rules, qualified/follow-up shortlist separation and same-snapshot reports. Unavailable or stale source evidence stays explicit and unproven. Never seed demo suppliers or invent evidence to make the product appear complete. See [research.md](research.md).

## Technical Context

**Language/Version**: Python3.14, TypeScript, React19/Vite8 and Node22.23.2, with Node24 supported. The installed Node22 satisfies Vite's documented22.12+ requirement; avoid changing the system Node installation. Exact package versions are locked.

**Primary Dependencies**: FastAPI/Pydantic2, SQLAlchemy2/Alembic1/psycopg3, LangGraph1/Postgres checkpointer; pwdlib Argon2 and opaque session primitives; HTTPX, Playwright Chromium, pdfplumber/pypdfium2/Tesseract, openpyxl for actual XLSX source imports, ReportLab; local Ollama HTTP and optional Google GenAI SDK. No S3 SDK, Keycloak/Authlib integration or paid data-provider adapter is required.

**Storage**: Free local PostgreSQL17 (native or one Docker service) for canonical records, sessions, jobs and checkpoint schema. Private ordinary filesystem files under an app data root; atomic writes/hashes/case-scoped paths and an append/fsync deletion ledger outside managed snapshot restore. No cloud object store or S3 emulator.

**Testing**: pytest, Vitest/React Testing Library and Playwright using actual public/authorized records and faithfully captured real responses. No synthetic suppliers, generated certificate evidence or fabricated provider responses. Distinguish live retrieval, genuine-record replay, controlled restart/fault/clock tests and actual auditor labels. No test fixture can masquerade as source truth.

**Target Platform**: Current Windows laptop, API/worker/frontend/Ollama on loopback; optional Docker only for local PostgreSQL. Observed Ryzen7 7840HS,15.3GiB RAM, RTX4060 Laptop8GiB VRAM and65.3GiB free disk. No server host/SLA deployment assumption.

**Project Type**: Local private web application plus one durable worker. No hosting platform, discovery index, voice/drawing intake, outreach, monitoring or second-country implementation in002.

**Performance Goals**: Five-supplier initial report within30minutes including source failures/queueing, actual excluded buyer waits recorded; text intake under5minutes. Benchmark local hardware and sources before claiming success. Local inference starts at one request at a time and4K context; chunk larger documents. Cold starts/free quota may affect timing and must be reported.

**Constraints**: Required monetary spend zero; no silent paid fallback, paid Search grounding or mandatory premium API. Real records only. Source access/robots/reuse restrictions respected; no CAPTCHA bypass or buyer portal tasks. Historical exports do not establish present status. Private/personal/confidential inputs remain local under provider rules; free Gemini handles eligible public business data only. Undeleted cases retain data until owner deletion.

**Scale/Scope**: One active five-supplier batch on this laptop; larger lists queue in the same case. Four outbound requests, one/domain/browser and one local inference at a time. Actual30-supplier human-auditor evaluation and per-supplier active-time measurements remain required for SC-002/003; lack of a real dataset means unmet evaluation, never synthetic substitution.

## Constitution Check

*Pre-research and post-design checks against constitution v1.0.0, repeated for this user-directed revision.*

| Principle/constraint | Design evidence | Result |
|---|---|---|
| I. Evidence Before Verdicts | Actual source bytes/rows/page provenance, dates/lineage, conservative criteria; stale/missing evidence unproven; no fabricated data. | PASS: design |
| II. Buyer-Controlled Decisions | Explicit intake/checklist/revision confirmation and selection; no supplier messages; closed snapshots immutable. | PASS: design |
| III. Durable Auditable State | Local Postgres/jobs/checkpoints, scoped files, private sessions, idempotent writes, deletion ledger and restore reconciliation. | PASS: design |
| IV. Scoped Shared Rules | One proof/country boundary; export corpus for known suppliers, not003 discovery; no future-feature code. | PASS: design |
| V. Honest Readiness | Real-record live/replay distinction, no demo data, all14 SCs mapped; no claimed runtime/source completeness. | PASS: design |
| Source access/capacity | Free-source matrix, explicit data dates/permissions/coverage and actual Gemini project quota; no invented sufficient free tier. | PASS: design; live source/data tests pending |
| Preferences/budget | React/FastAPI/LangGraph retained; local installed Qwen/free Gemini, local free DB/files; cloud/paid integrations deferred. | PASS: design |

No constitutional waiver requested. Zero required spend does not weaken proof thresholds or turn unavailable sources into successful checks. No premium credential is a design/acceptance prerequisite.

## Project Structure

### Documentation (this feature)

```text
specs/002-supplier-verification-core/
  spec.md
  plan.md
  research.md
  data-model.md
  quickstart.md
  contracts/{http-api,evidence-and-country-pack,conversation}.md
  checklists/requirements.md
  tasks.md                         # generated 102-task list
```

### Source Code (planned repository layout)

```text
backend/
  pyproject.toml
  uv.lock
  src/verisource/
    api/                           # local login, cases, revisions, content/events
    domain/                        # confirmation, policy, assessments, selection
    db/                            # local Postgres, owner scopes, transactions
    orchestration/                 # graph, leases, dispatch and recovery
    sources/                       # free fetchers, real export import/local lookup
    country_packs/india/            # BIS/registry/identity/address rules
    documents/                     # supplier certificate extraction/OCR
    models/                        # local Ollama; optional free Gemini routing
    storage/                       # ordinary filesystem, safe paths, atomic writes
    reports/                       # immutable snapshot/PDF
    operations/                    # setup, imports, captures, snapshots, real-data evaluation
  migrations/
  tests/{unit,contract,integration,acceptance}/
frontend/
  package.json
  package-lock.json
  src/{app,components,features,api}/
  tests/
infra/
  compose.yaml                     # optional local PostgreSQL only
scripts/                           # local startup/validation
tests/e2e/
tests/records/                     # manifests; actual permitted records, never fabricated
.local/                            # ignored data, captures, models/output references
```

**Structure Decision**: Keep one backend package with API/worker processes and a free local Postgres queue/checkpointer. Filesystem storage is deliberately small and independent of cloud protocols. Remove the previous identity/object-store/proxy infrastructure stack. Native processes use the installed laptop resources; hosting is a later decision.

## Phase 0 — Research resolution

[research.md](research.md) resolves stack/machine/model choices (D01–03), local identity/files (D04), free real-source/export ingestion (D05), certificate alternatives (D06), durability/evidence/spend bounds (D07), local snapshots/deletion (D08) and real-data acceptance (D09). Actual public downloads may still be unavailable; source access/schema/coverage is reported accurately without dummy replacements.

## Phase 1 — Design and contracts

1. Operator provisions local buyers and optional genuine source snapshots. Buyer enters an actual requirement/list; extraction yields editable drafts and cannot confirm itself.
2. Buyer confirms a requirement revision, then reviews/confirms required claims/proof criteria. No collection before these gates.
3. Start-run commits run/outbox intent atomically. Worker performs permitted free live checks and local corpus lookup independently, with deadlines/quota limits and no paid dispatch path.
4. Preserve actual retrieval/import byte hashes, publisher/URL, publication/cutoff, collected time and row/page provenance. A bulk file is not refreshed just because it was imported today. Incomplete input is quarantined, never filled with invented records.
5. Local Qwen extracts private/unknown-classification inputs; optional Gemini free path receives only eligible nonpersonal/nonconfidential business text. Never silently route local/private input to cloud on failure. Model output must pass schema/admissibility checks and cannot manufacture proof.
6. Shared policy matches assertion/entity/site/period/authority and independent lineage. Missing current evidence, uncertain source conflicts or supplier-only support yield unproven. Qualifying direct refutation yields contradicted.
7. Commit evidence/attempts/assessments/events idempotently; graph replay consults canonical rows. Pause only uploaded-document/identity dependencies; source blockage tries eligible free alternatives then gaps, without buyer scraping tasks.
8. Publish partial/deadline snapshots and qualified/follow-up lists from actual records. Export exact snapshot PDF; buyer selection remains explicit. Changed requirements require new confirmed revision/checklist; late results stay historical.
9. Owner deletion revokes content access, fences work, writes a durable local tombstone and purges content/checkpoints/temp plus every affected app-managed snapshot before completion. Restore reconciles current tombstones before traffic/workers. Offline restore must remove all restored login sessions and pre-auth bootstrap state before traffic/workers and require fresh sign-in. Old cookies and CSRF tokens must fail, including sessions logged out or expired after snapshot capture; fresh owner login must succeed.

### Records and interfaces

- [Data model](data-model.md): case/revision/evidence/history plus local source datasets and safe filesystem references.
- [HTTP API](contracts/http-api.md): local sessions, owner-scoped commands/content, concurrency and events.
- [Evidence/country contract](contracts/evidence-and-country-pack.md): real-source imports, free collection, provenance, proof and extension boundaries.
- [Conversation](contracts/conversation.md): editable gates, real evidence/gaps, revisions, local retention/delete and matching PDFs.

### Security, local operations and cost

Provision accounts locally with maintained Argon2 hashing, not custom cryptography. Opaque sessions last8h absolute/30min idle; CSRF/Origin/Host checks, login throttling and logout revocation. Loopback-only development can use non-Secure cookies under explicit local profile; remote deployment requires TLS review. Every nested route/download/stream checks current owner/session/deletion. No public filesystem/static URLs; no-store content responses. File paths are generated and resolved within the data root, rejecting traversal/junction/symlink escape.

Local files/DB are private to the application OS account. That trusted operator can access their own machine; browser account isolation is the application boundary. Provider/model secrets remain in ignored local configuration. Avoid claiming encrypted cloud storage or failure-independent replication. Source collectors validate destinations/redirects/resolved IPs and browser subresources against internal/metadata targets; parser/source text is untrusted and never executable application instructions.

Default paid-spend allowance is zero. No Gemini key is required for local inference. Free-tier rate limits are project-specific and checked at configuration;429 yields bounded queue/retry or a visible unavailable result. Scraping/imports can proceed without an inference provider for deterministic checks. Actual absent current-status coverage is a limitation, not a purchase prompt.

No cloud backup SLA. An optional explicit local snapshot command quiesces writes and captures DB/files/checkpoints with hashes; retain last3 managed snapshots by default to limit disk use. Local deletion follows physical content purge. Physically remove each affected managed snapshot, or verify a sanitized reconstruction and physically remove its original before completion. Metadata invalidation alone is insufficient; inspect actual DB dumps, checkpoint copies, blobs and temporary archives for residual private content. Preserve other cases in active storage and independently acquired public corpus. untracked user copies/SSD forensic erasure are outside the application guarantee. Preserve an append/fsync deletion ledger outside snapshot restore and fail closed if missing. Logs omit private content/secrets; track actual source/model latencies, queue age, disk usage, failures, replay labels and pending purge.

### Requirement and validation coverage

| Requirements | Design owner | Quickstart scenarios |
|---|---|---|
| FR-001–006 | Conversation/revisions/identifiers | V01,V02 |
| FR-007–008 | Confirmed checklist/policy | V02,V03 |
| FR-009–014 | Free sources, local corpus, India/certificate reader | V03,V04,V05,V12 |
| FR-015–019 | Identity/address/evidence policy | V03,V06 |
| FR-020 | Canonical local state/jobs/checkpoints | V07 |
| FR-021–023 | Snapshot, shortlist, PDF | V06,V08 |
| FR-024–025 | Country/India boundary | V09,V12 |
| FR-026–027 | Re-evaluation/history, actual attempts | V03,V07,V10 |
| FR-028 | Local sessions/owner checks | V01 |
| FR-029–030 | Revisions/independent checks | V04,V05,V10 |
| FR-031 | Local deletion/managed snapshots/restore | V11 |
| FR-032–033 | Zero required spend, genuine records, local official imports | V12,V13 |

[quickstart.md](quickstart.md) maps all14 success criteria. Real-world source capture/replay, independently labeled real audit data and disclosed fault/time conditions replace invented fixture responses. A missing real dataset leaves its accuracy criterion unmeasured.

## Delivery prerequisites and readiness

The generated 102-task list passed consistency analysis on2026-10-19 (47 requirements covered; no critical findings). Setup and foundation (20/102 tasks) are implemented and validated. The verification stories and final acceptance remain unimplemented/unverified; the feature is not acceptance-ready. Initial implementation and local acceptance require no paid API, billing project or cloud storage. Demonstrate real public supplier and official-document retrieval/import and local extraction on this machine, reporting exact coverage/remaining gaps. No fabricated records are an acceptable replacement for inaccessible portals or an unavailable30-supplier audit dataset.

## Complexity Tracking

No constitutional violation identified. Local Postgres/worker support durable committed state; ordinary files satisfy evidence/PDF retention without an object-store service. Remove paid data adapters, S3/LocalStack, Keycloak, cloud backup/SLA and production deployment work from current tasks. Future storage/hosting choices can reuse the simple interfaces without becoming current dependencies.
