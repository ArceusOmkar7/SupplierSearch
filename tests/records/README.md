# Genuine source records

No supplier, certificate, buyer request, source response or auditor label is generated
for testing. Keep actual bytes and per-record JSON manifests under ignored
`.local/records/`. Never commit private records. A missing capture is an unmet test
prerequisite, not permission to generate one. Do not count skipped checks as acceptance.

Each manifest conforms to `manifest.schema.json`. Record the original URL, publisher,
applicable reuse rights and attribution, actual UTC acquisition time, source cutoff
(or null with an explicit unknown-cutoff reason), jurisdiction and claim coverage,
relative byte-file path, SHA256 and original row/page locator. A successful HTTP
response alone does not establish reuse rights or current status.

Use `mode: live` only for actual collection. A replay preserves the original manifest
and uses a run-level replay label. Fault/restart/clock controls are documented in the
test/run metadata, never invented official response bodies. Do not edit source bytes
to manufacture certificate statuses or warning patterns. Auditor labels must be supplied
by an actual independent human, with identity/cutoff kept in protected local records.

Acquire allowed supplier pages and official documents from the feature's researched
sources. Check current access and reuse policies before capture. Keep failed attempts
in the acquisition log, not as successful content manifests. Imports preserve the
source's historical date; acquisition today cannot refresh it.
