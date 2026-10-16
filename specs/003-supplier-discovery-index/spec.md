# Feature Specification: VeriSource — Supplier Discovery and Index

**Feature Branch**: Not created; no branch hook is configured.

**Created**: 2026-10-16

**Status**: Draft

**Input**: User description: "Split the baseline's discovery and supplier-index capabilities into one feature that ingests permitted Indian directory and trade sources, finds candidates with source attribution, and hands a buyer-reviewed list to verification."

**Feature Directory**: `specs/003-supplier-discovery-index`

**Source**: [Product baseline](../001-supplier-verification-agent/spec.md); [ownership and dependency map](../README.md).

A buyer with no supplier list searches by confirmed part requirements and location, reviews source-labeled candidates and sends a chosen list to verification. This feature also owns directory ingestion and incremental supplier-index updates. Finding a candidate does not prove manufacturing capability.

**Dependencies**: The [verification core](../002-supplier-verification-core/spec.md) owns confirmed requirements, supplier identity resolution and verification verdicts. Discovery can be accepted independently using a confirmed sample requirement and source fixtures; handoff is verified against the core's intake contract.

Requirement IDs are local to this feature. The ownership map preserves links to all baseline IDs.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Find and review candidates for a part (Priority: P1)

A buyer looking for EN8 closed-die forgings in western India searches the existing supplier index and live sources, then reviews candidates before any verification starts.

**Why this priority**: The buyer needs attributable leads even without an existing supplier list.

**Independent Test**: Search with a prepared part/location query against a populated index and controlled live-source responses, then inspect the candidate list and its origins.

**Acceptance Scenarios**:

1. **Given** confirmed product, process/material and location criteria are available, **When** discovery starts, **Then** the existing index is queried first and results are supplemented with web search and a certification scope/location search.
2. **Given** at least eight relevant unique candidates exist across two independent origins in the acceptance sources, **When** results are displayed, **Then** the buyer receives 8–20 candidates with company name, location, source labels and website when known.
3. **Given** a candidate is found through several channels, **When** its card is inspected, **Then** each underlying origin and reference is shown; an index copy and a web-search copy of one original directory do not count as two independent origins.
4. **Given** a source is blocked, unavailable or returns fewer matches than requested, **When** discovery completes, **Then** the system displays actual matches and source failures without inventing companies or implying the requested coverage was achieved.

---

### User Story 2 - Maintain a supplier index from multiple source families (Priority: P2)

A project operator adds EPC directories, permitted public portal records and authorized trade data so buyers can find suppliers across manufacturing sectors.

**Why this priority**: Reusable source records make discovery more than a repeated web search.

**Independent Test**: Ingest sample records from each source family, repeat the import and refresh one source; compare searchable results and source history.

**Acceptance Scenarios**:

1. **Given** permitted EPC member PDFs and public EPC portal records are available, **When** the operator imports them, **Then** supplier names, locations, sector/product descriptions, identifiers and source references are searchable, with absent fields left unknown.
2. **Given** authorized government MSME and trade records are supplied, **When** they are imported alongside EPC data, **Then** the index preserves each record's origin and covers all three source families.
3. **Given** an existing directory is refreshed and a new source is added, **When** incremental updating runs, **Then** new or changed records become searchable without rebuilding unrelated sources, and unchanged records are not duplicated.
4. **Given** portal access rules or rate limits prevent collection, **When** an update runs, **Then** the affected operation is stopped or deferred, the outcome is recorded and previously collected data retains its collection date.
5. **Given** one supplier has different facts in successive source versions, **When** the index is inspected, **Then** old and new observations and source/collection dates remain distinguishable rather than silently erasing provenance.

---

### User Story 3 - Curate the list and hand it to verification (Priority: P3)

The buyer adds a referral, removes unsuitable matches and orders the remaining suppliers before starting a verification case.

**Why this priority**: The buyer must control which companies are evaluated and avoid duplicate work.

**Independent Test**: Combine user-provided and discovered records with known duplicates and ambiguous identities, edit the list, then inspect the selected supplier handoff.

**Acceptance Scenarios**:

1. **Given** a list contains confirmed same-entity duplicates, **When** records are reconciled, **Then** the richer nonconflicting fields and all origins are retained in one candidate.
2. **Given** similar names or a shared identifier have conflicting identity/site details, **When** deduplication runs, **Then** the system flags the conflict for review rather than silently combining potentially different entities.
3. **Given** the buyer adds, removes and reorders candidates, **When** the buyer starts verification, **Then** only the final ordered selection and confirmed part requirements are passed to the core, with supplier identifiers and provenance intact.

### Edge Cases

- A query has fewer than eight real matches: return the actual count with the coverage gap; do not pad the list.
- All available results trace to one publisher: state that only one independent origin was found even if several search channels returned it.
- A source is refreshed with a malformed or partial document: record the failed/partial import without deleting unaffected indexed records.
- A directory contains a trader or exporter: retain its source description without promoting it to a proven manufacturer.
- A record has only a company name: keep missing identity and website fields unknown and let the buyer review the ambiguity.
- A website's collection conditions are unknown: defer automated collection until permissions are verified; authorized document import remains distinguishable from live collection.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept confirmed part descriptions, material/process requirements and location preferences for discovery when no supplier list is provided.
- **FR-002**: System MUST query its existing Supplier Index before supplementing results with live discovery, without requiring an external request for the index lookup.
- **FR-003**: System MUST discover additional candidates through web search using the confirmed part and location criteria.
- **FR-004**: System MUST support IAF CertSearch candidate discovery by relevant certification scope and location through a permitted access method; unavailable access MUST be recorded as a source limitation.
- **FR-005**: System MUST maintain a searchable Supplier Index populated from EPC member directories, government MSME records and authorized trade-data sources, preserving the origin of every imported record.
- **FR-006**: System MUST extract supplier records from EPC directory PDFs, including company name, location, sector/product description, available identifiers and source-document reference, leaving unavailable fields unknown.
- **FR-007**: System MUST collect permitted publicly accessible EPC portal records while respecting the source's access conditions, robots directives and rate limits, and record any blocked or deferred collection.
- **FR-008**: System MUST add sources and refresh changed records incrementally without rebuilding unrelated data or duplicating unchanged records.
- **FR-009**: System MUST label each candidate with every known underlying source origin, source reference and collection time, distinguishing the originating publisher from the channel or index through which it was found.
- **FR-010**: System MUST let the buyer add, remove and reorder suppliers before verification; the final selection alone MUST control the handoff.
- **FR-011**: System MUST reconcile known same-entity duplicates across supplied and discovered records using corroborating identifiers and address roles, retaining richer nonconflicting fields and all provenance. Conflicting identity details MUST require review rather than automatic merging.
- **FR-012**: System MUST display source failures, unavailable access and actual result counts; it MUST NOT invent candidates, hide single-origin coverage or treat discovery labels as verified capability.
- **FR-013**: A relevant candidate MUST have an attributable product/process description matching the query's required category and location, with any unknown material or capacity requirement shown as unverified. Relevance MUST NOT be presented as a verification verdict.
- **FR-014**: System MUST hand confirmed requirements, selected supplier identifiers, order and source observations to the core without assigning proof verdicts or silently altering the buyer's selection.
- **FR-015**: System MUST retain collection dates, source versions and import outcomes so refreshed, stale and failed records can be distinguished; a failed refresh MUST NOT delete unaffected searchable records.

### Key Entities

- **Discovery Request**: Confirmed part, process/material and location criteria.
- **Candidate**: Potential supplier with identity details, matching description, unverified fields and attributed origins.
- **Source Observation**: Supplier facts from one publisher/document and collection time, independent of the retrieval channel.
- **Supplier Index**: Searchable observations across authorized source families and versions.
- **Import Run**: Source/version, processed records, changes and partial/failed collection outcomes.
- **Selected Supplier List**: Buyer-reviewed ordered list handed to verification.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For each of ten documented representative queries with at least eight relevant unique suppliers across two independent origins in the evaluation corpus, discovery returns 8–20 relevant candidates from at least two origins. Report results separately for live and simulated sources.
- **SC-002**: Every displayed candidate has a source reference and location or explicit unknown-location marker, and duplicate channels for one publisher are never counted as independent origins.
- **SC-003**: An acceptance import spanning at least two manufacturing sectors and EPC, government MSME and trade sources makes all valid sample records searchable; repeating it creates zero duplicate unchanged records.
- **SC-004**: Refreshing one source and adding another preserves 100% of unaffected records and their provenance without a full rebuild.
- **SC-005**: In all list-editing and handoff trials, the core receives exactly the buyer's selected suppliers in the chosen order, with no removed supplier included.
- **SC-006**: For zero-result, single-origin and source-outage trials, the buyer sees the actual coverage and can revise the query or supply candidates manually without any invented result.

## Assumptions

- Indian manufacturing coverage begins broadly across sectors. The acceptance corpus spans at least two sectors; the feature does not promise exhaustive coverage of every council or company.
- Planning must identify actual permitted sources and verify search capabilities, quotas and access costs. A failure-path demonstration does not establish a mandatory live integration as implemented.
- MSME and trade records may be supplied through authorized exports or documents where permitted; the method and whether data is live or imported must remain visible.
- Discovery does not establish legal existence, certificate validity or capability. All such verdicts belong to the core.
- Source refreshes are operator-triggered for initial acceptance; recurring index maintenance can use the same incremental behavior without introducing a new product capability.
- This is a draft specification, not a claim of implementation. The project constitution is still a template; adopting principles is a separate project step before constitution alignment can be established. Plans and task coverage have not been validated.
