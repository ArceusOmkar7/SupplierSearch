# Core 002 implementation progress

Updated 20 October 2026. This is a record of what exists and was executed, not feature
acceptance. Nothing below claims a success criterion (SC-001–SC-014) as passed.

## Status

73 of 102 tasks are marked complete in [tasks.md](tasks.md); each was checked only after the
tests named below passed. 29 remain open: T070, T072–T076, T078, T081–T092 and T093–T102.

| Area | State |
|---|---|
| Setup and foundation (T001–T020) | Complete (earlier session) |
| US1 — confirm requirements, verify a known supplier list (T021–T053) | Complete, including one real browser journey |
| US2 — evidence, shortlist, decisions (T054–T069) | Complete; T070 (end-to-end review spec) not written |
| US3 — lifecycle, reports, deletion, restore (T071–T092) | Started: lifecycle contracts (T071), deletion ledger (T077), revision/close/reopen (T079–T080) done; tests for restart, PDF, deletion/restore, report/deletion models' constraints, recovery, PDF rendering, report service, local snapshots, purge, restore, CLI, UI and the US3 acceptance remain |
| Phase 6 validation (T093–T102) | Not started |

## What was executed (measured, this session)

| Check | Result |
|---|---|
| Backend suite (`pytest`, fresh disposable PostgreSQL, 133 tests, real-run test excluded) | 132 passed, 1 skipped |
| The one skip | `test_natural_locked_and_scanned_certificates_are_missing_prerequisites`: no genuine locked or scanned certificate has been acquired |
| Real browser journey `backend/tests/acceptance/test_us1_real_run.py` + `tests/e2e/verify_known_suppliers.spec.ts` | 1 passed (Playwright reports 5.0 min) |
| Frontend (Vitest) | 21 passed in 3 files |
| `ruff check`, `ruff format --check`, strict `mypy` (125 files), `tsc -b`, production `vite build` | All pass |

Live-network and local-model tests (marked `live`) ran against the actual sources and the
installed, digest-pinned `qwen3.5:4b` model. If the model is cold or busy the certificate
model test skips instead of passing on rule output.

## Real-source acceptance record (US1)

Run through the real API, the durable worker and Chromium on 20 October 2026; raw output is in the
ignored `.local/acceptance/core002/us1/`. Four suppliers (not five) were verified, so this says
nothing about SC-001 timing. The suppliers are actual rows of the historical BIS IS 9473
licence list (cutoff 27 Aug 2020); each website is the company domain of the contact email
printed in that official record and is an unverified buyer-supplied identifier. The requirement text
was written by the operator for that licence list; it is not a genuine buyer request.

| Measured value | Result |
|---|---|
| Run state | `completed_with_gaps` |
| Check tasks | 8 succeeded, 16 ended with no evidence |
| Attempts | 88 success, 7 blocked (captcha), 8 no matching record, 4 skipped (not supported), 8 skipped (no identifier) |
| Requests actually sent | 91 |
| Evidence records | 82 (4 official publication, 78 supplier self-report) |
| Identity resolutions | 4 confirmed (exact licence number), 4 ambiguous |
| Assessments | 36, all `unproven` (no proven or contradicted verdict) |
| Collection time | about 267 s in the run record, 289 s observed in the UI |

The seven captcha-blocked attempts were, in an earlier identical run that was inspected, pages
on karam.in that gate a catalogue download behind a CAPTCHA; the product reported them as blocked
and did not solve them. Nothing was asked of the buyer.

Problems found by running against real sources, and fixed: a job that exhausted its retries left
its check `running` forever and the run unfinished (now the check is `failed` with a recorded
internal attempt); a page that merely embeds a CAPTCHA form was classed as blocked (now only
challenge pages are); worker logs hid the failure location (now exception type and frames are
logged, never values). One failed run was caused by my own concurrent pytest sessions deleting the
shared pytest temp directory; each harness run now has its own.

## Genuine records acquired this session (private, ignored `.local/records/`)

See [acquisition.md](../../tests/records/acquisition.md). They include the BIS QCO Scheme-I table, an
actual DNV ISO 9001 certificate PDF published by a casting company (valid 30 Sep 2023 – 29 Sep
2026, so expired at the time of the run), two BSI client-directory certificate profiles, the NABCB
page and a supplier page that is a real CAPTCHA download gate. The TUV Rheinland India client
list named in research.md now returns HTTP 404 and was not captured.

## Decisions and deviations

- Run admission is limited to one active run per case **and revision** (migration 0004 changes the
  index) so a late earlier-revision run can finish while a newer revision is confirmed. A late
  result never becomes the case's current snapshot and is flagged `historical`.
- T079's behavior lives in `api/cases.py` and `orchestration/planning.py`, not a separate
  `domain/revisions.py`. Every new revision re-runs all checks; no evidence is copied between runs.
- The deletion ledger is hash-chained. A header written by the earlier `setup-local` (no chain
  fields) is accepted and extended.
- Snapshot publication is per supplier as its checks finish, at the 30-minute deadline and at
  completion; identical states create no duplicate assessment or snapshot.
- Closing cancels pending runs, tasks, actions and jobs; decisions and runs are refused until the
  owner reopens the case.
- `jobs.fail` now takes an error type; unknown or exhausted work is visible rather than silent.

## Known limitations and unverified items

- No OCR engine is installed (Tesseract absent): scanned pages are reported unread. QR images are not
  decoded. The current BIS licence search is CAPTCHA-protected and is never automated. IAF
  CertSEARCH, current GST status and BSI/TUV SUD lookups by certificate number are explicitly
  unavailable.
- BIS order PDFs linked from the Scheme-I table are not read, so order coverage is `partial`
  and cannot prove applicability.
- Manufacturer/trader review indicators are unvalidated heuristics; no real confirmed example of
  any of the four patterns has been checked (SC-007 unmeasured).
- `reports`, `deletion_requests` and `local_snapshots` tables (migration 0004) are created and the
  migration applies in every test database, but no test exercises their constraints yet, so
  T075, T076 and T078 stay open.
- Restart/duplicate-delivery behavior is tested for duplicate delivery and cancellation; process-kill
  and multi-day-wait tests (T072) are not written.

## Success-criterion status

None is claimed passed. SC-002 and SC-003 are `unmeasured`: there are no independent human audit
labels and no observed per-supplier timings, and the evaluation tool (`evaluate`) reports exactly
that when run on a manifest without them. SC-001 (five-supplier timing), SC-004, SC-005 (export
side), SC-006, SC-007–SC-011, SC-013 and SC-014's full scope are not yet measured. Outstanding
real inputs: a genuine buyer request matching the suppliers, natural locked/scanned/contradicted
examples, 30 suppliers across six cases, independent human labels and observed active-time records.

## Operating notes

- The API and worker must be restarted to load this code, and the database migrated first:
  `uv run --project backend python -m verisource.operations.cli setup-local`
  (applies migrations 0002–0004). Start the worker with
  `uv run --project backend python -m verisource.orchestration.worker`.
- Docker Desktop was not running at the start of this session; the project's PostgreSQL container was
  restarted with `docker compose --env-file .env -f infra/compose.yaml up -d postgres`.
- Chromium for Playwright was reinstalled (`playwright install chromium`) because the earlier build did
  not match the installed Playwright version. `@testing-library/user-event` was added to the frontend.
- Reproduce the backend suite from the repository root with the disposable-database harness:
  `uv run --project backend python .local/validate_foundation.py backend/tests -q`
  (ports 8000 and 5173 must be free for `test_us1_real_run.py`; do not run other pytest sessions
  against the same base temp directory at the same time).
- Frontend: `cd frontend && npx tsc -b && npx vitest run && npm run build`.
