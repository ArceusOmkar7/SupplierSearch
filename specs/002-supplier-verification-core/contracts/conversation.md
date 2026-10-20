# Conversation and Interaction Contract

**Date**: 2026-10-17 | **Scope**:002 | **Related**: [API](http-api.md), [plan](../plan.md)

The primary workspace is a conversation with interactive components. Case list and sign-in are navigation; supplier/evidence/approval interactions stay inside the case conversation. This contract defines behavior/state, not a finished visual design.

## Components and gates

| Component | Required behavior and states |
|---|---|
| Requirement review | Entire interpretation editable, field provenance and uncertainty visible; missing required fields explained. Show supplier identifiers and location choices. Explicit Confirm creates an immutable revision; unhighlighted text is never guaranteed correct. |
| Supplier identifiers | Buyer adds/edits/removes identifiers in a draft. Distinguish names, websites, legal IDs and pasted listing URLs. IndiaMART link text is retained without automatic fetching/preview. Same-name or conflicting GST records prompt review, not silent merge. |
| Claim checklist | Separate claim/subclaim assertion, site/period and proof criteria. Buyer may add/remove/edit claims and choose required-for-shortlist flags. Confirm checklist precedes collection; at least one required claim is needed. |
| Collection progress | Independent checks with queued/checking/complete/no-evidence/waiting-input state and truthful source coverage. Scraping runs unattended. Blocked sources show unavailable evidence and alternatives tried without portal/CAPTCHA instructions. |
| Document action | Locked/unreadable buyer upload can request replacement/unlocked document. Show exactly affected checks; other suppliers/checks continue. Browser closure/restart preserves the request. |
| Identity review | Preserve original addresses and office/factory roles; show matching identifiers and unresolved conflicts. Fuzzy name score proposes a link but cannot supply proof. |
| Evidence matrix | Supplier rows and claim columns; exactly one permitted verdict for each evaluated cell. Expand reasoning, criteria/subclaims, source/document/page, observed dates, actual attempts, conflicts and missing evidence. Separate processing state and historical result labels. |
| Qualified shortlist | Only all required claims proven; explicit no-qualified-supplier state when empty. Follow-up candidates appear separately with evidence gaps. Required contradicted remains in assessment with reason, excluded from both lists. |
| Buyer decision | Explicit selection/rejection/no-selection attached to the displayed snapshot. Recommendation cannot automatically approve/contact a supplier or alter evidence. |
| Revision history | Show revision/checklist version and assessed time. Changed confirmed requirements create another draft in the same case; reconfirm and re-evaluate affected claims. Earlier inputs/evidence/results remain inspectable and clearly historical. |
| Report | Export the chosen immutable snapshot. Show generating/ready/failed and retry. PDF has same revision, verdicts, sources/dates, lists and gaps as the displayed snapshot; a newer snapshot does not overwrite an old PDF. |
| Close/reopen | Buyer can close with gaps without outreach. Closed snapshot remains immutable. Reopen/revise/recheck is explicit owner action; new results become later history. |
| Retention/delete | Closing never triggers expiry. Explain retention until owner deletion; explicit delete revokes access immediately. Show purge pending/retrying/completed only after local files/records/checkpoints and affected managed snapshots are verified removed. No cloud expiry promise or recalled-download claim. |

## Loading, empty, error and interruption states

- Empty case invites requirement and known supplier entry; no discovery results or invented suppliers in002.
- Model interpretation/loading retains editable input and supports safe retry without duplicating messages. Failure offers correction/retry and does not silently confirm a draft.
- No evidence means an unproven cell with actual attempt reason, not an invented quotation or fourth verdict. No record is not counterfeit proof. Unknown source coverage remains visible.
- Blocked/disabled source offers a plain-language coverage explanation and eligible free alternatives, with no mandatory paid-upgrade path. Operator source/import configuration stays outside the buyer flow.
- Only actual supplier/official records populate the application. No demo suppliers, synthetic datasets or fabricated evidence are seeded. Actual captured-source replay shows original source dates and a replay label; an old government export cannot be labeled current because it was imported today.
- Partial snapshots show pending checks/actions and remain exportable; independent completion does not require every human action to finish. Five-supplier benchmark timing is not promised for an unmeasured larger workload.
- SSE disconnect preserves the last snapshot, marks reconnecting and resumes from durable sequence. Reconnection never restarts a run. Failed event recovery refetches current authorized state.
- Stale two-tab edits show a conflict and reload comparison; no silent overwriting confirmed input. Late earlier-revision results cannot replace current revision labels/verdicts.
- Signed-out view requires sign-in before private content. Nonowner/deleted references use a generic unavailable message with no private title/excerpts. Logout clears cached case state and terminates streams; browser back/cache must not re-fetch private bytes without authentication.
- Deletion failures keep access revoked and display retrying metadata; completion requires verified active purge. No job/model response/upload can resurrect the case.

## Accessibility and language

Target WCAG2.2 AA behavior for core components: programmatic labels, keyboard-only edits/confirmation, visible focus, accessible expandable cell controls and dialogs, announced progress/errors, semantic table headers, sufficient contrast and verdict text/icons as well as color. Large tables allow horizontal scrolling without losing supplier/claim context. Focus returns to the initiating control after expansions/dialogs; background events do not steal focus. Announce meaningful progress changes without reading every log event.

English is the initial interface and OCR evaluation baseline; retain original Unicode source names/addresses and document unsupported extraction language. Localize displayed dates/quantities without changing canonical UTC/unit values. No speech controls, drawing editor or unsupported-country completeness claim appears in002.

## Acceptance behaviors on real records

1. Buyer confirms an actual part request, then changes quantity. The conversation creates another revision, requires confirmation and never relabels earlier capacity verdicts as current proof.
2. A supplier portal is CAPTCHA-blocked while another supplier's website succeeds. Collection completes permitted alternatives automatically, displays the blocked attempt and continues other checks without asking the buyer to browse.
3. All suppliers lack independent capability records. Qualified shortlist is empty; eligible follow-up candidates show missing evidence explicitly. Supplier marketing text cannot fill the shortlist.
4. Buyer opens an evidence cell and exports its snapshot. PDF references the same claim, revision, evidence/attempts and dates, even if another run later completes.
5. Buyer deletes a case. Lists/content/downloads stop exposing it immediately; a metadata-only tracker shows local and managed-snapshot purge. Another buyer's case remains available.
