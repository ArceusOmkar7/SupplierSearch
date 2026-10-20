import { ApiError, request, requestWithMetadata } from './client';
import type {
  BuyerAction, CaseSummary, Checklist, Page, Revision, Run, RunTask, SourceCapability,
} from './types';

const key = () => crypto.randomUUID();

export interface NewSupplier {
  display_name?: string;
  supplier_id?: string;
  identifiers: { type: string; value: string }[];
  address?: string | null;
  address_role?: string;
}

export async function listCases(): Promise<CaseSummary[]> {
  return (await request<Page<CaseSummary>>('/cases')).items;
}

export async function createCase(input: {
  title: string; initial_text?: string; suppliers: NewSupplier[];
}): Promise<{ case: CaseSummary; revision: Revision }> {
  return request('/cases', { method: 'POST', body: input, idempotencyKey: key() });
}

export async function getCase(id: string): Promise<CaseSummary> {
  const { data, etag } = await requestWithMetadata<CaseSummary>(`/cases/${id}`);
  return { ...data, etag: etag ?? data.etag };
}

export async function getRevision(caseId: string, id: string): Promise<Revision> {
  const { data, etag } = await requestWithMetadata<Revision>(`/cases/${caseId}/revisions/${id}`);
  return { ...data, etag: etag ?? data.etag };
}

export interface RevisionChanges {
  requirements?: Partial<Revision['requirements']>;
  location?: Partial<Revision['location']>;
  suppliers?: NewSupplier[];
}

export async function patchRevision(
  caseId: string, revision: Revision, changes: RevisionChanges,
): Promise<Revision> {
  return request(`/cases/${caseId}/revisions/${revision.id}`, {
    method: 'PATCH', body: changes, etag: revision.etag, idempotencyKey: key(),
  });
}

export async function confirmRevision(caseId: string, revision: Revision): Promise<Revision> {
  return request(`/cases/${caseId}/revisions/${revision.id}/confirm`, {
    method: 'POST', body: {}, etag: revision.etag, idempotencyKey: key(),
  });
}

export async function proposeChecklist(caseId: string, revisionId: string): Promise<Checklist> {
  const result = await request<{ checklist: Checklist }>(
    `/cases/${caseId}/revisions/${revisionId}/claims`,
    { method: 'POST', body: {}, idempotencyKey: key() },
  );
  return result.checklist;
}

export async function getChecklist(caseId: string, id: string): Promise<Checklist> {
  const { data, etag } = await requestWithMetadata<Checklist>(`/cases/${caseId}/checklists/${id}`);
  return { ...data, etag: etag ?? data.etag };
}

export interface ChecklistChanges {
  claims?: { id: string; required_for_shortlist?: boolean; assertion?: string }[];
  remove?: string[];
}

export async function patchChecklist(
  caseId: string, checklist: Checklist, changes: ChecklistChanges,
): Promise<Checklist> {
  return request(`/cases/${caseId}/checklists/${checklist.id}`, {
    method: 'PATCH', body: changes, etag: checklist.etag, idempotencyKey: key(),
  });
}

export async function confirmChecklist(caseId: string, checklist: Checklist): Promise<Checklist> {
  return request(`/cases/${caseId}/checklists/${checklist.id}/confirm`, {
    method: 'POST', body: {}, etag: checklist.etag, idempotencyKey: key(),
  });
}

export async function startRun(
  caseSummary: CaseSummary, revisionId: string, checklistId: string, mode: 'live' | 'replay' = 'live',
): Promise<{ run: Run; source_capabilities: SourceCapability[] }> {
  return request(`/cases/${caseSummary.id}/runs`, {
    method: 'POST', body: { revision_id: revisionId, checklist_id: checklistId, mode },
    etag: caseSummary.etag, idempotencyKey: key(),
  });
}

export async function getRun(caseId: string, runId: string): Promise<{ run: Run; tasks: RunTask[] }> {
  return request(`/cases/${caseId}/runs/${runId}`);
}

export async function listActions(caseId: string, state?: string): Promise<BuyerAction[]> {
  const query = state ? `?state=${state}` : '';
  return (await request<Page<BuyerAction>>(`/cases/${caseId}/actions${query}`)).items;
}

export async function resolveAction(
  caseId: string, action: BuyerAction,
  body: { decision?: 'confirm' | 'reject'; replacement_document_id?: string },
): Promise<BuyerAction> {
  return request(`/cases/${caseId}/actions/${action.id}/resolve`, {
    method: 'POST', body, etag: action.etag, idempotencyKey: key(),
  });
}

export async function uploadDocument(
  caseId: string, supplierId: string, revisionId: string, file: File,
): Promise<{ document: { id: string; state: string } }> {
  const session = await request<{ csrf_token: string }>('/session');
  const form = new FormData();
  form.set('file', file);
  form.set('supplier_id', supplierId);
  form.set('revision_id', revisionId);
  const response = await fetch(`/api/v1/cases/${caseId}/documents`, {
    method: 'POST', body: form, credentials: 'same-origin', cache: 'no-store',
    headers: { 'X-CSRF-Token': session.csrf_token },
  });
  if (!response.ok) {
    const reasons: Record<number, string> = {
      413: 'The PDF is over 20 MiB or 50 pages.',
      415: 'Only PDF documents are supported.',
      404: 'This resource is unavailable.',
    };
    throw new ApiError(response.status, reasons[response.status] ?? 'The upload could not be completed.');
  }
  return response.json();
}

export async function listSnapshots(caseId: string): Promise<import('./types').SnapshotSummary[]> {
  return (await request<Page<import('./types').SnapshotSummary>>(`/cases/${caseId}/snapshots`)).items;
}

export async function getSnapshot(caseId: string, id: string): Promise<import('./types').Snapshot> {
  return request(`/cases/${caseId}/snapshots/${id}`);
}

export async function recordDecision(
  caseSummary: CaseSummary,
  body: { snapshot_id: string; decision: 'select' | 'reject' | 'no_selection'; supplier_id?: string; reason?: string },
): Promise<{ decision: import('./types').DecisionView }> {
  return request(`/cases/${caseSummary.id}/decisions`, {
    method: 'POST', body, etag: caseSummary.etag, idempotencyKey: key(),
  });
}
