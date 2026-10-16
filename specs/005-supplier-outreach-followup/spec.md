# Feature Specification: VeriSource — Supplier Outreach and Follow-Up

**Feature Branch**: Not created; no branch hook is configured.

**Created**: 2026-10-16

**Status**: Draft

**Input**: User description: "Split the baseline's multi-day email gap-resolution loop into a feature that drafts specific supplier requests, requires approval for each outgoing message, waits durably, processes replies and proposes follow-ups."

**Feature Directory**: `specs/005-supplier-outreach-followup`

**Source**: [Product baseline](../001-supplier-verification-agent/spec.md); [ownership and dependency map](../README.md).

A buyer resolves missing evidence by approving email requests, reviewing later supplier replies through updated evidence assessments and deciding whether to follow up. The feature owns email drafts, sending approval, reply association and waiting/follow-up behavior. Verification can still close with unresolved claims when outreach is skipped.

**Dependencies**: The [verification core](../002-supplier-verification-core/spec.md) owns durable case state, certificate reading, pending human actions and the Evidence and Verdict Policy. Outreach reuses those capabilities. Buyer-document intake and monitoring are not needed for outreach acceptance.

Requirement IDs are local to this feature. The ownership map preserves links to all baseline IDs.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Approve a specific request for missing evidence (Priority: P1)

The buyer sees an email asking a named supplier for the missing ISO certificate or evidence of capacity, edits it and chooses approve or skip.

**Why this priority**: The buyer must control every external communication and understand the evidence gap it addresses.

**Independent Test**: Start from a case with unproven claims, generate a draft, change its recipient/content and approve or reject it; inspect whether anything was sent.

**Acceptance Scenarios**:

1. **Given** a supplier has unproven claims with identified evidence gaps, **When** the system drafts outreach, **Then** the draft names the supplier, intended recipient and exact documents or facts requested, with references to the affected claims.
2. **Given** a draft is visible, **When** the buyer edits its recipient, subject, body or attachments, **Then** the final version remains unsent until explicitly approved.
3. **Given** a draft is approved, **When** the approved version is sent, **Then** the send record identifies the exact recipient, content, attachments, buyer approval and outcome, and the case records a waiting state.
4. **Given** the buyer rejects or skips outreach, **When** the case is closed, **Then** no message is sent and unresolved claims retain their existing unproven reasons.
5. **Given** an approved message changes before sending, **When** sending is attempted, **Then** the changed version requires fresh buyer approval.

---

### User Story 2 - Resume verification when the supplier replies (Priority: P2)

Days later, the supplier replies with a certificate PDF. The system associates it with the case, preserves prior evidence and re-evaluates the affected claims under the core policy.

**Why this priority**: New evidence must advance a durable case without bypassing proof rules.

**Independent Test**: Restart a waiting case, deliver a matched reply with an attachment, and inspect the new evidence and assessment history; repeat with unrelated and duplicate replies.

**Acceptance Scenarios**:

1. **Given** a request has been sent and the case is waiting, **When** the service fully restarts and three days pass, **Then** the approval, sent content, supplier association and pending wait remain intact.
2. **Given** a reply identifies an existing supplier conversation and case, **When** it arrives with an attachment, **Then** the case resumes automatically, the attachment is preserved as source evidence and affected claims are re-evaluated by the core.
3. **Given** a reply contains only a supplier assertion of capability, **When** the affected claim is reassessed, **Then** the statement remains self-reported and does not become proven without required corroboration.
4. **Given** the same reply is received twice, **When** reply processing runs again, **Then** the system retains one reply/evidence event and does not create duplicate assessments for that event.
5. **Given** a reply cannot be safely associated with one supplier/case, **When** it is received, **Then** the buyer is asked to associate it before it can alter any case verdict.

---

### User Story 3 - Review a follow-up or recover from delivery problems (Priority: P3)

The buyer sees a follow-up draft when no response arrives within the chosen wait period. A failed or uncertain delivery remains visible and never causes an unapproved repeat email.

**Why this priority**: Follow-up must remain accountable during long waits and interrupted sends.

**Independent Test**: Advance a controlled waiting period, reject and approve separate follow-up drafts, and simulate send failure and uncertain delivery.

**Acceptance Scenarios**:

1. **Given** a supplier has not replied by the configured waiting threshold, **When** the threshold is reached, **Then** the system proposes a follow-up draft and requests a new approval rather than sending automatically.
2. **Given** a reply arrives before a pending follow-up is sent, **When** the case resumes, **Then** the stale follow-up is paused for buyer review instead of being sent as if no response existed.
3. **Given** email access or delivery fails, **When** a send is attempted, **Then** the outcome is shown and the message is not marked successfully sent.
4. **Given** a restart leaves the send outcome uncertain, **When** processing resumes, **Then** the system requests reconciliation of the outcome and does not blindly send the message again.

### Edge Cases

- A supplier replies after the buyer closes the case: preserve the reply and ask whether to reopen rather than silently changing the closed report.
- A reply contains an unreadable or protected certificate: reuse the core human-action request and keep the affected claim unproven.
- A mail conversation includes several suppliers: require explicit supplier/case association for ambiguous attachments.
- Buyer email authorization is missing or revoked: preserve drafts and wait state; explain the connection failure without claiming a successful send.
- A scheduled follow-up is rejected: keep the unresolved claims and allow closure; do not keep resending approval requests for the same rejected draft.
- Delivery is uncertain after interruption: reconcile using the sending account or buyer review before another send.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST draft supplier-specific email requests identifying the missing document/information and the affected unproven claims.
- **FR-002**: System MUST present recipient, subject, body and attachments for buyer editing, approval or rejection before every initial outreach message and follow-up.
- **FR-003**: System MUST send only the explicitly approved version from the buyer's connected email account and retain that approval with the exact sent content and recipient. Changing those fields MUST require fresh approval.
- **FR-004**: System MUST use the core's durable case history to preserve drafts, approvals, send outcomes, supplier/conversation associations and pending waits across service restarts and multi-day delays.
- **FR-005**: System MUST detect supplier email replies associated with a case and automatically resume processing of their text and attached documents.
- **FR-006**: System MUST attribute reply evidence to its sender, supplier, case and received time and apply the core Evidence and Verdict Policy while preserving prior evidence and verdicts.
- **FR-007**: System MUST allow a configurable waiting period, initially three calendar days after a successful send, then propose a follow-up for a non-responsive supplier. Every follow-up MUST require its own explicit approval.
- **FR-008**: System MUST let the buyer skip or reject outreach/follow-up and close the case with unchanged unresolved verdicts; rejection MUST NOT send a message.
- **FR-009**: System MUST require buyer association for an ambiguous or unrelated reply before it can change a case's evidence or assessments.
- **FR-010**: System MUST recognize a repeated delivery of the same reply as one event and avoid duplicate evidence/assessment events or duplicate sends after a restart.
- **FR-011**: System MUST show failed or uncertain sending outcomes accurately, retain the approved draft and seek outcome reconciliation before repeating an uncertain send.
- **FR-012**: System MUST pause a pending follow-up for review when a reply arrives, and ask the buyer whether to reopen a closed case before applying a late reply.

### Key Entities

- **Outreach Draft**: Supplier, claims addressed, recipient, subject/body, attachments and editable version.
- **Approval**: Buyer decision tied to one exact message version.
- **Send Record**: Approved content, sending account, send time and confirmed, failed or uncertain outcome.
- **Reply**: Sender, received time, text/attachments and confirmed or ambiguous supplier/case association.
- **Waiting Action**: Last successful send, configurable deadline and follow-up decision state.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Across initial-send, changed-draft, rejection and follow-up trials, zero outgoing messages lack approval for their exact recipient, content and attachments.
- **SC-002**: After a full restart and a simulated three-day wait, every pending approval, approved message, send outcome and case/supplier association remains available without duplicate sending.
- **SC-003**: For each matched reply in the acceptance set, the intended case resumes and the evidence history includes its text/attachments; every reassessed verdict satisfies the core policy and no reply is applied to an unrelated case.
- **SC-004**: Duplicate reply and interrupted-send trials produce zero duplicate reply evidence events and zero blind repeated sends.
- **SC-005**: A non-responsive case produces a follow-up draft at its configured deadline, but sends none until approved; an intervening reply pauses the obsolete draft.
- **SC-006**: In rejection, email-access failure and uncertain-delivery trials, the buyer can see the actual state and close or resolve the case without any false successful-send status.

## Assumptions

- Email is the initial outreach channel; WhatsApp remains outside the agreed initial scope.
- Messages use the buyer's own connected account. Connection, permitted sending and incoming-reply access must be researched during planning; choosing a sending method alone does not establish reply detection.
- Three days is the initial configurable follow-up default derived from the baseline's multi-day example, not a guarantee that suppliers respond within that period.
- Reply attachments are supplier evidence, distinct from buyer BOM/drawing intake. Certificate reading and evidence assessment reuse the core.
- A controlled clock and labeled email fixtures may exercise multi-day acceptance without actually waiting three days or contacting real suppliers.
- This is a draft specification, not a claim of implementation. The project constitution is still a template; adopting principles is a separate project step before constitution alignment can be established. Plans and task coverage have not been validated.
