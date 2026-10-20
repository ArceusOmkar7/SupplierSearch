/** Shapes returned by the local API (see specs/002-supplier-verification-core/contracts). */
export interface Identifier { type: string; value: string; normalized?: string }

export interface SupplierEntry {
  supplier_id: string;
  display_name: string;
  identifiers: Identifier[];
  address: string | null;
  address_role: string | null;
  site_id: string | null;
}

export interface Quantity { value: number; unit: string; period: string | null }

export interface Requirements {
  part_description: string | null;
  materials: string[];
  processes: string[];
  quantity: Quantity | null;
  certifications: string[];
  tolerance: string | null;
  standards: string[];
}

export interface Location {
  country: string | null;
  reference_location: string | null;
  radius: { value: number; unit: string } | null;
}

export interface Provenance { source: string; at: string; quote?: string }

export interface ReviewFlag { code: string; type: string; supplier_indexes: number[] }

export interface Revision {
  id: string;
  case_id: string;
  sequence: number;
  status: 'draft' | 'confirmed' | 'abandoned';
  requirements: Requirements;
  missing_fields: string[];
  field_provenance: Record<string, Provenance>;
  location: Location;
  suppliers: SupplierEntry[];
  review_flags: ReviewFlag[];
  input_provenance: Record<string, unknown>;
  confirmed_at: string | null;
  confirmed_by: string | null;
  created_at: string;
  etag: string;
}

export interface CaseSummary {
  id: string;
  title: string;
  state: string;
  active_revision_id: string | null;
  latest_snapshot_id: string | null;
  version: number;
  created_at: string;
  closed_at: string | null;
  etag: string;
  draft_revision_id?: string | null;
  latest_run_id?: string | null;
  latest_run_state?: string | null;
}

export interface Criterion {
  criterion_id: string;
  assertion: string;
  evidence_class: string;
  authority: string[];
  independent_corroboration: boolean;
  constraints: Record<string, boolean>;
  missing_evidence_condition: string;
}

export interface Claim {
  id: string;
  supplier_id: string;
  site_id: string | null;
  parent_claim_id: string | null;
  type: string;
  assertion: string;
  relevant_period: Record<string, unknown>;
  required_for_shortlist: boolean;
  proof_criteria: { criteria: Criterion[] };
  processing_state: string;
  waiting_input: boolean;
}

export interface Checklist {
  id: string;
  case_id: string;
  revision_id: string;
  sequence: number;
  status: 'draft' | 'confirmed';
  policy_version: string;
  confirmed_at: string | null;
  claims: Claim[];
  etag: string;
}

export interface Run {
  id: string;
  state: string;
  mode: string;
  requested_at: string;
  started_at: string | null;
  initial_deadline: string;
  completed_at: string | null;
  task_count: number;
  task_states: Record<string, number>;
  etag: string;
}

export interface RunTask {
  id: string;
  supplier_id: string;
  check_type: string;
  source_id: string;
  state: string;
  dependency_ids: string[];
  wait_action_id: string | null;
}

export interface SourceCapability {
  source_id: string;
  enabled: boolean;
  claim_types?: string[];
  disabled_reason?: string | null;
}

export interface BuyerAction {
  id: string;
  type: 'supply_unlocked_document' | 'resolve_identity';
  state: 'pending' | 'resolved' | 'cancelled';
  run_id: string;
  affected_task_ids: string[];
  requested_document_id: string | null;
  etag: string;
}

export interface CaseEvent {
  sequence: number;
  type: string;
  case_id: string;
  revision_id: string | null;
  run_id: string | null;
  created_at: string;
  payload: Record<string, unknown>;
}

export interface Page<T> { items: T[]; next_cursor: string | null }

export type Verdict = 'proven' | 'unproven' | 'contradicted';

export interface EvidenceView {
  id: string;
  source_ref: string;
  locator: string;
  observation: string;
  authority_role: string;
  self_reported: boolean;
  origin_lineage: string;
  collected_at: string;
  issued_at: string | null;
  expires_at: string | null;
  replay: boolean;
  identity_state: string | null;
  identity_basis: string | null;
}

export interface ConsideredRecord {
  evidence_id: string;
  reason: string;
  criterion_id: string;
  observation: string;
  source_ref: string;
  authority_role: string;
  issued_at: string | null;
}

export interface AttemptView {
  id: string;
  kind: string;
  target: string;
  outcome: string;
  reason_code: string | null;
  request_dispatched: boolean;
  http_status: number | null;
}

export interface CriterionResultView {
  criterion_id: string;
  label?: string;
  outcome: 'satisfied' | 'refuted' | 'insufficient';
  reasoning: string;
}

export interface SnapshotClaim {
  claim_id: string;
  parent_claim_id: string | null;
  type: string;
  assertion: string;
  required: boolean;
  relevant_period: Record<string, unknown>;
  verdict: Verdict | null;
  assessment_id: string | null;
  reasoning: string | null;
  criterion_results: CriterionResultView[];
  gaps: string[];
  evidence: EvidenceView[];
  considered: ConsideredRecord[];
  attempts: AttemptView[];
}

export interface Indicator { family: string; message: string; evidence_ids: string[]; validated: boolean }

export interface SnapshotSupplier {
  supplier_id: string;
  display_name: string;
  processing_state: string;
  pending_states: string[];
  status: 'qualified' | 'follow_up' | 'excluded';
  reasons: string[];
  claims: SnapshotClaim[];
  indicators: Indicator[];
}

export interface SnapshotContent {
  policy_version: string;
  trigger: string;
  run: { id: string; state: string; mode: string; completed_at: string | null; initial_deadline: string };
  revision: { id: string; sequence: number };
  suppliers: SnapshotSupplier[];
  pending_actions: { id: string; type: string }[];
  coverage: Record<string, unknown>;
  lists: { qualified: string[]; follow_up: string[]; excluded: Record<string, string[]>; counts: Record<string, number> };
}

export interface DecisionView {
  id: string;
  snapshot_id: string;
  supplier_id: string | null;
  decision: 'select' | 'reject' | 'no_selection';
  reason: string | null;
  created_at: string;
}

export interface SnapshotSummary {
  id: string;
  sequence: number;
  run_id: string;
  revision_id: string;
  trigger: string;
  created_at: string;
  content_hash: string;
  partial: boolean;
  counts: { qualified: number; follow_up: number; excluded: number };
}

export interface Snapshot extends SnapshotSummary { content: SnapshotContent; decisions: DecisionView[] }
