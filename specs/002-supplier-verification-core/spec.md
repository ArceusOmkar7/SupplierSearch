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

## Clarifications

### Session 2026-10-16

- Q: For the first release, who should be able to open and modify a verification case? → A: Each signed-in buyer owns private cases; other buyers cannot access them. Organization sharing and team roles are outside the first release.
- Q: How should a buyer change confirmed requirements after verification has started? → A: Create a new revision in the same case, reconfirm the changes and re-evaluate affected claims. Preserve previous results as history.
- Q: Which suppliers should qualify for the recommended shortlist? → A: Shortlist only suppliers whose buyer-required claims are all proven. If none qualify, say so and show suppliers needing more evidence separately as follow-up candidates; suppliers with contradicted required claims do not qualify.
- Q: When one check needs buyer help, should other checks continue? → A: Continue independent checks and pause only affected work and its dependencies. Scraping and external-source collection must run automatically without buyer intervention; try permitted alternatives when blocked and record unavailable checks and evidence gaps rather than requiring manual lookups.
- Q: How long should completed cases, reports and uploaded documents remain available? → A: Retain them until the owning buyer explicitly deletes the case; do not apply automatic time-based expiry.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Confirm requirements and verify a known supplier list (Priority: P1)

A purchase manager enters CF8M impeller castings, 2,000 pieces per month and required certifications, then adds four supplier names, websites or GST identifiers. She corrects the interpreted requirements and approves the claim checklist before evidence gathering.

**Why this priority**: This is the complete verification journey on which every other capability depends.

**Independent Test**: Enter a text requirement and four suppliers, confirm the case and claim checklist, run automatic source collection including an inaccessible-source scenario without buyer intervention, and inspect the resulting claims without using email or discovery.

**Acceptance Scenarios**:

1. **Given** a vague requirement such as steel parts, **When** the buyer starts intake, **Then** the conversation asks for missing material, process, quantity or certification details instead of inventing them.
2. **Given** text requirements and four supplier identifiers have been entered, **When** the system presents its interpretation, **Then** the buyer can correct requirements and identifiers, including pasted listing links, before any claim generation.
3. **Given** country, region, city or radius preferences are supplied, **When** the buyer confirms the case, **Then** the confirmed preferences are retained with the supplier list.
4. **Given** the confirmed case is ready, **When** the system proposes its checklist, **Then** it covers existence, manufacturer classification, part capability, certificate validity/accreditation/scope/site, applicable compliance and capacity plausibility as separately evaluable assertions.
5. **Given** the proposed checklist is visible, **When** the buyer adds, edits or removes a claim, **Then** the confirmed checklist and proof criteria control subsequent evidence collection.
6. **Given** supplier websites, certificate PDFs and official registry results are available, **When** the evidence run proceeds, **Then** website product/process/facility/address observations and certificate identifiers, issuer, standard, scope, site and expiry fields are recorded with provenance and India registration and QCO checks are attempted.
7. **Given** an external website, registry or certificate source is inaccessible or presents a CAPTCHA, **When** automatic collection encounters the restriction, **Then** the system records the attempt, tries permitted alternatives automatically and continues independent checks without requesting a manual lookup, CAPTCHA solution or pasted result from the buyer. If evidence remains unavailable, affected claims remain unproven with the gap displayed.
8. **Given** a buyer-uploaded certificate cannot be read and needs an unlocked or replacement copy, **When** the system requests that document, **Then** only the affected work and its dependencies pause; independent checks and available results continue, and the affected work resumes when the buyer supplies the document.
9. **Given** a legitimately obtained official export or public issuer document is available locally, **When** it is imported with its original source, publication/cutoff, licence and file provenance, **Then** known-supplier checks can use its actual records automatically while preserving historical/freshness limitations; importing it today does not establish current registry status.

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
8. **Given** a shortlist is requested, **When** the system recommends suppliers, **Then** only suppliers with every buyer-required claim proven for the assessed requirement revision appear on the qualified shortlist, with reasoning tied to displayed verdicts; the buyer can accept or reject the recommendation.
9. **Given** no supplier has every buyer-required claim proven, **When** the shortlist is displayed or exported, **Then** it explicitly states that no supplier qualifies and shows suppliers with unproven required claims and no contradicted required claims separately as follow-up candidates, with their evidence gaps. Suppliers with contradicted required claims remain visible in the assessment with their reasons and do not appear on either list.

---

### User Story 3 - Resume a case and share its report (Priority: P3)

The buyer can leave a case during a human check, return after a service restart, close it with unproven claims, and download a report that preserves the evidence trail.

**Why this priority**: A usable assessment must survive interruptions and remain reviewable outside the conversation.

**Independent Test**: Interrupt and restart a case, compare retained state, complete the assessment without outreach, and compare the exported report to the conversation.

**Acceptance Scenarios**:

1. **Given** a case contains confirmed inputs, suppliers, claims, evidence, attempts, verdict history and a pending human action, **When** the browser closes and the service fully restarts, **Then** the buyer resumes with all those records and the requested action intact.
2. **Given** a case has unresolved claims, **When** the buyer closes it without contacting suppliers, **Then** the report retains the unproven verdicts and reasons without requiring the outreach feature.
3. **Given** the final table and shortlist are available, **When** the buyer downloads a PDF report, **Then** it contains the same supplier/claim verdicts, reasons, source references and check times, including missing-evidence attempt references.
4. **Given** two signed-in buyers own separate cases, **When** either buyer lists, opens, modifies, resumes or exports cases or accesses their documents and evidence, **Then** only that buyer's own case data is accessible; signing out prevents access to all private case data, including through a previously obtained reference.
5. **Given** verification has started, **When** the buyer changes a confirmed material, quantity or certification requirement, **Then** the system creates a draft revision in the same case, requires explicit confirmation before using the changes, and re-evaluates affected claims against the confirmed revision. Earlier inputs, evidence and assessments remain inspectable as history; affected earlier verdicts are not presented as results for the changed requirements.
6. **Given** a completed case has not been deleted, **When** the owning buyer returns after 90 days or one year, **Then** the case, reports, uploaded documents and assessment history remain available without automatic expiry.
7. **Given** the owning buyer explicitly deletes a case, **When** deletion completes, **Then** the case and linked private records are unavailable through lists, direct references, document access and report export; pending work cannot recreate the deleted case, including after a service restart. Another buyer cannot delete the case.

### Edge Cases

- Supplier website or registry access fails or encounters a CAPTCHA: record the failed attempt, try permitted alternate sources automatically, and leave unsatisfied claims unproven if evidence remains unavailable. Do not require the buyer to scrape, browse a portal, solve a CAPTCHA or paste a lookup result.
- A buyer-uploaded certificate is password-protected: request an unlocked copy and preserve the pending action for affected work while independent checks continue. A password-protected document encountered during automatic source collection follows the automatic alternative-source and unavailable-evidence path instead.
- Two supplier records share a GST identifier but other attributes conflict: flag the anomaly for review; do not silently merge them.
- A same-name company has a different legal identifier or production site: do not transfer its evidence to the selected supplier.
- Source dates are missing, expired or outside the claim period: display the currency problem and apply the evidence policy.
- A claim has no retrieved evidence at all: cite its actual check attempts, never an invented quotation or fourth verdict.
- A signed-out user or another buyer uses a case, document or report reference: deny access without disclosing private case content. A background case retains its original owner across sign-out and service restarts.
- A check finishes after a requirements revision is created: retain its result against the revision it evaluated; do not overwrite assessments for another revision. Reused evidence must still satisfy the current revision's proof and freshness criteria.
- No supplier meets every buyer-required claim: show an empty qualified shortlist with an explicit explanation; do not relax proof criteria to fill it. Follow-up candidates remain separate and are not qualified recommendations.
- A case is explicitly deleted while linked work is pending: stop that work from recreating the case or exposing its records. Deleting one case must not delete another case's retained evidence or assessment history.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a natural-language conversation for intake, verification, human actions and report review.
- **FR-002**: System MUST display supplier information, claim checklists, expandable evidence tables and shortlist decisions as interactive components inside the conversation. Extension features MUST use the same conversation for their candidate and approval components.
- **FR-003**: System MUST accept typed part descriptions, material grades, processes, quantities/periods and certification requirements as the shared intake contract; missing required facts MUST prompt clarification.
- **FR-004**: System MUST present interpreted requirements for correction and explicit confirmation before generating claims. Text, PDF and voice intake MUST share this confirmation rule, and only confirmed values may enter verification.
- **FR-005**: System MUST accept supplier names, website URLs, GST identifiers and user-pasted IndiaMART listing links with the part specification. A pasted listing is an identifier and MUST NOT trigger automated access to that site.
- **FR-006**: System MUST retain confirmed country, region/state, city or radius preferences with the case.
- **FR-007**: System MUST propose per-supplier claims for legal existence/status, manufacturer classification, material/process/part capability, certificate validity/accreditation/scope/site, applicable compliance and capacity plausibility, separating required subclaims and stating proof criteria, entity/site and relevant period.
- **FR-008**: System MUST let the buyer add, remove or modify proposed claims, identify which claims are required for shortlist eligibility, and confirm the checklist and proof criteria before evidence collection starts.
- **FR-009**: System MUST automatically collect supplier website product ranges, process descriptions, facility-photo references and addresses without buyer intervention after intake and checklist confirmation, preserving the source, extracted observation, check time and whether a statement is self-reported.
- **FR-010**: System MUST read supplier certificate PDFs and extract certificate number, certification body, standard, scope, production-site address and expiry date; missing or unreadable fields MUST remain explicit.
- **FR-011**: System MUST attempt certificate validation against IAF CertSearch when available and apply the Evidence and Verdict Policy if it is unavailable or insufficient.
- **FR-012**: System MUST attempt to obtain legal name, active status, registered business activity and address automatically from applicable GST, Udyam or MCA sources through permitted access. Unavailable checks MUST follow FR-014 without requiring a user-provided official lookup. Voluntarily supplied official evidence MAY be evaluated under the shared evidence policy but MUST NOT be a prerequisite for completing the automatic run.
- **FR-013**: System MUST assess the confirmed product against the current official BIS QCO requirements and record applicability and the basis for any required licence or finding that no licence is required.
- **FR-014**: System MUST perform scraping and external-source collection automatically without buyer intervention. When a source is inaccessible, blocked by a CAPTCHA or otherwise unusable, it MUST record the attempt and try permitted alternative sources automatically. If evidence remains unavailable, it MUST record the gap and leave unsatisfied claims unproven without requiring manual browsing, CAPTCHA solving or pasted lookup results. It MUST NOT bypass access controls. Requests for an unlocked or replacement buyer-uploaded document MAY remain pending human actions; only affected work and its dependencies pause, independent checks continue, and affected work resumes when the requested document is supplied.
- **FR-015**: System MUST propose cross-source identity matches using name variations and corroborating identifiers, expose ambiguous matches and conflicting identifiers for human review, and avoid treating fuzzy similarity as proof.
- **FR-016**: System MUST compare Indian address variations while preserving original addresses and distinguishing registered-office and production-site roles.
- **FR-017**: System MUST assign every evaluated claim exactly one verdict of proven, unproven or contradicted. Pending/checking states and access failure reasons MUST remain separate from verdicts.
- **FR-018**: System MUST link each verdict to reasoning and its evidence citations, including source URL/document, observation or quote and check time. An unproven claim with no retrieved evidence MUST instead link to inspectable check attempts; a failure MUST NOT be represented as retrieved evidence.
- **FR-019**: System MUST show conflicting records and whether they concern the same entity, site, assertion and period; unresolved discrepancies MUST remain visible without automatically becoming contradicted verdicts.
- **FR-020**: For undeleted cases, system MUST durably retain case ownership, requirement revisions and their confirmation status, suppliers, claims, evidence, check attempts, verdict history and pending human actions across browser closure, full service restarts and multi-day waits, including waits introduced by outreach. Owner-initiated deletion follows FR-031.
- **FR-021**: System MUST present an expandable supplier-by-claim verdict table in the conversation, with reasons, retrieved evidence and failed/missing-evidence attempts visible from each cell.
- **FR-022**: System MUST include a supplier on the qualified shortlist only when every buyer-required claim is proven for the assessed requirement revision, with reasoning tied to the displayed verdicts. If none qualify, the system MUST explicitly show that no supplier qualifies. Suppliers with unproven required claims and no contradicted required claims MUST be shown separately as follow-up candidates with their evidence gaps; they MUST NOT be labeled qualified. Suppliers with contradicted required claims MUST remain visible in the assessment with their reasons and MUST NOT appear on the qualified shortlist or follow-up candidate list. The buyer MUST retain the final selection decision.
- **FR-023**: System MUST provide a downloadable PDF evidence report identifying the confirmed requirement revision assessed and preserving that revision's table verdicts, reasons, citations, check times, qualified shortlist and any separate follow-up candidates, including an explicit statement when no supplier qualifies.
- **FR-024**: System MUST separate shared case, evidence and verdict behavior from country-specific registry, compliance, address and red-flag rules. Adding a country pack MUST NOT require changing that shared behavior.
- **FR-025**: System MUST provide the India country pack covering GST/Udyam registration checks, BIS applicability, Indian address comparison and evidence-based manufacturer/trader assessment, with MCA used where applicable.
- **FR-026**: System MUST apply the Evidence and Verdict Policy below to initial verification and every re-evaluation, including human-provided and supplier-response evidence; historical verdicts and their reasons MUST remain inspectable.
- **FR-027**: System MUST record each evidence-check attempt with its claim, targeted source/document, time, outcome and failure/missing-evidence reason where applicable. No-content attempts MUST remain distinct from evidence and contain no invented excerpts.
- **FR-028**: System MUST require buyer sign-in for private case access and assign each case to its creating buyer. Only that signed-in owner may list, open, modify, resume or export the case or access its linked conversation, uploaded documents, evidence and reports. Unauthenticated users and other buyers MUST be denied access even when they possess a direct reference. Organization sharing and team roles are outside the first release.
- **FR-029**: System MUST allow the buyer to change confirmed requirements after verification starts by creating a new revision within the same case. Changed values MUST be explicitly reconfirmed before claim generation or verification uses them; affected claim checklists and proof criteria MUST pass the confirmation gate in FR-008 before collection. Affected claims MUST be re-evaluated for the confirmed revision, with earlier inputs, evidence and assessments retained as inspectable history. Claims, check attempts, assessments and reports MUST identify the revision they evaluate; affected earlier verdicts MUST NOT be represented as current results for changed requirements. Evidence reuse MUST satisfy the applicable proof and freshness criteria.
- **FR-030**: System MUST isolate a blocked check and its dependent work from independent checks, including checks for other suppliers. Available assessments MUST remain viewable and exportable with pending actions and evidence gaps distinguished from completed checks. An unresolved source-collection failure MUST NOT hold the case open awaiting buyer intervention; the buyer MAY close the case with unresolved claims.
- **FR-031**: System MUST retain completed cases, reports, uploaded documents and linked assessment history without automatic time-based expiry until the owning buyer explicitly deletes the case. Only the owning signed-in buyer may delete a case. Completed deletion MUST remove the case and its linked private records from product access, including direct references and exports, and MUST prevent pending work or a service restart from recreating them. Deletion MUST NOT remove records belonging to other cases. Planning MUST define removal from storage, backup retention and purge behavior; backup recovery MUST preserve completed deletions.
- **FR-032**: The initial product MUST run on the developer's local machine without required paid data/model APIs, cloud storage or hosting. It MUST use real-world source records throughout application operation and acceptance data, with no demo suppliers, synthetic datasets or fabricated source/evidence responses. Eligible free sources, permitted scraping, actual official exports and free-tier or local inference MUST support the initial workflow. Missing free coverage MUST remain an explicit limitation rather than trigger a required purchase or invented data. Controlled test conditions and replay of genuine captured records MUST be labeled and MUST NOT be represented as live verification.
- **FR-033**: System MUST support local ingestion of legitimately obtained official CSV/XLSX/PDF/HTML source files for known-supplier checks, retaining publisher, original source URL, licence/attribution, collection time, publication/cutoff, coverage, original file hash and row/page provenance. Dated imports MUST NOT be represented as current-status checks. Malformed or provenance-incomplete source files MUST remain quarantined/unavailable without invented replacement records. This source corpus MUST NOT imply implementation of the separate discovery index.

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

- **Buyer Account**: A signed-in buyer identity that owns private cases; the first release has no organization-sharing or team-role model.
- **Case**: Owning buyer account, requirement revisions, suppliers, locations, claims, evidence history, pending actions, reports and deletion status. Linked private records retain the same ownership and retention boundary; closure does not trigger expiry.
- **Requirement Revision**: An identified version of a case's part requirements with draft or confirmed status and its confirmation record. Earlier revisions and their evidence and assessments remain inspectable.
- **Supplier**: Company identity, identifiers, address roles and source attribution; a name match is not a confirmed identity.
- **Claim**: Assertion with proof criteria, buyer-confirmed required-for-shortlist flag, entity/site, relevant period, requirement revision, subclaims, processing state and assessment history.
- **Evidence Record**: An attributable observation, source/document reference, snapshot, check time and available issue/expiry/effective dates.
- **Check Attempt**: A source/document check with its outcome and any failure reason, whether or not content was retrieved.
- **Verdict**: Proven, unproven or contradicted assessment with reasoning and evidence/attempt references.
- **Country Pack**: Country-specific sources, applicability, address rules and red-flag patterns used under shared evidence rules.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a confirmed part requirement and five named suppliers, an initial report is available within 30 minutes, excluding waits for human input or supplier replies. Every claim has a verdict and evidence/attempt references, with failures labeled accurately. External-source access failures MUST NOT suspend this timing target or require buyer intervention.
- **SC-002**: Verdicts agree with a human auditor on at least 80% of claims across 30 suppliers. The labeled evaluation includes all three verdicts and each standard claim type; report agreement by verdict as well as overall.
- **SC-003**: Use the same 30 real suppliers across six five-supplier cases as SC-002. Record active intervals for intake, corrections, confirmations, evidence review and decision/report actions; divide shared case time equally across evaluated suppliers and never double-count overlapping intervals. Report all 30 per-supplier totals and the maximum; every total must be under one hour. Separately record unattended collection and excluded actual waits. Missing any supplier timing leaves SC-003 unmeasured; a five-supplier timing run or average alone cannot pass it. The estimated manual baseline remains unverified.
- **SC-004**: In five text-intake trials using a prepared part requirement and supplier list, each buyer can reach confirmed intake in under five minutes without assistance.
- **SC-005**: In every evaluated and exported verdict cell, reasoning and evidence or check-attempt references are inspectable; 100% of proven and contradicted verdicts have retrieved supporting evidence and no failed check has an invented excerpt.
- **SC-006**: A full service restart during collection, a pending human action and a multi-day wait loses none of the recorded confirmed inputs, evidence, attempts, verdict history or pending actions.
- **SC-007**: The system identifies at least three of four curated manufacturer/trader warning patterns: conflicting business activity, unresolved site inconsistency, unsupported catalogue breadth and unsupported capacity/headcount assertions. It flags them for evidence review without treating those indicators alone as conclusive proof.
- **SC-008**: The country extension boundary can accept the second-country feature's rules and evidence without changing shared case, evidence or verdict behavior; the second-country feature owns the demonstration.
- **SC-009**: In acceptance tests with two distinct buyer accounts and a signed-out user, every unauthorized attempt to list, open, modify, resume or export another buyer's case or retrieve its documents/evidence is denied, with zero private case content disclosed; the owning signed-in buyer can complete each permitted action.
- **SC-010**: In separate acceptance scenarios changing material, quantity and required certification after verification starts, changed values are used only after reconfirmation, affected claims are re-evaluated, earlier evidence and assessments remain inspectable, and every displayed or exported result identifies its requirement revision. A check completing for an earlier revision never overwrites the newer revision's assessments.
- **SC-011**: Across curated cases containing suppliers with all required claims proven, an unproven required claim and a contradicted required claim, every qualified shortlist entry has all buyer-required claims proven, follow-up candidates are separate and have no contradicted required claims, and an all-ineligible case explicitly shows no qualifying supplier. The conversation and PDF report agree on eligibility and evidence gaps.
- **SC-012**: After confirmed intake and checklist approval, acceptance scenarios covering successful collection, a CAPTCHA-blocked source and unavailable alternatives complete automatic source collection with zero buyer scraping or manual-lookup actions. Independent checks complete while an affected check is blocked; the initial report exposes actual attempts and evidence gaps without fabricated evidence. A separate buyer-uploaded locked-document scenario preserves and resumes only the affected work and its dependencies while other checks proceed. Controlled test restrictions and faithful replay of actual captured source records MUST be labeled, with no fabricated provider/evidence responses; live source access MUST be validated separately during integration.
- **SC-013**: With simulated elapsed time explicitly labeled, completed undeleted cases and their reports, uploaded documents and history remain accessible after 90 days and one year. After owner-initiated deletion completes, all case-content access attempts through lists, direct references, documents and exports are denied; pending work and a service restart do not recreate the case, another buyer cannot delete it, and another case's retained records remain intact. Storage and backup purge checks MUST follow the documented planning policy.
- **SC-014**: A local end-to-end run uses genuine public or authorized supplier/official records, local file storage and local or eligible free-tier inference with no paid API/model or cloud-storage credential required. At least one actual supplier page and official document retrieval/import are recorded with source/date/hash provenance; source limitations and genuine-record replays remain explicit, with zero seeded demo/synthetic suppliers or fabricated evidence. Unavailable current-status sources remain unproven rather than blocking the run on payment.

## Assumptions

- Users are signed-in buyers with private case ownership, using a modern browser with stable connectivity; offline operation is outside this baseline. Sign-in and account-management methods will be selected during planning.
- Authoritative source access, supported queries, permissions, quotas and costs must be verified during planning; unavailable checks remain explicit. Only genuine records may be replayed; controlled fault/time conditions must be visibly labeled.
- Scraping and external-source collection are automatic after confirmation; first-release operation does not depend on buyer-performed portal lookups. Planning must identify which required sources support unattended permitted access and document automatic alternatives or explicit coverage gaps. Buyer review of inputs, identity ambiguities, uploaded-document corrections and final supplier selection remains part of the workflow.
- The Evidence and Verdict Policy in this feature is the maintained shared policy for all seven delivery features. The product baseline is retained for provenance.
- Text intake and certificate-document reading are sufficient for this feature's acceptance. Buyer BOM/drawing interpretation, discovery, email sending, voice and recurring monitoring are separate capabilities.
- Sample production, inspection or buyer-acceptance records may be provided by users. Missing independent corroboration is a valid unproven result.
- Retention of prior inputs, evidence and verdict history applies while the case remains undeleted. Closing a case does not delete it or start an expiry period. Storage removal and backup purge details are planning decisions under FR-031.
- The initial product is local-first with a zero-required-spend path for data, inference and storage. Free-tier Gemini or locally useful models are preferred; AWS S3, LocalStack and hosted deployment are deferred. Real-world data only is mandatory. Public business excerpts may be used with eligible free inference; confidential/personal inputs must follow provider restrictions and can remain local.
- The four warning patterns in SC-007 are review indicators; direct EPFO collection and reverse-image checks were discussed in the transcript but were not mandated by the remediated baseline's functional requirements.
- This is a draft specification, not a claim of implementation. Constitution v1.0.0 was adopted on 2026-10-16; planning must assess this feature against its principles. The revised plan and 102-task coverage are subject to the current consistency review; implementation and acceptance remain unverified.
