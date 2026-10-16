# Feature Specification: VeriSource — Supplier Verification Core

**Feature Branch**: Not created; no branch hook is configured.

**Created**: 2026-10-16

**Status**: Draft

**Input**: User description: "Split the agreed baseline into a text-first, India-capable verification workflow that produces evidence-backed supplier assessments and reports without requiring discovery, voice, drawing intake, outreach, or monitoring to be installed."

**Feature Directory**: `specs/002-supplier-verification-core`

**Source**: [Product baseline](../001-supplier-verification-agent/spec.md); [ownership and dependency map](../README.md).

A buyer enters a part requirement and known supplier identifiers, confirms the case, reviews claims and evidence, and receives a shortlist. This feature owns the conversation shell, confirmed intake, durable case history, certificate-document reading, India checks, and shared country-specific verification boundary. Other features extend this workflow without changing its evidence rules.

**Dependencies**: No other delivery feature is needed for the core acceptance journey. The [product baseline](../001-supplier-verification-agent/spec.md) records agreed planning preferences; external registry access must be researched before live integration.

Requirement IDs are local to this feature. The ownership map preserves links to all baseline IDs.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Confirm requirements and verify a known supplier list (Priority: P1)

A purchase manager enters CF8M impeller castings, 2,000 pieces per month and required certifications, then adds four supplier names, websites or GST identifiers. She corrects the interpreted requirements and approves the claim checklist before evidence gathering.

**Why this priority**: This is the complete verification journey on which every other capability depends.

**Independent Test**: Enter a text requirement and four suppliers, confirm the case, exercise available sources and human-assisted checks, and inspect the resulting claims without using email or discovery.

**Acceptance Scenarios**:

1. **Given** a vague requirement such as steel parts, **When** the buyer starts intake, **Then** the conversation asks for missing material, process, quantity or certification details instead of inventing them.
2. **Given** text requirements and four supplier identifiers have been entered, **When** the system presents its interpretation, **Then** the buyer can correct requirements and identifiers, including pasted listing links, before any claim generation.
3. **Given** country, region, city or radius preferences are supplied, **When** the buyer confirms the case, **Then** the confirmed preferences are retained with the supplier list.
4. **Given** the confirmed case is ready, **When** the system proposes its checklist, **Then** it covers existence, manufacturer classification, part capability, certificate validity/accreditation/scope/site, applicable compliance and capacity plausibility as separately evaluable assertions.
5. **Given** the proposed checklist is visible, **When** the buyer adds, edits or removes a claim, **Then** the confirmed checklist and proof criteria control subsequent evidence collection.
6. **Given** supplier websites, certificate PDFs and official registry results are available, **When** the evidence run proceeds, **Then** website product/process/facility/address observations and certificate identifiers, issuer, standard, scope, site and expiry fields are recorded with provenance and India registration and QCO checks are attempted.
7. **Given** a legal lookup or document check requires human assistance, **When** the system requests a portal result or unlocked document, **Then** the case pauses with a clear requested action and resumes using the returned attributable evidence without bypassing access controls.

---

### User Story 2 - Inspect evidence and make a supplier decision (Priority: P2)

The buyer compares claims in an expandable evidence table and sees why each is proven, unproven or contradicted. The system recommends a shortlist based on those records; the buyer makes the final choice.

**Why this priority**: Evidence-backed reasoning is the product's central decision support.

**Independent Test**: Evaluate curated examples covering each verdict and claim type, inspect source conflicts and identity ambiguity, and verify that the shortlist follows the displayed assessments.

**Acceptance Scenarios**:

1. **Given** evidence gathering has completed or recorded failures, **When** the report is displayed, **Then** each evaluated claim has exactly one permitted verdict, reasoning and evidence or check-attempt references in an interactive conversation table.
2. **Given** only a supplier website or unsupported headcount estimate asserts manufacturing or capacity, **When** the claim is evaluated, **Then** it remains unproven unless the Evidence and Verdict Policy's corroboration criteria are met.
3. **Given** a current authoritative record refutes the same certificate's claimed validity, **When** the system evaluates the matched certificate and site, **Then** the claim is contradicted and both records and their check times remain visible.
4. **Given** names vary in spelling or Indian address formatting, **When** records are compared, **Then** identity suggestions use available identifiers and address roles; unresolved identities are flagged for review, and fuzzy similarity alone does not prove a match.
5. **Given** a certificate covers a factory but a registration identifies its office elsewhere, **When** site matching runs, **Then** the system distinguishes office and factory roles and does not infer a contradiction from that address difference alone.
6. **Given** two records conflict or a registry is inaccessible, **When** the report is expanded, **Then** the buyer sees both records or the failed check, any unresolved identity/site/period issue and the evidence still needed.
7. **Given** all required subclaims satisfy their proof criteria, **When** a compound claim is assessed, **Then** it is proven; a qualifying refutation makes it contradicted, and otherwise incomplete or unresolved subclaims leave it unproven.
8. **Given** a shortlist is requested, **When** the system recommends suppliers, **Then** each recommendation refers to displayed verdicts and outstanding gaps, and the buyer can accept or reject the recommendation.

---

### User Story 3 - Resume a case and share its report (Priority: P3)

The buyer can leave a case during a human check, return after a service restart, close it with unproven claims, and download a report that preserves the evidence trail.

**Why this priority**: A usable assessment must survive interruptions and remain reviewable outside the conversation.

**Independent Test**: Interrupt and restart a case, compare retained state, complete the assessment without outreach, and compare the exported report to the conversation.

**Acceptance Scenarios**:

1. **Given** a case contains confirmed inputs, suppliers, claims, evidence, attempts, verdict history and a pending human action, **When** the browser closes and the service fully restarts, **Then** the buyer resumes with all those records and the requested action intact.
2. **Given** a case has unresolved claims, **When** the buyer closes it without contacting suppliers, **Then** the report retains the unproven verdicts and reasons without requiring the outreach feature.
3. **Given** the final table and shortlist are available, **When** the buyer downloads a PDF report, **Then** it contains the same supplier/claim verdicts, reasons, source references and check times, including missing-evidence attempt references.

### Edge Cases

- Supplier website access fails or encounters a CAPTCHA: record the failed attempt, try permitted alternate sources, and leave unsatisfied claims unproven.
- A certificate is password-protected: request an unlocked copy and preserve the pending action.
- Two supplier records share a GST identifier but other attributes conflict: flag the anomaly for review; do not silently merge them.
- A same-name company has a different legal identifier or production site: do not transfer its evidence to the selected supplier.
- Source dates are missing, expired or outside the claim period: display the currency problem and apply the evidence policy.
- A claim has no retrieved evidence at all: cite its actual check attempts, never an invented quotation or fourth verdict.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a natural-language conversation for intake, verification, human actions and report review.
- **FR-002**: System MUST display supplier information, claim checklists, expandable evidence tables and shortlist decisions as interactive components inside the conversation. Extension features MUST use the same conversation for their candidate and approval components.
- **FR-003**: System MUST accept typed part descriptions, material grades, processes, quantities/periods and certification requirements as the shared intake contract; missing required facts MUST prompt clarification.
- **FR-004**: System MUST present interpreted requirements for correction and explicit confirmation before generating claims. Text, PDF and voice intake MUST share this confirmation rule, and only confirmed values may enter verification.
- **FR-005**: System MUST accept supplier names, website URLs, GST identifiers and user-pasted IndiaMART listing links with the part specification. A pasted listing is an identifier and MUST NOT trigger automated access to that site.
- **FR-006**: System MUST retain confirmed country, region/state, city or radius preferences with the case.
- **FR-007**: System MUST propose per-supplier claims for legal existence/status, manufacturer classification, material/process/part capability, certificate validity/accreditation/scope/site, applicable compliance and capacity plausibility, separating required subclaims and stating proof criteria, entity/site and relevant period.
- **FR-008**: System MUST let the buyer add, remove or modify proposed claims and confirm their proof criteria before evidence collection starts.
- **FR-009**: System MUST collect supplier website product ranges, process descriptions, facility-photo references and addresses, preserving the source, extracted observation, check time and whether a statement is self-reported.
- **FR-010**: System MUST read supplier certificate PDFs and extract certificate number, certification body, standard, scope, production-site address and expiry date; missing or unreadable fields MUST remain explicit.
- **FR-011**: System MUST attempt certificate validation against IAF CertSearch when available and apply the Evidence and Verdict Policy if it is unavailable or insufficient.
- **FR-012**: System MUST obtain legal name, active status, registered business activity and address from applicable GST, Udyam or MCA sources through permitted access or an attributable user-provided official lookup.
- **FR-013**: System MUST assess the confirmed product against the current official BIS QCO requirements and record applicability and the basis for any required licence or finding that no licence is required.
- **FR-014**: System MUST request human help when a portal, CAPTCHA or missing/unreadable document prevents progress, retain the pending request, and resume after the buyer supplies a result. It MUST NOT bypass access controls.
- **FR-015**: System MUST propose cross-source identity matches using name variations and corroborating identifiers, expose ambiguous matches and conflicting identifiers for human review, and avoid treating fuzzy similarity as proof.
- **FR-016**: System MUST compare Indian address variations while preserving original addresses and distinguishing registered-office and production-site roles.
- **FR-017**: System MUST assign every evaluated claim exactly one verdict of proven, unproven or contradicted. Pending/checking states and access failure reasons MUST remain separate from verdicts.
- **FR-018**: System MUST link each verdict to reasoning and its evidence citations, including source URL/document, observation or quote and check time. An unproven claim with no retrieved evidence MUST instead link to inspectable check attempts; a failure MUST NOT be represented as retrieved evidence.
- **FR-019**: System MUST show conflicting records and whether they concern the same entity, site, assertion and period; unresolved discrepancies MUST remain visible without automatically becoming contradicted verdicts.
- **FR-020**: System MUST durably retain confirmed requirements, suppliers, claims, evidence, check attempts, verdict history and pending human actions across browser closure, full service restarts and multi-day waits, including waits introduced by outreach.
- **FR-021**: System MUST present an expandable supplier-by-claim verdict table in the conversation, with reasons, retrieved evidence and failed/missing-evidence attempts visible from each cell.
- **FR-022**: System MUST recommend a shortlist with reasoning tied to the displayed evidence and unresolved gaps; the buyer MUST retain the final selection decision.
- **FR-023**: System MUST provide a downloadable PDF evidence report preserving the table's verdicts, reasons, citations, check times and shortlist.
- **FR-024**: System MUST separate shared case, evidence and verdict behavior from country-specific registry, compliance, address and red-flag rules. Adding a country pack MUST NOT require changing that shared behavior.
- **FR-025**: System MUST provide the India country pack covering GST/Udyam registration checks, BIS applicability, Indian address comparison and evidence-based manufacturer/trader assessment, with MCA used where applicable.
- **FR-026**: System MUST apply the Evidence and Verdict Policy below to initial verification and every re-evaluation, including human-provided and supplier-response evidence; historical verdicts and their reasons MUST remain inspectable.
- **FR-027**: System MUST record each evidence-check attempt with its claim, targeted source/document, time, outcome and failure/missing-evidence reason where applicable. No-content attempts MUST remain distinct from evidence and contain no invented excerpts.

### Evidence and Verdict Policy

**Claim boundaries**: Compound checks MUST be separated into verifiable subclaims. Certificate validity, accreditation, scope coverage, and production-site match each receive a verdict; capability checks separate required material, process, tolerances, and volume where those requirements exist. A compound claim is `proven` only when all required subclaims are proven, `contradicted` when a required subclaim has qualifying contrary evidence, and otherwise `unproven`. It MUST show its subclaim results.

**Verdict meanings**:

- `proven`: Evidence satisfies every stated proof criterion for the identified entity/site and relevant period, with no unresolved conflicting evidence about that same assertion.
- `unproven`: Evidence is missing, inaccessible, insufficiently current, self-reported without required corroboration, or cannot resolve identity or a material source conflict. The reason and remaining evidence needed MUST be displayed.
- `contradicted`: Evidence directly refutes the specific assertion for the matched entity/site and period. Lack of evidence, failed access, a fuzzy match, or an unexplained address difference is insufficient.

**Minimum proof criteria**:

| Claim type | Evidence needed for `proven` | Insufficient on its own |
|---|---|---|
| Legal existence and active registration | A matching official registry result for the relevant jurisdiction and status, retrieved during the current verification run or supplied by the user with an attributable source and check time. | A company website, directory entry, or name similarity. |
| Manufacturer classification | Direct evidence of the relevant production activity at an identified site plus at least one independent, attributable record corroborating that activity at that site. | A self-declared business type, exporter listing, broad product catalogue, or facility photo. Exporting alone does not establish manufacturing. |
| Specific part capability | Evidence explicitly covering each required material, process, tolerance, and volume subclaim, tied to the supplier/site and corroborated by independent production, inspection, or buyer-acceptance records for the relevant requirement. | An ISO certificate, generic marketing language, or headcount estimate. Where corroboration is unavailable, retain self-reported capability as `unproven`. |
| Certificate validity, accreditation, scope, and site | A matching authoritative registry or issuer/accreditation-body confirmation, certificate identifiers, applicable standard and dates, and evidence for each scope/site subclaim. Check current status during the verification run. | An unverified certificate PDF or an inaccessible registry. Missing dates or ambiguous scope/site matches remain `unproven`. |
| Applicable regulatory compliance | An official requirement and applicability assessment for the confirmed product, jurisdiction, and relevant date; where a licence is required, a matching official licence record covering the product/site. Record the basis when no licence is required. | Failure to find an order, an unrelated licence, or an unsupported model assertion that no requirement applies. |
| Capacity plausibility | Dated production or delivery records tied to the relevant site/process and requested volume/period, corroborated by an attributable buyer, auditor, or equivalent independent record. | Headcount, machine counts, or supplier statements without evidence connecting them to the requested output. |

`Proven` describes the documented assertion under these criteria; it does not promise future delivery or successful production of an untested part. User-defined claims MUST have explicit, user-confirmed proof criteria and use the same verdict meanings.

**Source conflicts and freshness**: Authority is evaluated for the particular assertion: legal registries for registration, registry/issuer records for certificate status, and official orders for regulatory requirements. A current, identity-matched authoritative record may refute an older supplier assertion; both records and the reason MUST remain visible. An authoritative record for one assertion does not establish another. Conflicts that cannot be resolved by identity, site role, dates, or applicable authority remain `unproven`. Repeated copies of one source do not count as independent corroboration.

Every evidence record MUST retain the collection time and any source issue, expiry, or effective dates available. Registry status MUST be checked in the current verification run; documentary evidence MUST cover the period required by its claim. If validity or currency cannot be established, the affected claim remains `unproven`. Registered offices and production sites MUST be identified by role before comparing addresses; fuzzy matching proposes identity links and does not itself prove them.

### Key Entities

- **Case**: Confirmed part requirements, suppliers, locations, claims, evidence history, pending actions and report.
- **Supplier**: Company identity, identifiers, address roles and source attribution; a name match is not a confirmed identity.
- **Claim**: Assertion with proof criteria, entity/site, relevant period, subclaims, processing state and assessment history.
- **Evidence Record**: An attributable observation, source/document reference, snapshot, check time and available issue/expiry/effective dates.
- **Check Attempt**: A source/document check with its outcome and any failure reason, whether or not content was retrieved.
- **Verdict**: Proven, unproven or contradicted assessment with reasoning and evidence/attempt references.
- **Country Pack**: Country-specific sources, applicability, address rules and red-flag patterns used under shared evidence rules.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a confirmed part requirement and five named suppliers, an initial report is available within 30 minutes, excluding waits for human input or supplier replies. Every claim has a verdict and evidence/attempt references, with failures labeled accurately.
- **SC-002**: Verdicts agree with a human auditor on at least 80% of claims across 30 suppliers. The labeled evaluation includes all three verdicts and each standard claim type; report agreement by verdict as well as overall.
- **SC-003**: Across that evaluation, active buyer time per supplier is under one hour; measure the result rather than assuming the baseline's estimated manual workload has been established.
- **SC-004**: In five text-intake trials using a prepared part requirement and supplier list, each buyer can reach confirmed intake in under five minutes without assistance.
- **SC-005**: In every evaluated and exported verdict cell, reasoning and evidence or check-attempt references are inspectable; 100% of proven and contradicted verdicts have retrieved supporting evidence and no failed check has an invented excerpt.
- **SC-006**: A full service restart during collection, a pending human action and a multi-day wait loses none of the recorded confirmed inputs, evidence, attempts, verdict history or pending actions.
- **SC-007**: The system identifies at least three of four curated manufacturer/trader warning patterns: conflicting business activity, unresolved site inconsistency, unsupported catalogue breadth and unsupported capacity/headcount assertions. It flags them for evidence review without treating those indicators alone as conclusive proof.
- **SC-008**: The country extension boundary can accept the second-country feature's rules and evidence without changing shared case, evidence or verdict behavior; the second-country feature owns the demonstration.

## Assumptions

- Users are buyers using a modern browser with stable connectivity; offline operation is outside this baseline.
- Authoritative source access, supported queries, permissions, quotas and costs must be verified during planning; unavailable checks remain explicit. Simulated records must be visibly labeled.
- The Evidence and Verdict Policy in this feature is the maintained shared policy for all seven delivery features. The product baseline is retained for provenance.
- Text intake and certificate-document reading are sufficient for this feature's acceptance. Buyer BOM/drawing interpretation, discovery, email sending, voice and recurring monitoring are separate capabilities.
- Sample production, inspection or buyer-acceptance records may be provided by users. Missing independent corroboration is a valid unproven result.
- The four warning patterns in SC-007 are review indicators; direct EPFO collection and reverse-image checks were discussed in the transcript but were not mandated by the remediated baseline's functional requirements.
- This is a draft specification, not a claim of implementation. The project constitution is still a template; adopting principles is a separate project step before constitution alignment can be established. Plans and task coverage have not been validated.
