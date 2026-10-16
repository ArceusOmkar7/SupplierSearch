# Feature Specification: VeriSource — Voice-Based Conversational Intake

**Feature Branch**: Not created; no branch hook is configured.

**Created**: 2026-10-16

**Status**: Draft

**Input**: User description: "Split the baseline's self-hosted English voice intake into a feature with recording, editable transcription, technical-term review and explicit confirmation under the bounded five-second timing target."

**Feature Directory**: `specs/006-voice-intake`

**Source**: [Product baseline](../001-supplier-verification-agent/spec.md); [ownership and dependency map](../README.md).

A buyer speaks a part requirement, reviews and corrects the transcript, then submits it to the same intake confirmation used for typed text. Voice remains an additional input method, with clear recovery when permission, recording or transcription fails.

**Dependencies**: The [verification core](../002-supplier-verification-core/spec.md) owns requirement interpretation, confirmation and case creation. Voice supplies reviewed text to that shared intake; discovery, PDF intake and outreach are not needed to accept voice behavior.

Requirement IDs are local to this feature. The ownership map preserves links to all baseline IDs.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Speak and review a part requirement (Priority: P1)

The buyer records an English requirement for CF8M castings in Gujarat and sees an editable transcript in the conversation before any case is created.

**Why this priority**: Voice must reduce typing while preserving user control over technical input.

**Independent Test**: Record or supply a labeled sample, inspect the editable transcript, correct its text and confirm it through the core intake.

**Acceptance Scenarios**:

1. **Given** microphone permission is granted, **When** the buyer starts and stops a recording, **Then** the conversation clearly shows recording/processing states and displays an editable transcript when ready.
2. **Given** a transcript contains CF8M, ISO 9001 or another technical code, **When** the buyer reviews it, **Then** technical codes and any reported uncertain spans are visibly marked for review, and all transcript text remains editable.
3. **Given** the buyer changes a material grade or quantity, **When** the buyer confirms the reviewed text, **Then** the corrected text alone enters the core's requirement interpretation and confirmation step.
4. **Given** the transcript has finished processing but has not been confirmed, **When** the buyer waits or navigates the conversation, **Then** no case is submitted on the basis of that unconfirmed text.

---

### User Story 2 - Recover from unavailable or failed voice input (Priority: P2)

If microphone access is denied or transcription fails, the buyer continues with typed text or retries without losing prior input.

**Why this priority**: Voice availability must not make the primary intake journey unusable.

**Independent Test**: Deny permission, simulate an unsupported recorder and failed/empty transcription, and verify typed input remains available.

**Acceptance Scenarios**:

1. **Given** microphone access is denied or recording is unsupported, **When** the buyer selects voice input, **Then** the system explains the problem and retains usable typed intake.
2. **Given** transcription takes longer than five seconds, **When** the buyer views the conversation, **Then** the actual processing state is shown without submitting incomplete text or claiming the timing target was met.
3. **Given** transcription fails, is empty or the buyer cancels, **When** the outcome is displayed, **Then** existing text remains intact and the buyer can retry or continue typing.
4. **Given** a transcription result arrives after the buyer has chosen typed input, **When** the result becomes available, **Then** it does not overwrite the buyer's newer text without their acceptance.

---

### User Story 3 - Receive timely transcripts under a repeatable workload (Priority: P3)

The buyer sees short-recording transcripts promptly under the agreed reference conditions; slower or longer recordings remain honestly reported.

**Why this priority**: A bounded target is needed to evaluate voice responsiveness without overstating performance.

**Independent Test**: Measure the acceptance workload defined below from stopping recording to editable transcript display, with separate reporting for other workloads.

**Acceptance Scenarios**:

1. **Given** 100 English clips satisfying the acceptance conditions are prepared, **When** their end-to-end latency is measured, **Then** at least 95 display editable transcripts within five seconds of recording stopping.
2. **Given** a cold start, longer clip or simultaneous request is measured, **When** results are reported, **Then** those results are separate from the bounded target and any slow processing remains visible to the buyer.

### Edge Cases

- Material grades or spoken numbers are transcribed incorrectly: retain the editable transcript and require user confirmation rather than silently interpreting uncertain codes.
- The transcription service provides no word-level confidence: still mark recognizable technical codes for review; do not fabricate confidence scores.
- A recording contains silence or unintelligible speech: explain that no usable transcript was obtained and offer retry or typing.
- The buyer cancels during upload or processing: do not submit the result later without renewed confirmation.
- A recording exceeds the timing workload's duration: allow the normal processing/review flow and report its timing separately rather than promising five seconds.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a microphone control in the conversation with start, stop and cancel actions and visible recording/processing states.
- **FR-002**: System MUST transcribe recordings through a project-controlled speech service and display the resulting text as an editable draft in the conversation.
- **FR-003**: System MUST mark recognizable technical codes and any transcription-reported uncertain spans as needing review. When confidence information is unavailable, it MUST NOT invent scores or imply highlighted spans are the only possible errors.
- **FR-004**: System MUST let the buyer edit highlighted spans and all other transcript text before confirmation.
- **FR-005**: System MUST pass only the buyer-reviewed, explicitly confirmed transcript into the core's common requirement interpretation/confirmation flow; an unconfirmed recording or draft MUST NOT create a verification case.
- **FR-006**: System MUST keep typed intake available when recording is unsupported, permission is denied, transcription is empty/failed or the buyer cancels, preserving existing typed text.
- **FR-007**: System MUST show processing that exceeds the five-second target as ongoing, expose actual failures and offer retry or typing without claiming a successful or timely transcript.
- **FR-008**: System MUST not overwrite newer buyer text or submit a canceled recording when a delayed transcription result arrives.

### Key Entities

- **Recording**: Buyer-controlled audio capture and recording, processing or cancellation state.
- **Transcript Draft**: Editable text associated with the recording and any uncertainty information actually available.
- **Review Span**: Technical code or reported uncertain portion marked for buyer review, without an unsupported accuracy guarantee.
- **Confirmed Transcript**: Buyer-approved text passed into the core's shared intake.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For at least 95 of 100 English part-specification recordings lasting 5–30 seconds, an editable transcript appears within five seconds of recording stopping, including upload and display time, under the acceptance conditions below.
- **SC-002**: In five voice-intake trials using a prepared part description and supplier list, each buyer can record, correct and reach confirmed intake in under five minutes without assistance.
- **SC-003**: In every technical-code review test, the buyer can correct the marked term and every submitted field derives from confirmed text; zero cases start from an unconfirmed transcript.
- **SC-004**: In every permission, unsupported-recording, empty-result, failure and cancel trial, typing remains usable and previously entered text is retained.
- **SC-005**: Late-result and slow-processing trials cause zero silent text replacements or automatic submissions and display the actual current state.

## Assumptions

- Initial transcription is English-only. Multilingual input is a future change and is not implied by model interchangeability.
- Acceptance conditions for SC-001 are one active transcription at a time, the service already ready to transcribe, client upload bandwidth of at least 10 Mbps and client-to-service round-trip latency no more than 100 ms. A fixed reference deployment and browser/audio versions must be documented before measurement. Cold starts, longer clips and simultaneous requests are measured separately.
- The implementation plan must record processor/accelerator, memory, model/version and inference settings for that reference deployment, preserving the remediated baseline's transcription reproducibility conditions without claiming a benchmark already passed.
- The baseline's chosen speech-model preference and self-hosting constraint remain planning context. This specification mandates project-controlled transcription without prescribing a framework or model library.
- Highlighting is a review aid, not a guarantee of calibrated uncertainty or correct unhighlighted text. Technical codes are flagged even when no confidence is supplied.
- Recognizable technical codes include alphanumeric material grades and a certification name followed by a number; the acceptance samples include CF8M and ISO 9001. Other text remains editable through the same review.
- This is a draft specification, not a claim of implementation. The project constitution is still a template; adopting principles is a separate project step before constitution alignment can be established. Plans and task coverage have not been validated.
