# Feature Specification: VeriSource — AI Supplier Verification Agent

**Feature Branch**: `001-supplier-verification-agent`

**Created**: 2026-10-15

**Status**: Product baseline — delivery requirements are maintained in the seven [feature specs](../README.md).

**Last revised**: 2026-10-16 — evidence rules, feature boundaries, monitoring coverage, and acceptance conditions clarified.

**Input**: User description: "An AI agent that helps manufacturers discover suppliers, verify whether they can actually make a specific part (not just whether the company exists), and monitor approved suppliers over time. The system uses a conversational interface with voice input, parses part specs from PDFs/drawings, searches multiple discovery sources (web, EPC directories, trade data, IAF CertSearch), generates evidence-based claim checklists per supplier, collects and cross-checks evidence from official registries and supplier documents, handles multi-day outreach loops with human approval, and produces a shortlist where every verdict links to its source."

---

## Scope and Delivery Dependencies

This document preserves the full agreed product scope and original requirement identifiers for provenance. The seven delivery specs have now been created under `002` through `008`; see the [feature and traceability map](../README.md) for their requirements, acceptance criteria, dependencies and checklists. This baseline is not an eighth implementation feature. No implementation is claimed.

The requirement and evidence-policy text below records the remediated pre-split baseline. The [verification core's Evidence and Verdict Policy](../002-supplier-verification-core/spec.md#evidence-and-verdict-policy) is the maintained shared policy for delivery. Future requirements changes belong in the owning feature spec and traceability map.

| Capability | Requirement ownership | Dependencies and acceptance boundary |
|---|---|---|
| Supplier verification core | FR-001–002; text intake in FR-005; FR-008–010; FR-018–030; FR-033; FR-036–038; FR-045–046; FR-048–049 | Accept confirmed text requirements and a known supplier list, collect evidence, assign verdicts, and produce the report. Durable case state and country-pack interfaces belong here. Email integration is not required to complete this acceptance test. |
| Discovery and supplier index | FR-011–017; FR-042–044 | Ingest, update, search, and review candidates, then hand the selected suppliers to the core. Discovery source labels do not establish verification verdicts. |
| PDF and drawing intake | PDF input in FR-005; FR-006–007 | Produce structured requirements for the core's FR-008 confirmation step. Certificate PDF reading under FR-021 remains part of verification. |
| Outreach and follow-up | FR-031–032; FR-034–035 | Extend the core's persisted cases with approved sending, reply handling, and follow-up. New evidence is evaluated under the same verdict rules. |
| Voice intake | FR-003–004; voice input in FR-005 | Produce editable text for the core's FR-008 confirmation step; use the SC-009 acceptance workload. |
| Approved supplier monitoring | FR-039–041; FR-050 | Reuse verified supplier identities and evidence history for recurring certificate and QCO checks. |
| Second-country verification | FR-047 | Exercise the core's FR-045 extension boundary and demonstrate SC-010. |

FR-005 defines the shared intake contract; PDF and voice capabilities supply additional input methods. FR-008 owns the common confirmation step for all methods, rather than each capability defining a different confirmation rule. Each capability requires its own acceptance evidence before it may be described as implemented.

**Planning prerequisite**: `.specify/memory/constitution.md` currently contains template placeholders. Project principles must be adopted through a separate constitution update before constitution alignment can be assessed. This specification does not establish or amend project governance. No implementation plan or task coverage has yet been validated.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Verify Suppliers from a Known List (Priority: P1)

A purchase manager at a pump factory needs to qualify 4 supplier candidates she already has — 2 from IndiaMART, 1 referral, 1 old vendor. She opens VeriSource, describes her part requirement ("CF8M stainless steel impeller castings, 2,000 pieces/month, ISO 9001 required"), and pastes in the 4 supplier names/websites/GST numbers. The agent generates a claim checklist per supplier, collects evidence from the web and official registries, cross-checks names/addresses/certificate scopes, and presents an evidence table showing each claim as proven, unproven, or contradicted with source citations. She reviews the table and approves 2 suppliers for her shortlist.

**Why this priority**: This is the core value proposition — the verification engine. Without this working, nothing else matters. Every other feature (discovery, monitoring, voice, PDF parsing) feeds into or builds upon this loop.

**Independent Test**: Can be tested by manually entering a part spec + supplier list and verifying that the system generates claims, collects evidence, cross-checks, and produces a verdict table with source links.

**Acceptance Scenarios**:

1. **Given** a user has entered a part description and a list of 4 supplier identifiers (names, websites, or GST numbers), **When** the agent processes them, **Then** it generates a claim checklist per supplier covering: legal existence, manufacturer vs trader, capability for the specified part, certificate validity/scope/site match, and applicable compliance requirements.
2. **Given** the agent has generated claims, **When** it completes the initial evidence run, **Then** each claim receives a verdict under the Evidence and Verdict Policy, with reasoning and evidence citations or check-attempt references as specified in FR-029.
3. **Given** evidence has been collected, **When** two sources disagree, **Then** the agent shows both sources and distinguishes an unresolved discrepancy from evidence that contradicts a specific claim under the Evidence and Verdict Policy. Different registered-office and factory addresses alone do not establish a contradiction.
4. **Given** the initial evidence run is complete, **When** the agent produces the report table, **Then** the user can expand any verdict cell to see its reasoning, underlying evidence with source links and extracted quotes where available, and check-attempt records explaining any missing evidence.
5. **Given** a claim remains unproven after the initial evidence run, **When** the report is produced, **Then** it shows the missing evidence and check failures, and the user can close the case with that verdict without sending email. Outreach is tested separately in User Story 4.
6. **Given** only a supplier's own website asserts the required manufacturing capability, **When** no qualifying independent evidence is available, **Then** the capability claim remains `unproven` and the supplier's assertion is cited as self-reported evidence.
7. **Given** a required registry check fails or reaches its access limit, **When** no other evidence satisfies the claim's proof criteria, **Then** the verdict is `unproven`, the failed attempt is inspectable, and the system does not invent a source quote or introduce another verdict value.
8. **Given** matching identifies a registered office and a different factory site belonging to the same supplier, **When** a certificate covers the factory, **Then** the system evaluates that factory against the required production site without treating the office address difference alone as contradictory evidence.
9. **Given** an authoritative registry record identifies the same certificate and production site as suspended, **When** the supplier's PDF still describes it as valid, **Then** the current-validity claim is `contradicted` and both records and the registry check time are shown.

---

### User Story 2 — Discover Suppliers When No List Exists (Priority: P2)

A small auto-parts manufacturer needs a new supplier for heat-treated steel forgings but has no leads. He opens VeriSource, describes the part and location preference ("closed-die steel forgings, EN8 material, 500 pcs/month, western India preferred"). The agent searches across its indexed sources (EPC directories, web search, IAF CertSearch by scope) and presents 12 candidate suppliers with source labels. The user reviews, removes 3 irrelevant results, and triggers verification on the remaining 9.

**Why this priority**: Discovery expands the addressable market from "users who already have supplier lists" to "users who need to find suppliers from scratch." It's the second most important flow because without it, the tool only serves half the use case.

**Independent Test**: Can be tested by entering a part spec without any supplier list and verifying the system returns relevant candidates from multiple sources with source attribution.

**Acceptance Scenarios**:

1. **Given** a user has entered a part description with location preference and no supplier list, **When** the agent runs discovery, **Then** it returns 8–20 candidate suppliers sourced from at least 2 different data sources.
2. **Given** discovery results are shown, **When** the user views a candidate card, **Then** each card displays: company name, location, source label (e.g., "EEPC directory", "web search", "IAF CertSearch"), and website if available.
3. **Given** the user reviews discovery results, **When** they remove or add candidates, **Then** the modified list is used as input to the verification pipeline (User Story 1).
4. **Given** the supplier index has been previously populated with EPC directory data, **When** the user searches for a matching sector/location, **Then** index results appear alongside live web search results, clearly labeled by source.

---

### User Story 3 — Parse Part Requirements from a PDF Document (Priority: P3)

An export manager uploads a customer's purchase order PDF containing a BOM with 3 line items — each specifying a material grade, quantity, and required certifications. The agent extracts structured requirements from the PDF and presents them to the user: "I found 3 items in your document. Here's what I understood — please correct anything before I proceed." The user edits one material grade the agent got wrong, confirms, and the agent creates a verification case for each line item.

**Why this priority**: PDF intake reduces friction for users who already have their specs in document form (which is the majority — purchase orders, BOMs, drawings). It directly feeds into P1 and P2 stories.

**Independent Test**: Can be tested by uploading a sample BOM PDF and verifying the system extracts structured fields (material, quantity, certifications) and presents them for user confirmation.

**Acceptance Scenarios**:

1. **Given** a user uploads a text-based BOM PDF, **When** the agent processes it, **Then** it extracts part descriptions, material grades, quantities, and certification requirements as structured data.
2. **Given** a user uploads a scanned engineering drawing (image-based PDF), **When** the agent detects text extraction failure, **Then** it falls back to rendering the page as a high-res image and using a vision model to extract key fields (part number, material, tolerances, notes).
3. **Given** the agent has extracted requirements from a PDF, **When** it presents them to the user, **Then** any field the agent is uncertain about is visually highlighted and editable by the user.
4. **Given** the user has confirmed (and optionally corrected) extracted requirements, **When** they proceed, **Then** the confirmed data is used to generate claims — not the raw extraction.

---

### User Story 4 — Multi-Day Outreach and Follow-Up (Priority: P4)

After the initial evidence run, 2 of 5 suppliers have unproven claims (missing ISO certificate, unconfirmed capacity). The agent drafts polite email requests for each, shows them to the user for approval. The user approves both. The emails are sent. Three days later, one supplier replies with a certificate PDF. The agent picks up the case, reads the PDF, validates the cert against the IAF registry, and updates the claim table. The other supplier hasn't replied — the agent drafts a follow-up and asks the user to approve it.

**Why this priority**: This is what makes the system agentic — it holds state over days, recovers from gaps, and drives the process forward. But it requires P1 to be fully working first.

**Independent Test**: Can be tested by triggering outreach for a supplier with unproven claims, simulating an email reply with an attached document, and verifying the agent resumes, processes the document, and updates verdicts.

**Acceptance Scenarios**:

1. **Given** a supplier has unproven claims after evidence collection, **When** the agent determines outreach is needed, **Then** it drafts a specific, professional message requesting the exact missing document and presents it to the user for approval.
2. **Given** the user approves an outreach message, **When** it is sent, **Then** the case enters a waiting state and the system persists all case data durably (no data loss on server restart).
3. **Given** a supplier replies with a document, **When** the agent detects the reply, **Then** it automatically resumes the case, processes the document, and updates the claim table.
4. **Given** a supplier has not replied within a configurable period, **When** the follow-up threshold is reached, **Then** the agent drafts a follow-up message and presents it to the user for approval.
5. **Given** a user declines to send an outreach or follow-up, **When** they skip it, **Then** the claim remains "unproven" and the case can still be closed with that status.
6. **Given** a supplier reply contains a new claim or attachment, **When** the case resumes, **Then** the system retains prior evidence and verdicts and applies the Evidence and Verdict Policy to the new evidence; receipt of a reply alone does not prove the claim.

---

### User Story 5 — Voice-Based Conversational Intake (Priority: P5)

A purchase manager prefers speaking over typing. She clicks the microphone button, says "I need someone who can make stainless steel CF8M castings, two thousand pieces a month, ISO nine thousand one certified, somewhere in Gujarat." The system transcribes her speech, shows the transcript with uncertain terms highlighted (e.g., "CF8M" may show as "CF-8M" or "CF eight M"), and lets her edit inline before the agent processes it.

**Why this priority**: Voice adds UX polish and accessibility. The core product works without it, but it removes friction for users who find typing part specs cumbersome.

**Independent Test**: Can be tested by recording audio of a part specification, sending it through the transcription endpoint, and verifying the transcript is displayed with editable uncertain terms.

**Acceptance Scenarios**:

1. **Given** the user records a part specification under the SC-009 workload and deployment conditions, **When** they stop recording, **Then** the transcript display latency meets SC-009 and the user can edit and confirm the text before case creation.
2. **Given** the transcription contains technical terms (material grades, certification codes), **When** the transcript is displayed, **Then** terms the model is uncertain about are visually highlighted as editable spans.
3. **Given** the user edits a highlighted term in the transcript, **When** they confirm, **Then** the corrected text is used as the input for case creation.
4. **Given** the browser does not support audio recording or microphone access is denied, **When** the user tries to use voice, **Then** the system shows a clear message and the text input remains available.
5. **Given** transcription is still processing after 5 seconds or fails, **When** the user views the conversation, **Then** the system shows the actual processing or failure state, preserves the entered text, and permits retry or text entry without submitting an unconfirmed transcript.

---

### User Story 6 — Monitor Approved Suppliers (Priority: P6)

After completing verification, the purchase manager marks Shreeji Precicast as "approved." Three months later, IAF CertSearch shows their ISO 9001 certificate has been suspended. The system alerts the user in-app, showing what changed and when. The user can then re-open the case or initiate outreach to the supplier.

**Why this priority**: Monitoring is long-term value — it catches problems before they hit production. But it only makes sense once the verification pipeline is proven and suppliers are being approved.

**Independent Test**: Can be tested by approving a supplier, simulating a certificate status change in the monitoring data source, and verifying the alert is triggered and displayed correctly.

**Acceptance Scenarios**:

1. **Given** a supplier is marked as approved, **When** a monitoring cycle runs, **Then** it checks IAF CertSearch for the supplier's certificate status.
2. **Given** a certificate status changes to suspended, withdrawn, or expired, **When** the system detects it, **Then** it creates an alert visible to the user with the previous and current status, detection time, source link, and source-reported change date when available.
3. **Given** a BIS Quality Control Order is newly issued, amended, or withdrawn for a product linked to a watched supplier's case, **When** the monitoring cycle detects it, **Then** it alerts the user with the previous and current requirement, affected product, source, detection time, and effective date when stated; uncertain applicability is marked for review.
4. **Given** a monitoring source cannot be accessed, **When** a scheduled check fails, **Then** the system preserves the last confirmed status and shows the failed check and last successful check time; it does not treat a source outage as a certificate or regulatory change.

---

### Edge Cases

- What happens when a supplier's website is down or returns a 403/captcha during crawling? → Agent marks the crawl as failed and falls back to other sources.
- What happens when two suppliers share the same GST number? → Flag as a data anomaly — may indicate a common parent company or a data error.
- What happens when a certificate PDF is password-protected? → Agent asks the user to provide the unlocked version via the `ask_human` tool.
- What happens when registry access is unavailable or its configured quota is exhausted? → Agent records the failed attempt and reason, notifies the user, and continues with other sources. Any claim whose proof criteria remain unsatisfied is `unproven` with a reason such as `registry limit reached`; access failure alone never means `contradicted`.
- What happens when a user starts a case and closes the browser mid-process? → Case state is persisted; user can resume from where they left off.
- What happens when the part description is vague (e.g., "steel parts")? → Agent asks clarifying questions before generating claims.
- What happens when the same supplier appears in both the user's list and discovery results? → De-duplicate by matching name + address/GST, keeping the richer record.
- What happens when a registry record lists manufacturing activity but other evidence suggests trading? → Agent shows both records, checks that they concern the same entity, site, activity, and period, and applies the Evidence and Verdict Policy. Inconclusive signals leave the manufacturing claim `unproven`; the buyer makes the final supplier-selection decision.

---

## Requirements *(mandatory)*

### Functional Requirements

**Conversational Interface**

- **FR-001**: System MUST provide a conversational chat interface where the user interacts with the agent through natural language messages.
- **FR-002**: System MUST display structured data (supplier cards, evidence tables, verdict matrices, outreach drafts) as interactive components embedded within the conversation flow — not as separate pages.
- **FR-003**: System MUST support voice input via a microphone button that records, transcribes via a self-hosted speech-to-text model, and displays the transcript as editable text with uncertain terms visually highlighted.
- **FR-004**: System MUST allow users to edit any highlighted uncertain term inline before the agent processes the input.

**Case Intake**

- **FR-005**: System MUST accept part/product requirements via text input, voice input, or document upload (PDF).
- **FR-006**: System MUST parse text-based PDF documents (BOMs, spec sheets, purchase orders) to extract structured requirements: part descriptions, material grades, quantities, and certification requirements.
- **FR-007**: System MUST detect when a PDF contains image-based content (scanned documents, engineering drawings) and fall back to rendering the page as a high-resolution image for vision-model-based extraction.
- **FR-008**: System MUST present structured requirements from text, voice, or PDF input to the user for confirmation and inline editing before generating claims; only confirmed values may enter verification.
- **FR-009**: System MUST accept an optional list of supplier identifiers (company names, website URLs, GST numbers, or IndiaMART listing links) as input alongside the part specification.
- **FR-010**: System MUST accept location preferences (country, state/region, city or radius) as part of the case input.

**Supplier Discovery**

- **FR-011**: System MUST discover supplier candidates through web search when no supplier list is provided.
- **FR-012**: System MUST discover supplier candidates through IAF CertSearch by searching for companies with relevant certification scope and location.
- **FR-013**: System MUST maintain a Supplier Index populated from Export Promotion Council (EPC) member directories, government MSME portals, and trade data sources.
- **FR-014**: System MUST query the Supplier Index as the first discovery source (fast, no external API call) and supplement with live web search results.
- **FR-015**: System MUST label each discovery result with its source (e.g., "EEPC directory", "web search", "IAF CertSearch", "Volza trade data").
- **FR-016**: System MUST allow the user to add, remove, or re-order suppliers in the discovery results before triggering verification.
- **FR-017**: System MUST de-duplicate suppliers that appear in both the user-provided list and discovery results, merging records and keeping the richer data.

**Claim Generation**

- **FR-018**: System MUST generate a structured claim checklist per supplier based on the part specification and requirements. Standard claims include: (a) legal existence and active status, (b) manufacturer vs. trader classification, (c) capability to produce the specific part (material, process), (d) certification validity, accreditation status, scope coverage, and site match, (e) applicable regulatory compliance (e.g., BIS licence), (f) stated capacity plausibility.
- **FR-019**: System MUST allow the claim checklist to be customized per case — users can add, remove, or modify claims before evidence collection begins.

**Evidence Collection**

- **FR-020**: System MUST crawl supplier websites to extract product range, process descriptions, facility photos, and address information.
- **FR-021**: System MUST read and extract structured data from certificate PDF documents (certificate number, certification body, standard, scope text, site address, expiry date).
- **FR-022**: System MUST validate certificates against the IAF CertSearch registry when available.
- **FR-023**: System MUST look up company information (legal name, status, registered business type, address) from GST/Udyam/MCA sources — either via licensed API or by prompting the user to perform a manual lookup and provide the result.
- **FR-024**: System MUST check the current BIS Quality Control Order list to determine whether the specified product requires a BIS licence.
- **FR-025**: System MUST support an `ask_human` tool that prompts the user to perform a manual action (solve a CAPTCHA, provide a document, look up a portal) and return the result to the agent.

**Cross-Matching & Verdicts**

- **FR-026**: System MUST perform fuzzy name matching across multiple data sources to identify whether records from different sources refer to the same entity.
- **FR-027**: System MUST normalize Indian addresses to enable matching across sources that use different formats, abbreviations, and conventions.
- **FR-028**: System MUST assign each evaluated claim exactly one verdict of `proven`, `unproven`, or `contradicted`, following FR-048. Processing states such as pending or checking and failure reasons such as registry quota exhaustion MUST be recorded separately from verdicts.
- **FR-029**: System MUST link every verdict to the evidence and reasoning used to assign it. Each evidence citation MUST include its source URL or document reference, extracted text or data point, and check timestamp. An `unproven` verdict with no retrieved evidence MUST instead link to an inspectable check-attempt record under FR-049; failed access MUST NOT be presented as retrieved evidence.
- **FR-030**: System MUST display conflicting source records and explain whether they concern the same entity, site, claim, and period. A mismatch in names or addresses alone MUST NOT automatically produce a `contradicted` verdict. Unresolved discrepancies MUST remain visible even when they do not establish a contradiction.

**Outreach & Follow-Up**

- **FR-031**: System MUST draft outreach messages (email) to suppliers requesting specific missing documents or information for unproven claims.
- **FR-032**: System MUST present every outreach message to the user for approval, editing, or rejection before sending.
- **FR-033**: System MUST persist all case state durably, including confirmed requirements, suppliers, claims, evidence, check attempts, verdict history, and pending human actions, so that an in-progress case or a case waiting for supplier replies survives server restarts and can be resumed days later. This is a core capability shared with outreach.
- **FR-034**: System MUST detect incoming supplier replies and automatically resume the case — processing any attached documents and updating verdicts.
- **FR-035**: System MUST send follow-up messages to non-responsive suppliers after a configurable waiting period, with user approval.

**Reporting & Output**

- **FR-036**: System MUST present a final evidence table as an interactive component in the chat — with one row per supplier, one column per claim, and expandable verdict cells showing underlying evidence.
- **FR-037**: System MUST generate a recommended shortlist with reasoning, based on the evidence collected.
- **FR-038**: System MUST support exporting the evidence report as a downloadable PDF document.

**Monitoring**

- **FR-039**: System MUST allow users to mark verified suppliers as "approved" and add them to a monitoring watchlist.
- **FR-040**: System MUST check IAF CertSearch for certificate status changes (suspended, withdrawn, expired) for watched suppliers on a configurable schedule, initially once every 24 hours. Each cycle MUST record its outcome and last successful check time. Access failures MUST preserve the last confirmed status and be displayed separately from status changes.
- **FR-041**: System MUST alert the user in-app when a monitored supplier's certificate status changes, showing the old status, new status, detection time, source, and source-reported change date when available; it MUST NOT substitute detection time for an unknown change date.

**Supplier Index Infrastructure**

- **FR-042**: System MUST parse publicly available EPC member directory PDFs and populate a searchable supplier index.
- **FR-043**: System MUST scrape publicly accessible EPC web portals (respecting robots.txt and rate limits) to supplement the index.
- **FR-044**: System MUST support incremental index updates — new data sources or refreshed directories can be added without rebuilding the entire index.

**Multi-Country Support**

- **FR-045**: System MUST be architected with a shared verification core and pluggable "country packs" that encapsulate country-specific registries, compliance rules, and red flags.
- **FR-046**: System MUST ship with a complete India country pack (GST, Udyam, BIS, Indian address normalization, trader-detection patterns).
- **FR-047**: System MUST include a thin second country pack (e.g., US — using public company registries + IAF CertSearch) to demonstrate the architecture scales.

**Evidence Rules and Monitoring Completeness**

- **FR-048**: System MUST apply the Evidence and Verdict Policy below to initial verification, human-provided evidence, supplier replies, and re-evaluation. Each claim MUST identify its proof criteria, applicable entity/site, and relevant period before collection begins.
- **FR-049**: System MUST record each completed or failed evidence-check attempt with an identifier, claim reference, source or document targeted, check time, outcome, and failure or missing-evidence reason when applicable. Attempts with no retrieved content MUST remain distinguishable from evidence records and MUST NOT contain invented excerpts.
- **FR-050**: System MUST monitor the BIS QCO requirements applicable to confirmed products in watched suppliers' cases on the FR-040 schedule. Newly issued, amended, or withdrawn requirements MUST produce in-app alerts containing the affected product, previous and current requirement, official source reference, detection time, and effective date when stated. Uncertain applicability MUST be flagged for user review; source failure MUST preserve the last confirmed requirement and show check freshness.

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

- **Case**: A verification request encompassing a part specification, a set of suppliers, generated claims, collected evidence, and a final report. A case persists across days.
- **Supplier**: A company being evaluated — with identifiers (name, GST, website), source attribution, and a claim checklist.
- **Claim**: A verifiable assertion about a supplier, with proof criteria, entity/site, relevant period, processing state, verdict, and evidence chain. Compound assertions have separately evaluated subclaims.
- **Evidence Record**: A single data point collected from a specific source at a specific time — includes source URL/document, extracted data, timestamp, and a snapshot.
- **Check Attempt**: An auditable record of an attempted source or document check, including its outcome and any failure reason. It can exist without retrieved evidence.
- **Verdict**: The assessment of a claim: `proven`, `unproven`, or `contradicted`, with reasoning and links to evidence or, for absent evidence, check-attempt records. New verdicts retain the prior assessment history.
- **Country Pack**: A pluggable module that adds country-specific registry tools, compliance checks, and red-flag patterns to the shared agent core.
- **Supplier Index**: A persistent, searchable database of known manufacturers populated from EPC directories, trade data, and government sources. Grows over time across cases.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user with a part spec and 5 supplier names can receive an initial evidence table within 30 minutes of confirming case intake, excluding waits for human input or supplier replies. Every claim has a verdict and evidence or check-attempt references; inaccessible sources are recorded as failed checks rather than described as successfully checked. An initial report does not require outreach to complete.
- **SC-002**: The system's claim verdicts agree with a human auditor's assessment on at least 80% of claims across a test set of 30 suppliers.
- **SC-003**: The system reduces the time a purchase manager spends per supplier verification from an estimated 4–6 hours (phone calls, portal lookups, email back-and-forth) to under 1 hour of active user time.
- **SC-004**: Discovery mode returns at least 8 relevant candidates for a well-defined part spec + location query, sourced from at least 2 different data sources.
- **SC-005**: Users can complete case intake (part spec + supplier list entry) in under 5 minutes, whether using text, voice, or PDF upload.
- **SC-006**: Every verdict links to its reasoning and evidence citations, or to inspectable check-attempt records when no evidence was retrieved. All `proven` and `contradicted` verdicts have supporting retrieved evidence. No failed check is displayed as a successful lookup or given an invented source excerpt.
- **SC-007**: Case state survives a full server restart — no data loss for in-progress cases.
- **SC-008**: The system correctly identifies at least 3 out of 4 trader-posing-as-manufacturer patterns in a curated test set (e.g., mismatched business type, address inconsistency, breadth-of-product-range anomaly, headcount mismatch).
- **SC-009**: For at least 95 of 100 English part-specification recordings of 5–30 seconds each, the editable transcript is displayed within 5 seconds of the user stopping recording, measured end-to-end including upload and rendering. Test with one active transcription request at a time, the model already loaded, client upload bandwidth of at least 10 Mbps, and client-to-service round-trip latency of at most 100 ms. The implementation plan MUST identify a fixed reference deployment (processor/GPU, memory, model/version, and inference settings) before benchmarking; results MUST record that deployment, browser/version, audio format, and clip durations. Cold starts, longer clips, and concurrent requests MUST be measured and reported separately without being represented as satisfying this target. The user MUST be able to correct and confirm every transcript before submission.
- **SC-010**: Adding a second country pack requires only adding country-specific registry tools and configuration — no changes to the core verification engine.

---

## Assumptions

- Users have stable internet connectivity. Offline operation is not in scope.
- Users have access to a modern web browser (Chrome, Edge, Firefox). Internet Explorer is not supported.
- The Gemini API (or equivalent LLM API) is available and within budget for the project duration. If local LLM deployment is chosen, adequate GPU resources are available.
- Access methods, permissions, supported queries, quotas, and costs for external registries and discovery sources must be verified and documented during planning before live integration is selected. No particular free tier is assumed sufficient for discovery, the 30-supplier evaluation set, and recurring monitoring combined. Controlled test fixtures may exercise failure and change scenarios but must be labeled as simulated evidence, not presented as live verification.
- For government portal lookups that require CAPTCHA solving (GST, EPFO, MCA), the system uses the `ask_human` tool — it does not bypass CAPTCHAs programmatically.
- Email outreach is sent from the buyer's own email account via SMTP integration. The system does not provide its own sending infrastructure.
- WhatsApp outreach is out of scope for the initial build. Email is the primary outreach channel.
- The supplier index will initially cover Indian EPCs. Expansion to other countries' directories is a future effort.
- The system does not replace human judgment — it presents evidence and recommendations. The buyer always makes the final decision.
- Distil-Whisper Small (English) is the initial speech-to-text model. Multilingual support can be added by swapping to a larger model variant.
- PDF engineering drawings use a "best effort" VLM extraction approach — accuracy depends on drawing quality, and user confirmation is always required.
- IndiaMART listings are accepted as user-pasted identifiers, not fetched automatically. Source-specific permissions must be verified before adding any automated access.
