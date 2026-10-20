<!--
Sync Impact Report
Version change: unratified template -> 1.0.0 (initial project constitution)
Modified principles:
- PRINCIPLE_1_NAME -> I. Evidence Before Verdicts
- PRINCIPLE_2_NAME -> II. Buyer-Controlled Decisions and Communication
- PRINCIPLE_3_NAME -> III. Durable, Auditable Case State
- PRINCIPLE_4_NAME -> IV. Scoped Features and Shared Verification Rules
- PRINCIPLE_5_NAME -> V. Verifiable Behavior and Honest Readiness
Added sections:
- Product and Engineering Constraints
- Development Workflow and Quality Gates
- Project-specific governance and amendment rules
Removed sections: template examples and unused placeholder instructions
Deferred placeholders: none
Follow-up review: assess delivery specs and their historical constitution-status notes
during clarification/planning; this workflow does not rewrite dependent artifacts.
Scope: only .specify/memory/constitution.md is changed by this workflow.
This report is temporary amendment-review material, not governance content.
Remove this comment before committing the amended constitution.
-->

# VeriSource Constitution

## Core Principles

### I. Evidence Before Verdicts

Every evaluated supplier claim MUST have exactly one verdict: `proven`, `unproven`,
or `contradicted`. Processing states and failed-check reasons MUST remain separate.
A verdict MUST identify the assertion, relevant entity/site and period, proof criteria,
reasoning, and attributable evidence. Where no evidence was retrieved, an `unproven`
verdict MUST link to actual check attempts and the missing-evidence reason.

The supplier verification core's Evidence and Verdict Policy MUST govern all countries,
intake methods, supplier replies and re-evaluations. Missing evidence, blocked access,
fuzzy name similarity, or differing office/factory addresses alone MUST NOT establish
proof or contradiction. Supplier assertions and repeated copies of one source MUST NOT
be presented as independent corroboration.

Evidence MUST retain source references, observations or excerpts, collection times and
available issue, expiry or effective dates. Unresolved identity, currency and source
conflicts MUST remain visible. Facts that may change, including source access, quotas,
pricing and supported searches, MUST be checked against current authoritative sources
during research and recorded with references and check dates. Unavailable or unverified
facts MUST be labeled as such; they MUST NOT be invented.

Rationale: the product supports decisions through inspectable evidence, including
honest uncertainty when a supplier's capabilities cannot be established.

### II. Buyer-Controlled Decisions and Communication

Requirements obtained from text, voice or buyer documents MUST be editable and explicitly
confirmed before claim generation. Only confirmed values may enter verification.
Uncertainty highlighting MUST remain a review aid, with the whole interpreted input
editable; unhighlighted content MUST NOT be implied to be guaranteed correct.

Every outgoing supplier message, including each follow-up, MUST have explicit buyer
approval tied to its exact recipient, content and attachments. A changed message MUST
require fresh approval. Skipping or rejecting outreach MUST send nothing and MUST
allow closure with unresolved claims.

The buyer MUST retain the final supplier selection and approval decision. A shortlist,
monitoring alert or model-generated recommendation MUST NOT silently approve a supplier,
send a message, or rewrite a closed assessment. Human-assisted registry checks MUST
preserve attributable results without bypassing access controls.

Rationale: interpretation and recommendations assist the buyer while external actions
and business decisions remain under the buyer's control.

### III. Durable, Auditable Case State

Confirmed inputs, supplier identities, claims, evidence, check attempts, assessment
history and pending human actions MUST survive browser closure and service restarts.
Features that wait for replies or scheduled work MUST preserve their pending state
across multi-day delays.

Re-evaluation MUST retain prior evidence and verdict reasoning. Retried reply handling
MUST avoid duplicate evidence events; interrupted sends with uncertain outcomes MUST be
reconciled before another send is attempted. Source failures MUST remain distinguishable
from successful checks and substantive certificate or regulatory changes.

Buyer documents, recordings, case records and connected email credentials MUST be
accessible only to authorized case participants and required services. Credentials MUST
NOT be committed to source control or included in evidence excerpts or routine logs.
Plans MUST define access boundaries and handling of these records before implementation.

Rationale: long-running verification is only useful when its state and provenance
remain trustworthy through interruptions and later review.

### IV. Scoped Features and Shared Verification Rules

Implementation work MUST be governed by its owning delivery feature spec. The frozen
product baseline MUST remain a historical reference; the specification map MUST record
ownership and traceability when a delivery requirement changes.

Shared confirmation, evidence, verdict and durable-case rules MUST have one maintained
owner in the verification core. PDF intake, voice, discovery, outreach and monitoring
MUST consume those rules rather than establish conflicting alternatives. Supplier
certificate reading and buyer BOM/drawing interpretation MUST remain distinct
responsibilities.

Country-specific registry, compliance, identity/address and red-flag rules MUST use the
shared country-pack boundary. Country expansion MUST NOT require changes to shared case,
evidence or verdict behavior or weaken proof thresholds. Unsupported country or claim
coverage MUST be shown explicitly.

Each feature MUST have a bounded acceptance journey. New abstractions, dependencies and
cross-feature changes MUST be justified by an existing requirement or demonstrated
integration need; future scope MUST NOT be silently added as mandatory work.

Rationale: feature separation enables incremental delivery while keeping the product's
verification semantics consistent.

### V. Verifiable Behavior and Honest Readiness

A feature MUST be described as implemented only when its required behavior has been
demonstrated with recorded acceptance evidence. Specifications, checked quality
checklists, planned integrations and generated code alone MUST NOT count as proof of
working functionality.

Verification MUST cover consequential behavior appropriate to the change: proof and
identity rules, confirmation and approval gates, restart recovery, source failures,
reply association, monitoring changes and cross-country consistency where applicable.
Tests MUST exercise observable outcomes and failure boundaries rather than merely
mirror implementation details. Documentation-only or other low-impact changes MAY use
focused structural and reference checks.

Performance reports MUST state their workload, deployment and measurement conditions.
Results outside the agreed workload MUST be reported separately. Fixtures, simulated
time and mocked sources MUST be labeled; they MUST NOT be represented as successful
live access or real supplier evidence.

Rationale: reliable evaluation and accurate status reporting prevent prototypes and
partial integrations from being mistaken for completed verification capabilities.

## Product and Engineering Constraints

- VeriSource MUST support both a buyer-provided supplier list and discovery without a
  list, through the delivery features that own those journeys.
- The product MUST use a conversational interface with interactive supplier, evidence
  and approval components. Voice and PDF/drawing input MUST preserve the common
  correction and confirmation gate.
- India is the initial complete country pack. A thin second-country demonstration MUST
  state its jurisdiction and claim coverage instead of implying global completeness.
- Source collection MUST respect verified access permissions, access controls and
  collection limits. A pasted supplier identifier MUST NOT imply permission to
  automate access to its originating service.
- Planning MUST document actual source availability and combined discovery,
  verification and monitoring capacity. No trial, free tier or public listing may be
  assumed to provide sufficient access without verification.
- The transcript's React, FastAPI, LangGraph with durable persistence, Gemini-or-local
  model and project-controlled speech preferences MUST be considered during planning.
  Plans MUST record concrete technology choices and explain departures in terms of
  requirements, source access, cost or deployment evidence; product proof rules MUST
  remain independent of the chosen model or framework.
- The product MUST display unavailable data, uncertain interpretation and source
  coverage limitations without inventing successful checks, capabilities or results.

## Development Workflow and Quality Gates

Work MUST proceed against a selected delivery feature with explicit dependencies.
Feature selection MUST identify the exact feature directory; branch names alone MUST
NOT determine scope. Concurrent work on separate features MUST preserve ownership and
shared contracts.

Before implementation of a feature:

1. Review its specification, shared dependencies and quality checklist; resolve
   material ambiguities through clarification.
2. Produce an implementation plan with current-source research, data relationships,
   interface contracts where applicable, and reproducible validation scenarios.
3. Evaluate the plan against every applicable constitutional principle before and
   after design. Violations MUST be resolved through compliant design or a separate
   explicit constitution amendment.
4. Generate dependency-ordered tasks that cover the feature's requirements and
   buildable success criteria.
5. Analyze specification, plan and task consistency. Critical conflicts and missing
   baseline functionality MUST be resolved before the affected implementation starts.

During implementation, changes MUST remain traceable to the selected feature and
applicable shared contracts. Run the checks needed to validate changed behavior and
report their actual results. Update affected delivery specs and the ownership map
when an explicitly authorized scope change alters their contract; preserve the
historical product baseline.

Completion reports MUST distinguish specified, planned, implemented, tested, simulated
and unavailable behavior. Remaining failures or unverified live integrations MUST
remain visible. Performance and evidence-quality targets MUST be reported as targets
until measured under their documented acceptance conditions.

## Governance

This constitution governs project specifications, plans, tasks and implementation.
Templates, tool defaults and example comments MUST NOT override adopted principles.
Feature-specific evidence-policy details MUST conform to these principles.

An amendment MUST be explicit and adopted by the project maintainer(s), state the
reason for the change, identify affected principles and artifacts, and describe any
required migration or revalidation. A feature implementation MUST NOT silently amend
or reinterpret a principle to avoid a conflict.

Constitution versions use semantic versioning:

- MAJOR for incompatible removal or redefinition of a principle.
- MINOR for a new principle or materially expanded governance.
- PATCH for clarifications that do not change normative obligations.

Every amendment MUST update the version and last-amended date. The original
ratification date MUST be preserved. Plans and substantive change reviews MUST state
their constitutional compliance or identify the specific unresolved conflict.
Dependent artifacts MUST be reviewed when an amendment changes obligations; templates
MUST NOT be rewritten automatically by the constitution workflow.

**Version**: 1.0.0 | **Ratified**: 2026-10-16 | **Last Amended**: 2026-10-16
