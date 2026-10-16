# Feature Specification: VeriSource — Second-Country Verification

**Feature Branch**: Not created; no branch hook is configured.

**Created**: 2026-10-16

**Status**: Draft

**Input**: User description: "Split the thin second-country demonstration into a US country pack that verifies supplier registration and certification through the shared case/evidence/verdict workflow without changing that workflow."

**Feature Directory**: `specs/008-second-country-verification`

**Source**: [Product baseline](../001-supplier-verification-agent/spec.md); [ownership and dependency map](../README.md).

A buyer selects the United States for a known-list case and receives attributable legal-registration and certificate assessments using the same conversation, evidence policy and report as India cases. The initial demonstration covers one named US state, with California as the documented default; unsupported checks remain explicit.

**Dependencies**: The [verification core](../002-supplier-verification-core/spec.md) must provide its country-pack boundary and shared evidence policy. This feature exercises that boundary; US discovery directories, outreach, voice, drawing intake and monitoring are not required for its acceptance.

Requirement IDs are local to this feature. The ownership map preserves links to all baseline IDs.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Verify a supplier using the second country's sources (Priority: P1)

A buyer opens a US case for a supplier in the demonstration state. Legal identity is checked against the applicable public company registry and certification against IAF CertSearch when available, then reported using the core's verdicts.

**Why this priority**: A real second jurisdiction demonstrates that India-specific assumptions are not embedded in shared verification.

**Independent Test**: Run a known-list case using labeled state-registration and certification observations and inspect the same report shape used for India.

**Acceptance Scenarios**:

1. **Given** the buyer selects United States and the demonstration state, **When** the buyer confirms supplier identity and part requirements, **Then** the case records that jurisdiction and uses its country-specific source rules rather than requesting India-only identifiers.
2. **Given** matching legal-registration and certificate observations are available, **When** verification completes, **Then** the shared report displays proven, unproven or contradicted assessments with attributable sources and the same proof rules used in India.
3. **Given** a registry result identifies a same-name company with a different identity/site, **When** matching runs, **Then** the system flags the ambiguity and does not transfer unrelated evidence.
4. **Given** a certificate cannot be checked because access is unavailable, **When** the case report is produced, **Then** the affected claim is unproven with an inspectable failed attempt rather than silently omitted.

---

### User Story 2 - Show honest coverage boundaries (Priority: P2)

The buyer sees which jurisdiction and claim types the thin pack supports, including when a requested US location or compliance check is outside that coverage.

**Why this priority**: A thin demonstration must not imply complete US-wide legal or regulatory verification.

**Independent Test**: Request an unsupported state and an unsupported compliance claim, then inspect the case report for explicit limitations and preserved claims.

**Acceptance Scenarios**:

1. **Given** a requested state is outside the pack's declared coverage, **When** verification starts, **Then** the buyer sees the jurisdiction limit and can provide attributable official evidence or leave the affected claim unproven.
2. **Given** a requested regulatory or capacity claim lacks a supported country source, **When** the checklist is evaluated, **Then** the claim remains visible with its missing-evidence reason and is not relabeled as unnecessary simply because the pack lacks a check.
3. **Given** a human provides an official result for an unsupported automated check, **When** the result is added, **Then** the core applies its normal identity, currency, provenance and proof criteria without an exception for that country.

---

### User Story 3 - Demonstrate the shared country boundary (Priority: P3)

The team accepts the second pack only if the same case workflow and evidence policy work for both India and the US demonstration.

**Why this priority**: The architectural claim must be checked through an actual cross-country demonstration.

**Independent Test**: Compare the shared workflow before and after adding the country-specific sources/rules and run paired India and US acceptance cases.

**Acceptance Scenarios**:

1. **Given** the India core is accepted and the US country-specific rules are added, **When** paired cases are run, **Then** the same intake, confirmation, evidence history, verdict meanings and report behavior are used for both countries.
2. **Given** the country extension is reviewed, **When** the change set is examined, **Then** all additions required for the second country are limited to country-specific registry checks, jurisdiction/identity rules and configuration; shared case, evidence and verdict behavior is unchanged.
3. **Given** an India acceptance case is repeated after the extension, **When** its report is reviewed, **Then** its confirmation rules, source-failure handling, proof thresholds and verdict outcomes remain unchanged for the same evidence.

### Edge Cases

- A supplier operates in several states or countries: retain the selected legal entity and production-site jurisdiction rather than merging all companies with a similar name.
- A public registry is blocked or unavailable: retain the failed attempt and permit attributable human-provided results.
- An India-specific identifier is absent from a US case: do not infer invalid legal existence from an inapplicable identifier.
- A certificate's legal entity and production site differ from the selected supplier: preserve the discrepancy for core identity review.
- The pack does not support a compliance domain: show the unproven assessment and coverage limit instead of claiming compliance.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a thin United States country pack with an explicitly declared state/jurisdiction coverage list and supported claim/source descriptions visible to the buyer.
- **FR-002**: System MUST support legal-name, identity, status and address lookup from the applicable public company registry for the demonstration state through permitted access or attributable user-supplied official results.
- **FR-003**: System MUST support IAF CertSearch certificate checks for US suppliers when available, using the core's certificate identity, status, scope and site proof rules.
- **FR-004**: System MUST route selected-jurisdiction registry, compliance, identity/address and red-flag rules through the core's country-specific boundary, without requiring India-only identifiers for US cases.
- **FR-005**: System MUST reuse the core's confirmed intake, claim customization, proof policy, evidence/attempt history, verdict meanings, human-action handling and report behavior without country-specific exceptions to proof thresholds.
- **FR-006**: System MUST expose unsupported states, claim types and unavailable sources; affected claims MUST remain visible and unproven when proof criteria cannot be met, with human-provided evidence still subject to the shared policy.
- **FR-007**: The second country MUST be added using only country-specific registry checks, jurisdiction rules and configuration; shared case, evidence and verdict behavior MUST remain unchanged.
- **FR-008**: System MUST preserve existing India verification behavior when the second pack is added and demonstrate paired cases for the same standard claim/report concepts.

### Key Entities

- **Country Coverage**: Supported country/state, claim types, authoritative source references and known access limitations.
- **Jurisdiction-Specific Supplier Identity**: Legal entity and production-site identity interpreted under the selected jurisdiction.
- **Country-Specific Observation**: Registration or certificate evidence evaluated by the existing core policy.
- **Paired Acceptance Case**: India and US cases demonstrating the same shared confirmation, evidence and report behavior.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A review of the complete second-country change set finds zero changes to shared case, evidence or verdict behavior; the demonstration requires only country-specific checks, jurisdiction rules and configuration.
- **SC-002**: At least one India case and three US supplier cases in the demonstration state complete the shared workflow, with all standard claims shown and 100% of verdict cells containing reasoning and evidence or check-attempt references.
- **SC-003**: The US acceptance set exercises proven, unproven and contradicted legal/certificate assessments under the same proof meanings as the India set; no supplier's self-report or unavailable lookup is automatically proven.
- **SC-004**: Every unsupported-jurisdiction and unavailable-source trial displays the coverage gap and preserves the affected claim; zero inapplicable India-only identifiers are demanded in the US flow.
- **SC-005**: Repeating the existing India acceptance cases against unchanged evidence after adding the second pack produces the same confirmation requirements, verdicts and source-failure outcomes.

## Assumptions

- The baseline suggested the US as the thin second pack. California is the initial demonstration-state default; this is a scope choice, not a claim that any specific live access method has been verified. Changing that state must update the declared coverage and acceptance corpus together.
- Public registry permissions, available fields, supported access methods, certificate access and costs must be researched during planning. Controlled fixtures must be labeled and cannot be represented as live successful verification.
- The demonstration covers legal-registration and certificate evidence in the declared state. It does not claim complete federal/state regulatory coverage or a US supplier discovery index.
- Shared capability and capacity criteria remain applicable even if the thin pack has insufficient corroborating sources; unproven is an honest outcome.
- Architecture-specific proof for SC-001 is supplied by implementation-change review, while paired buyer journeys verify that shared behavior remains consistent.
- This is a draft specification, not a claim of implementation. The project constitution is still a template; adopting principles is a separate project step before constitution alignment can be established. Plans and task coverage have not been validated.
