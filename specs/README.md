# VeriSource Specification Map

The [product baseline](001-supplier-verification-agent/spec.md) preserves the agreed scope and original identifiers. The seven delivery specs below are the active requirements for planning. The baseline is retained for provenance rather than treated as an eighth implementation feature.

The split was performed as seven successive speckit-specify passes: one new feature directory and quality checklist per pass, using the project's resolved spec template and sequential numbering. No extension hooks were registered, so no branches were created. All features remain draft specifications except that implementation of `002-supplier-verification-core` is under way (see its [implementation-progress.md](002-supplier-verification-core/implementation-progress.md)); no feature is claimed complete or accepted.

## Delivery features

| Directory / SPECIFY_FEATURE_DIRECTORY | SPEC_FILE | Independent acceptance boundary | Required predecessor |
|---|---|---|---|
| `specs/002-supplier-verification-core` | [Core spec](002-supplier-verification-core/spec.md) | Confirm typed intake and a known list; gather evidence; assess India suppliers; resume cases; review/export a report. | None |
| `specs/003-supplier-discovery-index` | [Discovery spec](003-supplier-discovery-index/spec.md) | Ingest multiple source families, search and curate attributable candidates, then hand off the chosen list. | Core confirmed-intake and identity contracts |
| `specs/004-pdf-drawing-intake` | [PDF/drawing spec](004-pdf-drawing-intake/spec.md) | Extract and review buyer-document fields, use visual fallback, confirm separate BOM items. | Core confirmation and case-creation contracts |
| `specs/005-supplier-outreach-followup` | [Outreach spec](005-supplier-outreach-followup/spec.md) | Approve exact emails, wait durably, associate replies, re-evaluate evidence and approve follow-ups. | Core persistence, certificate reading and evidence policy |
| `specs/006-voice-intake` | [Voice spec](006-voice-intake/spec.md) | Record, transcribe, edit and confirm requirements; measure the bounded timing workload. | Core confirmation contract |
| `specs/007-approved-supplier-monitoring` | [Monitoring spec](007-approved-supplier-monitoring/spec.md) | Watch certificates and applicable QCOs; distinguish changes from failures; review attributable alerts. | Core identities, case products and evidence history |
| `specs/008-second-country-verification` | [Second-country spec](008-second-country-verification/spec.md) | Demonstrate the US country pack and unchanged shared behavior with paired India/US cases. | Core country-pack boundary and evidence policy |

Each directory contains `checklists/requirements.md`. The checklist markers record requirements-quality review, not runtime verification.

## Shared rules and authority

- **Evidence and verdict policy**: [002, Evidence and Verdict Policy](002-supplier-verification-core/spec.md#evidence-and-verdict-policy) is the maintained shared policy. The baseline's copy records its pre-split provenance. Later policy changes must update affected feature acceptance criteria and this map.
- **Confirmed intake**: 002/FR-003–004 own the shared input and confirmation contract. 004 supplies document-derived drafts and 006 supplies reviewed transcripts. Neither extension may bypass confirmation.
- **Private case ownership**: [002/FR-028](002-supplier-verification-core/spec.md) owns signed-in buyer access and private case isolation, clarified on 2026-10-16. Case-linked records and extension workflows retain that owner boundary; organization sharing and team roles are outside the first release.
- **Requirement revisions**: [002/FR-029](002-supplier-verification-core/spec.md) owns changes to confirmed requirements within the same case: reconfirmation, re-evaluation of affected claims and preservation of prior inputs, evidence and assessments. Extensions retain the assessed revision when using this shared contract.
- **Shortlist eligibility**: [002/FR-022](002-supplier-verification-core/spec.md) requires every buyer-required claim to be proven for a qualified shortlist entry. Suppliers needing more evidence are separate follow-up candidates; contradicted required claims exclude a supplier from both lists. An empty qualified shortlist is an explicit valid result.
- **Certificate documents**: 002 owns supplier certificate reading. 004 owns buyer BOM/spec/drawing interpretation. Outreach reuses 002 for supplier attachments.
- **Persistence**: 002/FR-020 owns durable case state. Outreach adds its own drafts, approvals and wait records using that behavior.
- **Retention and deletion**: [002/FR-031](002-supplier-verification-core/spec.md) retains completed cases and their reports, uploads and history until the owning buyer explicitly deletes the case, with no automatic expiry. Extensions must honor case deletion and prevent pending work from recreating deleted records; planning defines storage and backup purge behavior.
- **Country boundaries**: 002 owns shared country-pack behavior and India coverage; 008 owns the second-country demonstration. A thin pack does not weaken shared proof requirements.
- **Local-first budget and genuine data**: [002/FR-032–033](002-supplier-verification-core/spec.md) records the user's2026-10-17 direction: build locally with no required paid APIs/models, AWS/LocalStack or hosting, using free-tier/local inference, permitted scraping and actual official-source imports. Application/acceptance data must be real-world, with no seeded demo suppliers, synthetic datasets or fabricated responses. Future feature plans must honor these preferences; hosting/paid integrations are deferred until explicitly revisited.
- **Source availability**: access methods, rights, fields and actual free-project quotas require research. Replays use faithfully captured real records with attribution/dates and must never be presented as live retrieval. Missing downloads remain unavailable rather than replaced by invented rows.
- **Automatic collection and blocked work**: [002/FR-009, FR-012, FR-014 and FR-030](002-supplier-verification-core/spec.md) own unattended scraping/source collection and isolation of blocked checks. A collection failure triggers permitted automatic alternatives or an explicit evidence gap, without mandatory buyer portal lookups; independent checks continue. Buyer-uploaded document corrections may pause only affected work. This clarification supersedes earlier manual-registry fallback wording in the core; dependent plans must consume this contract.
- **Technical preferences**: the [transcript](../transcript.md) and baseline retain the agreed React, FastAPI, LangGraph/persistent case-state, Gemini-or-local-model and self-hosted speech preferences. These are planning context, not evidence of implementation; feature specs describe user behavior without prescribing libraries or service interfaces.
- **Requirement authority**: use the delivery spec for work in that feature and the core for shared rules. Original baseline IDs below are provenance references, not a second mutable requirements set. Changes that alter product scope must update the affected spec and traceability together.

## Planning order and active feature

Begin with 002. Once its shared contracts are planned, discovery, PDF intake, outreach and voice can be planned separately; monitoring and the second-country demonstration also depend on the core but do not require all the intake extensions. Monitoring's contact action depends on outreach only if email is chosen.

After this split, `.specify/feature.json` selects `specs/002-supplier-verification-core` so the next feature command targets the core. To work on a different feature, set its `feature_directory` to the exact directory in the table before running the next Spec Kit command. A branch name does not select the feature.

Constitution v1.0.0 was adopted on 2026-10-16; each feature plan must assess compliance. The 002 clarification pass recorded five answers. Its [plan](002-supplier-verification-core/plan.md), [research](002-supplier-verification-core/research.md), [data model](002-supplier-verification-core/data-model.md), [contracts](002-supplier-verification-core/contracts/http-api.md) and [validation guide](002-supplier-verification-core/quickstart.md) were revised on2026-10-17 for local-first, zero-required-spend, real-world-data-only operation. The [task list](002-supplier-verification-core/tasks.md) now contains 102 implementation/validation tasks (20 complete, 82 unchecked) grouped into setup, foundation, three stories and final verification. Actual source coverage/local-model quality remain to be validated; no paid credentials are a prerequisite and setup and foundation are implemented; the supplier-verification stories remain pending. The 2026-10-19 remediation aligns full30-supplier SC-003 timing, restored-session invalidation, lifecycle nullability and physical managed-snapshot purge. The read-only `$speckit-analyze` review found47/47 requirements covered and no critical issues. T012's timestamp failure is fixed; `$speckit-implement` completed T001–T020 with45 backend/4 frontend tests and local preflight passing; see [implementation progress](002-supplier-verification-core/implementation-progress.md). Task markers and executed evidence govern readiness.

## Baseline functional requirement traceability

IDs are feature-local: `002/FR-001` and `003/FR-001` are distinct. Every baseline functional requirement has an implementation owner below. Repeated target rows within one owner decompose a compound baseline requirement. Baseline FR-005 is deliberately partitioned into shared/text intake, PDF upload and voice input; baseline FR-008 remains owned by the core and consumed by both input extensions.

| Baseline ID | Owning feature requirement(s) | Shared consumers / notes |
|---|---|---|
| FR-001 | [002/FR-001](002-supplier-verification-core/spec.md) | — |
| FR-002 | [002/FR-002](002-supplier-verification-core/spec.md) | — |
| FR-003 | [006/FR-001](006-voice-intake/spec.md), [006/FR-002](006-voice-intake/spec.md), [006/FR-003](006-voice-intake/spec.md) | — |
| FR-004 | [006/FR-004](006-voice-intake/spec.md) | — |
| FR-005 | [002/FR-003](002-supplier-verification-core/spec.md), [004/FR-001](004-pdf-drawing-intake/spec.md), [004/FR-006](004-pdf-drawing-intake/spec.md) | Partitioned intake: core owns text/shared contract, 004 owns PDF upload; 006/FR-001–005 provides voice using that contract. |
| FR-006 | [004/FR-002](004-pdf-drawing-intake/spec.md), [004/FR-007](004-pdf-drawing-intake/spec.md) | — |
| FR-007 | [004/FR-003](004-pdf-drawing-intake/spec.md), [004/FR-004](004-pdf-drawing-intake/spec.md) | — |
| FR-008 | [002/FR-004](002-supplier-verification-core/spec.md) | [004/FR-005](004-pdf-drawing-intake/spec.md), [006/FR-005](006-voice-intake/spec.md) |
| FR-009 | [002/FR-005](002-supplier-verification-core/spec.md) | — |
| FR-010 | [002/FR-006](002-supplier-verification-core/spec.md) | — |
| FR-011 | [003/FR-001](003-supplier-discovery-index/spec.md), [003/FR-003](003-supplier-discovery-index/spec.md) | — |
| FR-012 | [003/FR-004](003-supplier-discovery-index/spec.md) | — |
| FR-013 | [003/FR-005](003-supplier-discovery-index/spec.md) | — |
| FR-014 | [003/FR-002](003-supplier-discovery-index/spec.md) | — |
| FR-015 | [003/FR-009](003-supplier-discovery-index/spec.md) | — |
| FR-016 | [003/FR-010](003-supplier-discovery-index/spec.md) | — |
| FR-017 | [003/FR-011](003-supplier-discovery-index/spec.md) | — |
| FR-018 | [002/FR-007](002-supplier-verification-core/spec.md) | — |
| FR-019 | [002/FR-008](002-supplier-verification-core/spec.md) | — |
| FR-020 | [002/FR-009](002-supplier-verification-core/spec.md) | — |
| FR-021 | [002/FR-010](002-supplier-verification-core/spec.md) | — |
| FR-022 | [002/FR-011](002-supplier-verification-core/spec.md) | — |
| FR-023 | [002/FR-012](002-supplier-verification-core/spec.md) | — |
| FR-024 | [002/FR-013](002-supplier-verification-core/spec.md) | — |
| FR-025 | [002/FR-014](002-supplier-verification-core/spec.md) | — |
| FR-026 | [002/FR-015](002-supplier-verification-core/spec.md) | — |
| FR-027 | [002/FR-016](002-supplier-verification-core/spec.md) | — |
| FR-028 | [002/FR-017](002-supplier-verification-core/spec.md) | — |
| FR-029 | [002/FR-018](002-supplier-verification-core/spec.md) | — |
| FR-030 | [002/FR-019](002-supplier-verification-core/spec.md) | — |
| FR-031 | [005/FR-001](005-supplier-outreach-followup/spec.md) | — |
| FR-032 | [005/FR-002](005-supplier-outreach-followup/spec.md), [005/FR-003](005-supplier-outreach-followup/spec.md), [005/FR-008](005-supplier-outreach-followup/spec.md) | — |
| FR-033 | [002/FR-020](002-supplier-verification-core/spec.md) | [005/FR-004](005-supplier-outreach-followup/spec.md) |
| FR-034 | [005/FR-005](005-supplier-outreach-followup/spec.md), [005/FR-006](005-supplier-outreach-followup/spec.md) | — |
| FR-035 | [005/FR-007](005-supplier-outreach-followup/spec.md) | — |
| FR-036 | [002/FR-021](002-supplier-verification-core/spec.md) | — |
| FR-037 | [002/FR-022](002-supplier-verification-core/spec.md) | — |
| FR-038 | [002/FR-023](002-supplier-verification-core/spec.md) | — |
| FR-039 | [007/FR-001](007-approved-supplier-monitoring/spec.md), [007/FR-012](007-approved-supplier-monitoring/spec.md) | — |
| FR-040 | [007/FR-002](007-approved-supplier-monitoring/spec.md), [007/FR-003](007-approved-supplier-monitoring/spec.md), [007/FR-009](007-approved-supplier-monitoring/spec.md) | — |
| FR-041 | [007/FR-004](007-approved-supplier-monitoring/spec.md), [007/FR-005](007-approved-supplier-monitoring/spec.md) | — |
| FR-042 | [003/FR-006](003-supplier-discovery-index/spec.md) | — |
| FR-043 | [003/FR-007](003-supplier-discovery-index/spec.md) | — |
| FR-044 | [003/FR-008](003-supplier-discovery-index/spec.md) | — |
| FR-045 | [002/FR-024](002-supplier-verification-core/spec.md) | [008/FR-004](008-second-country-verification/spec.md), [008/FR-007](008-second-country-verification/spec.md) |
| FR-046 | [002/FR-025](002-supplier-verification-core/spec.md) | — |
| FR-047 | [008/FR-001](008-second-country-verification/spec.md), [008/FR-002](008-second-country-verification/spec.md), [008/FR-003](008-second-country-verification/spec.md), [008/FR-006](008-second-country-verification/spec.md) | — |
| FR-048 | [002/FR-026](002-supplier-verification-core/spec.md) | [008/FR-005](008-second-country-verification/spec.md) |
| FR-049 | [002/FR-027](002-supplier-verification-core/spec.md) | [008/FR-005](008-second-country-verification/spec.md) |
| FR-050 | [007/FR-006](007-approved-supplier-monitoring/spec.md), [007/FR-007](007-approved-supplier-monitoring/spec.md), [007/FR-008](007-approved-supplier-monitoring/spec.md), [007/FR-009](007-approved-supplier-monitoring/spec.md) | — |

## Baseline success criterion traceability

These are specified acceptance targets, not measured achievements. The shared intake timing criterion is partitioned by input mode, and the country-extension criterion has a core contract plus a second-country demonstration.

| Baseline ID | Delivery criterion(s) | Notes |
|---|---|---|
| SC-001 | [002/SC-001](002-supplier-verification-core/spec.md) | Initial-report timing excludes human/supplier waits; failures remain visible. |
| SC-002 | [002/SC-002](002-supplier-verification-core/spec.md) | 30-supplier auditor comparison, with per-verdict breakdown. |
| SC-003 | [002/SC-003](002-supplier-verification-core/spec.md) | Under one hour of active buyer time for every supplier in the same30-supplier evaluation; the estimated manual baseline is not asserted as measured. |
| SC-004 | [003/SC-001](003-supplier-discovery-index/spec.md) | Eight candidates from two independent origins on documented queries with sufficient coverage; shortfalls are explicit. |
| SC-005 | [002/SC-004](002-supplier-verification-core/spec.md), [004/SC-001](004-pdf-drawing-intake/spec.md), [006/SC-002](006-voice-intake/spec.md) | Text, document and voice intake each retain a five-minute bounded acceptance journey. |
| SC-006 | [002/SC-005](002-supplier-verification-core/spec.md) | Every verdict has reasoning and evidence or a real check attempt; failed checks are never fabricated citations. |
| SC-007 | [002/SC-006](002-supplier-verification-core/spec.md), [005/SC-002](005-supplier-outreach-followup/spec.md) | Core restart survival plus outreach-specific multi-day state retention. |
| SC-008 | [002/SC-007](002-supplier-verification-core/spec.md) | Three of four curated trader-warning patterns, without treating indicators as proof. |
| SC-009 | [006/SC-001](006-voice-intake/spec.md) | Five-second transcript display for 95/100 bounded English recordings; other workloads are reported separately. |
| SC-010 | [002/SC-008](002-supplier-verification-core/spec.md), [008/SC-001](008-second-country-verification/spec.md) | Core extension boundary plus actual second-country and India-regression demonstration. |

## Original user journeys

| Baseline journey | Delivery spec |
|---|---|
| US1 — Verify known suppliers | [002](002-supplier-verification-core/spec.md) |
| US2 — Discover suppliers | [003](003-supplier-discovery-index/spec.md) |
| US3 — Parse buyer PDFs | [004](004-pdf-drawing-intake/spec.md) |
| US4 — Multi-day outreach | [005](005-supplier-outreach-followup/spec.md) |
| US5 — Voice intake | [006](006-voice-intake/spec.md) |
| US6 — Monitoring | [007](007-approved-supplier-monitoring/spec.md) |
| Baseline FR-047 / SC-010 — Second country | [008](008-second-country-verification/spec.md) |
