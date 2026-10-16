# Feature Specification: VeriSource — PDF and Drawing Intake

**Feature Branch**: Not created; no branch hook is configured.

**Created**: 2026-10-16

**Status**: Draft

**Input**: User description: "Split buyer BOM, purchase-order, specification and engineering-drawing intake into a feature that extracts structured requirements, falls back to visual interpretation, and requires correction and confirmation before verification."

**Feature Directory**: `specs/004-pdf-drawing-intake`

**Source**: [Product baseline](../001-supplier-verification-agent/spec.md); [ownership and dependency map](../README.md).

A buyer uploads a PDF and reviews extracted part requirements, including separate line items, before creating cases. This covers text documents, scanned pages and engineering drawings. Reading supplier certificate documents remains owned by the verification core.

**Dependencies**: The [verification core](../002-supplier-verification-core/spec.md) owns confirmed case requirements and the common confirmation gate. This feature supplies draft fields and source references to that gate; its extraction/review journey can be tested using documents without running verification.

Requirement IDs are local to this feature. The ownership map preserves links to all baseline IDs.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Review requirements from a text-based document (Priority: P1)

A buyer uploads a purchase order containing three BOM lines, corrects one material grade and confirms the intended requirements for each line.

**Why this priority**: Existing buyer documents should become usable requirements without manual retyping.

**Independent Test**: Upload a labeled three-item BOM, inspect extracted values and page references, correct one value, and compare the resulting confirmed cases to the approved fields.

**Acceptance Scenarios**:

1. **Given** a text-based BOM PDF contains part descriptions, material grades, quantities and required certifications, **When** the buyer uploads it, **Then** the system proposes those fields per line item and preserves the relevant page/text reference.
2. **Given** three distinct BOM items have been extracted, **When** the buyer reviews the result, **Then** the items remain separately editable and a missing field in one item is not filled using another item's value.
3. **Given** the buyer corrects a material grade or quantity and confirms all selected items, **When** case creation proceeds, **Then** one case per selected line item receives the confirmed values and source references, while the raw extraction remains inspectable.

---

### User Story 2 - Review a scanned document or drawing (Priority: P2)

A buyer uploads a scanned drawing whose text cannot be read reliably. The system interprets the visible content and asks the buyer to confirm the proposed part number, material, tolerances and notes.

**Why this priority**: The agreed intake scope includes drawings and scans with an explicit human review step.

**Independent Test**: Upload labeled scanned, mixed-content and rotated drawing samples; inspect fallback behavior, uncertainty markers and user corrections without promising perfect automatic extraction.

**Acceptance Scenarios**:

1. **Given** a page is scanned or ordinary extraction yields missing required fields, unreadable characters or conflicting layout, **When** document interpretation proceeds, **Then** the system uses the page's visual content to propose fields rather than treating failed text extraction as successful.
2. **Given** a drawing contains part number, material, tolerance and manufacturing notes, **When** visual interpretation produces draft fields, **Then** each proposed value retains its page reference and any ambiguity is highlighted.
3. **Given** a material code is ambiguous or a dimension is unreadable, **When** the review is displayed, **Then** the system marks the field as needing review and leaves unreadable values unknown instead of guessing.
4. **Given** the buyer has not confirmed the reviewed values, **When** the document has finished processing, **Then** no claims are generated and no case enters verification.

---

### User Story 3 - Recover from an unreadable upload (Priority: P3)

The buyer can replace a protected or damaged PDF or enter requirements manually without losing confirmed information.

**Why this priority**: Document limitations must not force invented requirements or block text intake.

**Independent Test**: Upload protected and malformed files, then provide a readable replacement or use text input.

**Acceptance Scenarios**:

1. **Given** an uploaded PDF is password-protected or damaged, **When** reading fails, **Then** the buyer receives a specific explanation and can provide an unlocked/replacement document or continue with typed requirements.
2. **Given** some pages are readable and others fail, **When** the review is displayed, **Then** usable extracted fields are retained, failed pages are identified and unresolved required fields need buyer input before confirmation.

### Edge Cases

- A PDF mixes readable text and scanned pages: choose the appropriate interpretation per affected page; do not discard successful fields.
- Drawing content is rotated or handwritten: show uncertain values and allow correction; do not claim perfect interpretation.
- A BOM quantity lacks a unit or period: ask the buyer to supply it rather than borrowing a neighboring line's unit.
- Two pages disagree about material grade: show both page references and require the buyer to select the confirmed value.
- A replacement upload is supplied after editing: preserve the prior review until the buyer explicitly accepts replacement values.
- A document contains no identifiable part requirements: report that result and offer manual intake rather than creating an empty case.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept buyer-uploaded PDF BOMs, specification sheets, purchase orders and engineering drawings as an additional case-intake method.
- **FR-002**: System MUST extract draft part descriptions, material grades, quantities/units/periods and certification requirements from text-based documents, preserving per-item boundaries and source-page/text references.
- **FR-003**: System MUST fall back to visual page interpretation when a page is image-based or text extraction lacks required fields, contains unreadable characters or cannot resolve the layout, and MUST preserve successfully extracted content from other pages.
- **FR-004**: System MUST propose visible drawing part numbers, materials, tolerances and manufacturing notes with page references; values that cannot be read MUST remain unknown.
- **FR-005**: System MUST highlight missing, ambiguous or conflicting draft fields, let the buyer edit any proposed value and use the core's shared explicit confirmation gate before creating claims.
- **FR-006**: System MUST retain draft extraction and buyer corrections separately and transfer only confirmed values and their source references into verification.
- **FR-007**: System MUST let the buyer select and confirm individual BOM lines and create one case per selected item without mixing requirements between items.
- **FR-008**: System MUST identify protected, damaged, empty or partially unreadable documents and affected pages, preserve usable review data, and allow replacement, unlocked-file submission or typed intake.

### Key Entities

- **Uploaded Requirement Document**: Buyer PDF, page references and processing outcomes, separate from supplier certificate evidence.
- **Extracted Item**: Draft fields for one part or BOM line, including quantity units/periods.
- **Field Observation**: Proposed value, source-page/text reference and missing, ambiguous or conflicting state.
- **Confirmed Item**: Buyer-approved values and correction history passed to the core as one case.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In five intake trials using readable BOM/specification PDFs of up to five pages and three line items, each buyer can upload, review, correct and confirm the selected requirements in under five minutes, with a prepared supplier list when needed.
- **SC-002**: In a labeled acceptance corpus containing a text BOM, a scanned drawing, a mixed-content PDF and an ambiguous-code sample, every required field is either proposed with a page reference or explicitly marked unknown/for review; no missing value is silently fabricated.
- **SC-003**: Across all confirmation tests, 100% of case fields match the buyer-confirmed values, no unselected BOM line creates a case and no case combines two items' requirements.
- **SC-004**: Every scanned or failed-text sample exercises the visual fallback, and all ambiguity/conflict samples expose a reviewable field before confirmation.
- **SC-005**: For protected, damaged and partially unreadable samples, the buyer can replace the file or use typed intake without losing previously confirmed information or starting verification on unconfirmed fields.

## Assumptions

- Drawing interpretation is best effort. Buyer confirmation is mandatory for every document; automatic recovery of every dimension or tolerance is not promised.
- The five-minute target uses bounded readable samples. Longer or ambiguous drawings are measured separately and must not be reported as satisfying that workload.
- Text-first and visual-fallback behavior is an agreed capability; model, rendering and extraction technology choices belong in the implementation plan.
- Source references from a buyer document establish what was requested, not proof that a supplier can manufacture it.
- The baseline's common confirmation requirement is owned by the core. This feature consumes that shared rule rather than redefining it.
- This is a draft specification, not a claim of implementation. The project constitution is still a template; adopting principles is a separate project step before constitution alignment can be established. Plans and task coverage have not been validated.
