# Feature Specification: VeriSource — Approved Supplier Monitoring

**Feature Branch**: Not created; no branch hook is configured.

**Created**: 2026-10-16

**Status**: Draft

**Input**: User description: "Split recurring checks for buyer-approved suppliers into a feature that monitors certificate status and applicable BIS QCO changes, preserves check freshness and alerts the buyer without confusing source failure with a substantive change."

**Feature Directory**: `specs/007-approved-supplier-monitoring`

**Source**: [Product baseline](../001-supplier-verification-agent/spec.md); [ownership and dependency map](../README.md).

A buyer adds approved suppliers and their confirmed product requirements to a watchlist. Scheduled checks compare current certificate and applicable regulatory observations to previous records, then create attributable in-app alerts. The buyer decides whether to reopen verification or initiate outreach.

**Dependencies**: The [verification core](../002-supplier-verification-core/spec.md) supplies supplier/site identities, case products, evidence history and shared assessment rules. [Outreach](../005-supplier-outreach-followup/spec.md) is needed only if the buyer chooses to send a message from an alert; certificate and QCO monitoring must work without email.

Requirement IDs are local to this feature. The ownership map preserves links to all baseline IDs.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Watch an approved supplier's certificates (Priority: P1)

The buyer marks a supplier approved, adds it to monitoring and later sees that its certificate changed from active to suspended.

**Why this priority**: Approval must not hide later changes in the evidence supporting that decision.

**Independent Test**: Seed a verified supplier and certificate observation, add it to the watchlist, simulate a status change and run a controlled monitoring cycle.

**Acceptance Scenarios**:

1. **Given** a supplier has case-linked identity, site and certificate details, **When** the buyer marks it approved and adds it to the watchlist, **Then** the entry retains those references and shows the configured next-check schedule.
2. **Given** the initial 24-hour interval elapses, **When** a monitoring cycle runs, **Then** the current certificate status is checked against the previous observation and the check outcome and time are retained.
3. **Given** an identified certificate changes from active to suspended, withdrawn or expired, **When** the change is detected, **Then** the buyer sees an in-app alert with previous/current status, affected supplier/site/certificate, source and detection time.
4. **Given** the source does not state when the status actually changed, **When** the alert is displayed, **Then** the source-reported change date is labeled unknown and the detection time is not substituted for it.
5. **Given** an unchanged status is returned in a later cycle, **When** the cycle completes, **Then** the successful check freshness is updated without creating another alert for the unchanged observation.

---

### User Story 2 - Watch applicable product requirements (Priority: P2)

A new or amended BIS QCO may affect a product the buyer sources from a watched supplier. The buyer sees what changed and whether applicability requires review.

**Why this priority**: Regulatory requirements can change even when a supplier's certificate stays valid.

**Independent Test**: Seed a case product and prior applicability observation, then simulate newly issued, amended and withdrawn official requirements and an ambiguous match.

**Acceptance Scenarios**:

1. **Given** a watched supplier is linked to confirmed case products, **When** a scheduled cycle runs, **Then** the system checks the current applicable official QCO requirements for those products.
2. **Given** a relevant order is issued, amended or withdrawn, **When** the changed requirement is detected, **Then** an alert shows the affected product, previous/current requirement, official source, detection time and effective date when stated.
3. **Given** the available product description cannot establish applicability, **When** a potentially relevant requirement is found, **Then** the alert explicitly requests user review instead of asserting a definite licence obligation.
4. **Given** the same regulatory observation is returned repeatedly, **When** later cycles run, **Then** the system retains the check history without duplicating the same change alert.

---

### User Story 3 - Understand failed checks and decide what to do (Priority: P3)

The buyer can see a stale observation after a source outage, adjust monitoring or act on an alert by reopening verification or choosing outreach.

**Why this priority**: An unavailable source must never masquerade as a compliance change or a fresh successful check.

**Independent Test**: Simulate blocked/quota-limited sources, change the schedule, remove a watchlist entry and inspect the available actions on an alert.

**Acceptance Scenarios**:

1. **Given** a registry or QCO source is unavailable or quota-limited, **When** its check fails, **Then** the last confirmed status/requirement is preserved and the failed attempt and last successful check time are displayed separately.
2. **Given** an alert is shown, **When** the buyer chooses to review its evidence or reopen the linked case, **Then** the relevant supplier, product and observation history are available to the core without silently rewriting a closed report.
3. **Given** a supplier no longer needs monitoring, **When** the buyer removes it or changes the interval, **Then** subsequent cycles follow the updated selection/schedule and existing alerts and check history remain inspectable.
4. **Given** outreach is installed and the buyer chooses contact from an alert, **When** a message is proposed, **Then** the outreach feature's normal explicit approval gate applies before any send.

### Edge Cases

- A watched supplier has several factory sites or certificates: compare each identified certificate/site separately.
- A source outage affects only QCO checks: preserve valid certificate results and show partial monitoring failure.
- A change is detected after its effective date: show both dates honestly and do not claim it was detected earlier.
- An official order is future-effective: show the stated future date rather than asserting it already applies.
- A supplier was approved despite an unproven certificate claim: preserve the buyer's approval separately from the uncertain verification state.
- An entry is removed from monitoring: stop future recurring checks for that entry while retaining existing history.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST let the buyer mark suppliers approved and add/remove them from a monitoring watchlist linked to confirmed supplier/site identities, certificates and case products. Approval MUST remain a buyer decision separate from proof verdicts.
- **FR-002**: System MUST check watched certificate status through IAF CertSearch on a buyer-configurable schedule, initially once every 24 hours, preserving each check outcome and time.
- **FR-003**: System MUST compare observations for the same supplier, certificate and production site, preserving the previous/current values and check history rather than conflating unrelated certificates or sites.
- **FR-004**: System MUST create in-app alerts for changes to suspended, withdrawn or expired certificate status, identifying the supplier/site/certificate, previous/current status, source and detection time.
- **FR-005**: System MUST include a source-reported change date only when known and label it unknown otherwise; it MUST NOT represent detection time as the actual date of change.
- **FR-006**: System MUST check the official BIS QCO requirements applicable to confirmed case products linked to watched suppliers on the certificate-monitoring schedule.
- **FR-007**: System MUST alert for newly issued, amended or withdrawn applicable requirements with the product, previous/current requirement, official source, detection time and effective date when stated.
- **FR-008**: System MUST identify uncertain product applicability as requiring buyer review instead of claiming a definite compliance obligation.
- **FR-009**: System MUST preserve the last confirmed status/requirement on access failure, display the failed attempt and last successful check time, and distinguish partial failures from successful checks and substantive changes.
- **FR-010**: System MUST avoid repeated alerts for the same unchanged certificate/regulatory observation while retaining each check's freshness and outcome.
- **FR-011**: System MUST let the buyer inspect alert evidence, reopen a linked verification case and, when outreach is available, request contact under its approval rules. An alert MUST NOT silently alter a closed case report or send email.
- **FR-012**: System MUST apply watchlist removal or schedule changes to future cycles while preserving prior alerts, observations and check history.

### Key Entities

- **Watchlist Entry**: Buyer approval, supplier/site, linked certificates/products and configurable monitoring schedule.
- **Monitoring Observation**: Certificate status or applicable requirement from an attributable source and check time.
- **Monitoring Attempt**: Successful, partial or failed check with last-success freshness.
- **Change Alert**: Old/new observation, affected supplier/product, source, detection time and actual change/effective date when known.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a controlled-clock acceptance run, every active watchlist entry receives its configured check attempts at the initial 24-hour interval; removed entries receive none in subsequent cycles.
- **SC-002**: Each simulated active-to-suspended, active-to-withdrawn and active-to-expired change creates one correctly attributed alert with all required status/date/source fields.
- **SC-003**: Each newly issued, amended and withdrawn relevant QCO test creates one correctly attributed product alert; all ambiguous-applicability tests request buyer review.
- **SC-004**: Source-outage and quota-limit tests create zero false status/regulatory-change alerts, retain all last-confirmed observations and display accurate last-success times.
- **SC-005**: Repeating an unchanged monitoring observation generates zero duplicate change alerts while updating check freshness.
- **SC-006**: In every alert-action trial, the buyer can inspect the cited evidence and reopen the correct case; no email is sent or closed report rewritten without the required buyer action.

## Assumptions

- Registry and official QCO access, source capacity and monitoring costs must be verified during planning; no free-tier capacity is assumed sufficient.
- Initial monitoring is India-focused and linked to actual confirmed products, not a promise to detect every regulatory event globally.
- The initial 24-hour cadence is configurable. Tests may advance a controlled clock and use labeled change fixtures; those do not establish that live monitoring has been implemented.
- Detection time, source-reported status-change date and regulatory effective date are different facts and are retained separately.
- Certificate and product baselines come from the linked verification case or a first successful observation; absent previous values are shown as unknown rather than invented.
- Other status transitions may be recorded in history, but the mandatory certificate alerts in this feature are the suspended, withdrawn and expired transitions specified by the baseline.
- This is a draft specification, not a claim of implementation. The project constitution is still a template; adopting principles is a separate project step before constitution alignment can be established. Plans and task coverage have not been validated.
