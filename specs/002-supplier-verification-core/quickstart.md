# Local Setup and Real-Data Acceptance Guide — Core 002

**Revised**: 2026-10-19 | **Design**: [plan.md](plan.md) | **API**: [contracts/http-api.md](contracts/http-api.md)

## Availability and data policy

Backend/frontend scaffolds, dependency locks, local settings, genuine-record loaders and foundational mappings now exist. T012 now passes. Local setup/create-buyer/preflight, session/login/logout, initial case-read authorization and the durable worker foundation exist; see [implementation-progress.md](implementation-progress.md). Capture/import/evaluation/benchmark/report/restore commands and the supplier-verification stories below remain planned deliverables until their tasks are checked. Runtime preflight readiness does not establish feature acceptance. There is no seed-demo or synthetic-data setup path. Use actual buyer input, supplier pages, official downloads and attributable captured records throughout.

Required external-service cost is zero. No AWS, LocalStack, S3 account, Keycloak, paid verification API or billing-enabled model project is required. Hosting choices wait until the local product works. Source restrictions and evidence gaps remain visible rather than trigger a purchase requirement or fabricated replacement.

## Local prerequisites

Observed machine: Ryzen7 7840HS,15.3GiB usable RAM, RTX4060 Laptop8GiB VRAM and approximately65.3GiB free C drive at inspection. Windows Python3.14 and installed Node22.23.2 have passed dependency/build checks; uv/Docker/Ollama are available. Model quality and runtime memory under inference remain unmeasured. Start with already installed `qwen3.5:4b` pinned by digest, one inference at a time,4K context, page/section chunking. Its model file fitting on disk does not establish extraction accuracy or full GPU fit.

Run FastAPI, one worker, frontend and Ollama natively on loopback. Use free PostgreSQL17 locally, either native or a single Docker service. Do not allocate the earlier multi-service identity/object-storage stack. The foundation supplies `.env.example`, ignored `.env`/`.local/`, locked packages and basic local operations. Set actual local DB credentials and pin the installed model digest before preflight. Never replace existing credentials or pull a model to hide an unavailable dependency.

| Configuration | Required local behavior |
|---|---|
| App/login | Loopback allowed Host/Origin, session/CSRF secrets, operator-provisioned local accounts with Argon2 hashes; no public registration/cloud IdP. Secure cookie exception only for explicit local HTTP profile. |
| Database | Local Postgres URL and separate checkpoint schema; persistent local data. No hosted service or paid DB. |
| Files | Private local data root outside frontend assets/Git, generated case/UUID paths, atomic writes/hashes, OS-account access restrictions and safe path resolution. |
| Model | Local Ollama endpoint/model digest; no cloud mode. Optional free Gemini key/model with actual project quota and eligible public/nonpersonal data only. No key needed for local path. |
| Sources | Actual source URLs/policy checks and legitimate downloaded datasets with publisher/licence/cutoff/hash manifests. No fabricated success responses or dummy CSV records. |
| Spend/limits | Paid dispatch disabled; actual Gemini free quota if used; bounded web/page/token/concurrency limits from research. No mandatory tariff/account configuration for free pages/files. |
| Snapshots/deletion | Optional operator snapshots, default last3; append/fsync local tombstones outside restore paths; purge affected managed snapshots before deletion completion. No cloud retention/SLA assumption. |

Public business data is not automatically free of personal information. Omit unnecessary contact/demographic fields from Gemini inputs. Private buyer material or unknown-classification input stays local. Free-tier provider terms/quotas remain applicable; user opt-in cannot waive them.

## Local setup commands

The foundation commands are available. Run from repository root in PowerShell; preserve an existing private .env file:

```powershell
if (-not (Test-Path -LiteralPath .env)) { Copy-Item -LiteralPath .env.example -Destination .env }
uv sync --project backend --locked
npm --prefix frontend ci
docker compose --env-file .env -f infra/compose.yaml up -d postgres
uv run --project backend alembic -c backend/alembic.ini upgrade head
uv run --project backend python -m verisource.operations.cli setup-local --data-dir .local/data
uv run --project backend python -m verisource.operations.cli create-buyer
uv run --project backend python -m verisource.operations.cli preflight --profile local-free
```

Native Postgres users skip the compose command and supply the same local DB configuration. `create-buyer` prompts locally for the actual account credentials; invoke again for the second team member's ownership tests. No committed/default passwords or fake business records. Setup creates private directories and local ledger, not sample suppliers/certificates. Preflight checks DB/checkpoint schema, filesystem safety, local model and zero-spend configuration without printing secrets. It must not demand paid keys.

Buyer passwords must be at least 12 characters. To replace an existing password, run `uv run --project backend python -m verisource.operations.cli change-buyer-password` from the repository root. It prompts for the current and new passwords without command-line arguments and revokes that buyer's existing login sessions. Restart the API process after backend code changes before retrying in the browser; the frontend can remain running.

Start the available API/worker/frontend foundation processes in separate local terminals. US1 verification handlers remain pending:

```powershell
uv run --project backend uvicorn verisource.api.app:app --host 127.0.0.1 --port 8000
uv run --project backend python -m verisource.orchestration.worker
npm --prefix frontend run dev -- --host 127.0.0.1
```

Use the configured same-origin frontend API proxy. Ollama must listen locally; select the already installed model without an automatic pull. Record `ollama ps`/GPU memory during the real-record benchmark; do not make timing claims from model size or a synthetic prompt.

## Actual source acquisition and import

Implementation provides operator-local capture/import tools:

```powershell
uv run --project backend python -m verisource.operations.cli capture-source --url https://www.bis.gov.in/product-certification/products-under-compulsory-certification/ --output .local/sources/bis
uv run --project backend python -m verisource.operations.cli import-source --manifest .local/sources/official-export.manifest.json
```

The capture tool checks source policy/robots, records actual HTTP outcome/URL/time/content hash and retrieves only permitted real content. It must not write a successful document when retrieval failed. Imports use actual legitimately obtained CSV/XLSX/PDF/HTML, never invented replacement rows. Operator-controlled login/download for a bulk export may be needed once; buyer runs consume local data automatically without per-supplier manual portal work.

Manifest fields: publisher, original official URL, applicable licence/attribution, obtained time, publication/cutoff, geography/entity/claim coverage, original SHA256, source format and import/schema version. Original row/page locators remain traceable. Missing current exports remain unavailable; an old export cannot prove present active status. This local lookup corpus does not implement feature003 discovery.

Concrete researched real sources and their limitations are listed in [research.md](research.md): BIS QCO documents, actual supplier product pages, NABCB accreditation, issuer public profiles/client PDFs and legitimate MCA/Udyam exports when obtainable. Some official download metadata was accessible while actual current files were not; do not claim those imports succeeded. GST/other CAPTCHA coverage can remain unavailable without blocking the local product on payment.

For repeatability, capture allowed actual source bytes with their manifests and review acquisition rights before retaining/sharing. Replaying those records is labeled captured-record replay with original dates, never live retrieval. No seeded demo suppliers, synthetic country packs, fabricated certificate statuses or invented human-auditor labels. Protocol/error/restart tests can control test conditions while leaving the real domain records intact and disclosing the condition.

## Planned checks

```powershell
uv run --project backend pytest backend/tests/unit backend/tests/contract
uv run --project backend pytest backend/tests/integration
npm --prefix frontend run test -- --run
npm --prefix frontend run build
npm --prefix frontend run test:e2e -- --project=chromium
uv run --project backend python -m verisource.operations.cli evaluate --manifest .local/records/acceptance.manifest.json --profile local-free --output .local/acceptance/core002
```

Implementation supplies these scripts and actual record manifests. Tests must not fall back to generated fake records when a required capture is absent: report the missing-data test dependency honestly. Use a disposable test database so tests cannot erase the developer's cases. No live private artifacts or passwords committed to Git. Run browser tests through actual local login with two provisioned accounts, not automatic impersonation.

## Validation scenarios

| ID | Action using genuine records/input | Required outcome |
|---|---|---|
| V01 — Private accounts | First buyer owns actual case/documents/report. Second buyer and signed-out browser attempt all case/nested/stream/file/export/delete routes; log out owner and reuse references. | Owner permitted; other requests denied without content; no unauthenticated file URL. Bad password/CSRF/Origin rejected. SC-009. |
| V02 — Intake | Five timed trials using actual user-entered part requirements and real known suppliers; edit all fields, try starting before confirmations. | No unconfirmed claim generation/collection; explicit editable gates, under5min per trial if measured. No invented missing material/volume. SC-004. |
| V03 — Proof | Actual issuer/registry/supplier/official records naturally cover available claim/verdict types; independently assess their admissibility. | Only sufficient evidence proves, qualifying real refutation contradicts; missing/stale/ambiguous remains unproven. No model-generated citation or label is accepted as source truth. SC-002,005. |
| V04 — Automatic failure | Actual blocked/inaccessible source or faithfully replayed captured blocked page plus an independently accessible supplier source; disclosed interrupted request/quotas. | Zero buyer scraping actions; honest local decisions/real requests, independent work continues, gaps visible. No fabricated CAPTCHA response posing as official output. SC-001,012. |
| V05 — Certificate documents | Actual obtained text/scanned certificate documents and legitimately held locked/unreadable documents where available. | Page provenance/uncertainty; replacement upload pauses only dependencies. Missing real locked/scanned sample is an explicit test-data gap, never a fabricated certificate. SC-006,012. |
| V06 — Identity/shortlist | Actual name/identifier/address/source conflicts and naturally incomplete/contradicted required claims from the real corpus. | No fuzzy-only proof, office/factory roles preserved; all-required-proven qualification, separate follow-up, contradictions excluded, empty shortlist valid. Missing examples stay untested. SC-005,007,011. |
| V07 — Restart | Kill/restart API/worker at collection/commit/checkpoint/ack boundaries using actual captured records; duplicate real work delivery and disclosed multi-day clock condition. | Committed state/actions survive; idempotency and lease recovery, no invented response content. SC-006. |
| V08 — PDF | Export a real-record immutable snapshot, then allow later work and export another. Render every page and compare content. | Same revision/snapshot/verdicts/lists/dates/citations/gaps; legible long/Unicode fields, authenticated local downloads. SC-005,011. |
| V09 — Country interface | Attributable real India/other-country source record envelopes validate shared contracts; actual country008 checking is not implemented here. | Shared schema/policy boundary unchanged, unsupported coverage explicit; no synthetic pack or fictional US result. SC-008. |
| V10 — Revision | Buyer changes their actual material/quantity/certification after collection, reconfirms and allows earlier jobs to finish; closes/reopens explicitly. | Same case/new revision; no changed-input use before confirmation; late results historical, closed snapshots immutable. SC-010. |
| V11 — Retention/delete | Use real stored cases under disclosed clock advancement, delete during file writes, inspect actual local rows/files/checkpoints/managed snapshots, restore earlier snapshot offline. | No live-data TTL; immediate denial; verified content/snapshot purge, durable tombstone, no restored/late resurrection, other cases intact. Missing ledger blocks restore. Offline restore must remove all restored login sessions and pre-auth bootstrap state before traffic/workers and require fresh sign-in. Old cookies and CSRF tokens must fail, including sessions logged out or expired after snapshot capture; fresh owner login must succeed. SC-009,013. |
| V12 — Free local real run | Real supplier page and official document retrieval/import plus real-record local extraction on the laptop; optional eligible Gemini free path. | No paid/cloud credentials needed, zero demo data; URLs/dates/hashes and live/replay distinctions recorded. Source gaps remain unproven. SC-001,005,012,014. |
| V13 — Actual exports | Import an actually acquired official CSV/XLSX/PDF/HTML and inspect selected exact-ID matches, original locators and cutoff. | Schema/provenance validated, malformed files quarantined, historical status never silently current. Missing real export means unavailable source, not dummy rows. FR-033,SC-014. |

Also exercise collector SSRF/redirect/subresource guards and source prompt injection without altering source facts; disclose constructed attack/control conditions instead of presenting them as official evidence. Test keyboard edits/confirmations, table headers/expansion, focus, contrast and non-color verdict labels with the real displayed records.

## Model, timing and auditor evaluation

```powershell
uv run --project backend python -m verisource.operations.cli benchmark-model --manifest .local/records/model-evaluation.manifest.json --model qwen3.5:4b --output .local/acceptance/model
uv run --project backend python -m verisource.operations.cli benchmark --suppliers 5 --profile local-free --manifest .local/records/acceptance.manifest.json --output .local/acceptance/core002/timing
```

The model manifest contains actual allowed excerpts/pages with original source/time/hash and human-checked field references; do not invent a purchase requirement or certificate to fill it. Record load time, model digest/context, RAM/VRAM/offload, latency and field errors. Schema-valid extraction is not proof of supplier capability. Current model usefulness and30-minute performance remain unmeasured until this genuine-record evaluation runs.

SC-002 requires30 real suppliers across six five-supplier cases, all standard claim types/three verdicts and actual independent human-auditor labels/cutoff. Missing verdict classes or auditor labels must be reported, not manufactured; no acceptance pass until real coverage exists. Report overall agreement target≥80%, per-verdict/type counts and confusion matrix. Use the same 30 real suppliers across six five-supplier cases as SC-002. Record active intervals for intake, corrections, confirmations, evidence review and decision/report actions; divide shared case time equally across evaluated suppliers and never double-count overlapping intervals. Report all 30 per-supplier totals and the maximum; every total must be under one hour. Separately record unattended collection and excluded actual waits. Missing any supplier timing leaves SC-003 unmeasured; a five-supplier timing run or average alone cannot pass it. The estimated manual baseline remains unverified.

SC-001 starts at accepted start-run after confirmations, includes queue/retries/local inference/report time and does not stop for source failures. Exclude only actual recorded buyer/supplier waits and report them separately. Record laptop load, concurrency, free source/project limits, retrieved pages/bytes, model/digest/tokens and p50/p95/max. Bigger lists and real-record replay are separate workload/results. Free Gemini quota exhaustion is not a reason to silently pay or fabricate output.

## Local snapshots and deferred hosting

```powershell
uv run --project backend python -m verisource.operations.cli snapshot-local --retain 3
uv run --project backend python -m verisource.operations.cli restore-drill --offline --output .local/acceptance/core002/restore
```

Snapshots are optional actual local files, not a cloud backup service. Quiesce writes and capture consistent DB/checkpoints/blobs/hash manifests. Physically remove each affected managed snapshot, or verify a sanitized reconstruction and physically remove its original before completion. Metadata invalidation alone is insufficient; inspect actual DB dumps, checkpoint copies, blobs and temporary archives for residual private content. Preserve other cases in active storage and independently acquired public corpus. Current tombstones are never rolled back by restore. Offline restore must remove all restored login sessions and pre-auth bootstrap state before traffic/workers and require fresh sign-in. Old cookies and CSRF tokens must fail, including sessions logged out or expired after snapshot capture; fresh owner login must succeed. Same-disk backups cannot promise recovery from disk loss, and arbitrary user-made copies cannot be erased by app deletion. No cloud SLA,35-day backup window or S3-version test is required. Host/deployment/storage migration is deferred until the local product works.

## Success-criterion mapping

| Criterion | Required genuine evidence |
|---|---|
| SC-001 | Five-real-supplier local timing/source coverage and waits: V04,V12 |
| SC-002 |30 actual suppliers and independent auditor labels: V03 |
| SC-003 | Same30 suppliers as SC-002; every active-time total and maximum<1hour; no assumed baseline |
| SC-004 | Five actual-input intake trials: V02 |
| SC-005 |100% evaluated/exported references match actual content/attempts: V03,V06,V08 |
| SC-006 | Actual local state and labeled restart/wait tests: V05,V07 |
| SC-007 | At least3of4 warning-pattern families found in real records; missing real examples reported: V06 |
| SC-008 | Real-source envelope compatibility/unsupported coverage: V09 |
| SC-009 | Two local accounts and signed-out route/file/stream denial: V01 |
| SC-010 | Actual requirement revision and late-work scenarios: V10 |
| SC-011 | Naturally qualified/follow-up/excluded/empty outcomes agree in table/PDF: V06,V08 |
| SC-012 | Unattended real-source/free fallback and independent work: V04,V05,V12 |
| SC-013 | Real stored data under labeled clock tests; local purge/restore: V11 |
| SC-014 | Genuine local end-to-end records, source/import provenance and no required paid/cloud key: V12,V13 |

Final report distinguishes planned, implemented, real live-tested, genuine-record replay, controlled test conditions, unavailable and untested behavior. No demo data or synthetic result can close a missing acceptance gap.
