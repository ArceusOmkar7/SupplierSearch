import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { clearPrivateState } from '../../api/client';
import type { BuyerAction, Checklist, Revision, Run, RunTask } from '../../api/types';
import { ClaimChecklist } from '../ClaimChecklist';
import { CollectionProgress } from '../CollectionProgress';
import { RequirementReview } from '../RequirementReview';
import { capture, FakeEventSource, mockApi } from './captures';

const created = capture<{ case: { id: string }; revision: Revision }>('case-created');
const caseId = created.body.case.id;

beforeEach(() => { vi.stubGlobal('EventSource', FakeEventSource); FakeEventSource.instances = []; });
afterEach(() => { cleanup(); clearPrivateState(); vi.unstubAllGlobals(); });

describe('requirement review (actual recorded draft)', () => {
  it('keeps unconfirmed input editable, names what is missing and sends the ETag', async () => {
    const draft = created.body.revision;
    const edited = capture<Revision>('revision-edited');
    const onChange = vi.fn();
    const calls = mockApi({
      [`PATCH /cases/${caseId}/revisions/${draft.id}`]: () => ({ body: edited.body, etag: edited.etag }),
    });
    const user = userEvent.setup();
    render(<RequirementReview caseId={caseId} revision={draft} onChange={onChange} />);

    // Interpretation text alone does not fill or confirm anything.
    expect(screen.getByLabelText(/Part or equipment/)).toHaveValue('');
    expect(screen.getByText(/Not provided:/)).toHaveTextContent('Part or equipment');
    expect(screen.getByRole('button', { name: 'Confirm requirements' })).toBeDisabled();
    expect(screen.getByLabelText('Supplier 1 name')).toHaveValue(draft.suppliers[0].display_name);

    await user.type(screen.getByLabelText(/Part or equipment/), 'Universal Testing Machine');
    expect(screen.getByRole('button', { name: 'Confirm requirements' })).toBeEnabled();
    await user.click(screen.getByRole('button', { name: 'Save draft' }));

    await waitFor(() => expect(onChange).toHaveBeenCalled());
    const patch = calls.find(call => call.method === 'PATCH')!;
    expect(patch.headers.get('If-Match')).toBe(draft.etag);
    expect(patch.headers.get('Idempotency-Key')).toBeTruthy();
    expect(patch.headers.get('X-CSRF-Token')).toBe('csrf');
    expect((patch.body as { requirements: { part_description: string } }).requirements.part_description)
      .toBe('Universal Testing Machine');
  });

  it('offers a reload when another tab changed the revision (412)', async () => {
    const draft = created.body.revision;
    mockApi({
      [`PATCH /cases/${caseId}/revisions/${draft.id}`]: () => ({ status: 412, body: { error: { code: 'stale_version' } } }),
      [`GET /cases/${caseId}/revisions/${draft.id}`]: () => ({ body: draft, etag: draft.etag }),
    });
    const user = userEvent.setup();
    render(<RequirementReview caseId={caseId} revision={draft} onChange={vi.fn()} />);
    await user.type(screen.getByLabelText(/Part or equipment/), 'x');
    await user.click(screen.getByRole('button', { name: 'Save draft' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('This item changed');
    expect(screen.getByRole('button', { name: 'Reload the latest version' })).toBeInTheDocument();
  });

  it('shows a confirmed revision read-only', () => {
    const confirmed = capture<Revision>('revision-confirmed').body;
    render(<RequirementReview caseId={caseId} revision={confirmed} onChange={vi.fn()} />);
    expect(screen.getByLabelText(/Part or equipment/)).toBeDisabled();
    expect(screen.queryByRole('button', { name: 'Confirm requirements' })).not.toBeInTheDocument();
  });
});

describe('claim checklist (actual recorded proposal)', () => {
  const checklist = capture<Checklist>('checklist-proposed');
  const confirmed = capture<Checklist>('checklist-confirmed');
  const revision = capture<Revision>('revision-confirmed').body;

  it('requires an explicit required claim before confirmation and sends the diff', async () => {
    const onChange = vi.fn();
    const calls = mockApi({
      [`PATCH /cases/${caseId}/checklists/${checklist.body.id}`]: () => ({ body: { ...checklist.body, etag: '"next"' }, etag: '"next"' }),
      [`POST /cases/${caseId}/checklists/${checklist.body.id}/confirm`]: () => ({ body: confirmed.body, etag: confirmed.etag }),
    });
    const user = userEvent.setup();
    render(<ClaimChecklist caseId={caseId} checklist={checklist.body} suppliers={revision.suppliers} onChange={onChange} />);

    const button = screen.getByRole('button', { name: 'Confirm checklist' });
    expect(button).toBeDisabled();
    expect(screen.getByText('Select at least one required claim to continue.')).toBeInTheDocument();

    const first = revision.suppliers[0].display_name;
    const group = screen.getByRole('region', { name: first });
    const legal = within(group).getByRole('checkbox', { name: /Legal existence/ });
    await user.click(legal);
    expect(button).toBeEnabled();
    await user.click(button);

    await waitFor(() => expect(onChange).toHaveBeenCalledWith(confirmed.body));
    const patch = calls.find(call => call.method === 'PATCH')!;
    expect(patch.headers.get('If-Match')).toBe(checklist.body.etag);
    expect((patch.body as { claims: unknown[] }).claims).toHaveLength(1);
  });

  it('lists proof criteria and nests subclaims under the certificate claim', () => {
    mockApi({});
    render(<ClaimChecklist caseId={caseId} checklist={checklist.body} suppliers={revision.suppliers} onChange={vi.fn()} />);
    expect(screen.getAllByText('What counts as proof').length).toBeGreaterThan(5);
    expect(screen.getAllByText(/certificate status is valid/).length).toBeGreaterThan(0);
  });
});

describe('collection progress (actual recorded run)', () => {
  const finished = capture<{ run: Run; tasks: RunTask[] }>('run-finished');
  const attempts = capture<{ items: unknown[] }>('run-attempts');
  const revision = capture<Revision>('revision-confirmed').body;
  const runId = finished.body.run.id;

  function routes(actions: unknown = capture('actions-empty').body) {
    return mockApi({
      [`GET /cases/${caseId}/runs/${runId}`]: () => ({ body: finished.body }),
      [`GET /cases/${caseId}/runs/${runId}/attempts`]: () => ({ body: attempts.body }),
      [`GET /cases/${caseId}/actions?state=pending`]: () => ({ body: actions }),
    });
  }

  it('shows every check with text status, what was sent and no portal or CAPTCHA task', async () => {
    routes();
    render(<CollectionProgress caseId={caseId} runId={runId} revisionId={revision.id} suppliers={revision.suppliers} />);
    expect(await screen.findByText(/Checks finished/)).toBeInTheDocument();
    expect(screen.getAllByRole('table')).toHaveLength(revision.suppliers.length);
    expect(screen.getAllByText(/nothing was sent/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/no identifier to look up/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Live retrieval/).length).toBe(1);
    const text = document.body.textContent ?? '';
    expect(text).not.toMatch(/solve|log in to the portal|visit the website/i);
    expect(screen.getAllByRole('columnheader', { name: 'Status' }).length).toBe(revision.suppliers.length);
  });

  it('refreshes when a live event arrives and marks reconnecting without losing the last state', async () => {
    const calls = routes();
    render(<CollectionProgress caseId={caseId} runId={runId} revisionId={revision.id} suppliers={revision.suppliers} />);
    await screen.findByText(/Checks finished/);
    const before = calls.length;
    const source = FakeEventSource.instances[0];
    source.emit('check.completed', { sequence: 99, type: 'check.completed', case_id: caseId, revision_id: null, run_id: runId, created_at: '', payload: {} });
    await waitFor(() => expect(calls.length).toBeGreaterThan(before));
    source.onerror?.();
    expect(await screen.findByText(/reconnecting — showing the last known state/)).toBeInTheDocument();
    expect(screen.getAllByRole('table').length).toBe(revision.suppliers.length);
  });

  it('closes the event stream on logout', async () => {
    routes();
    render(<CollectionProgress caseId={caseId} runId={runId} revisionId={revision.id} suppliers={revision.suppliers} />);
    await screen.findByText(/Checks finished/);
    clearPrivateState();
    expect(FakeEventSource.instances[0].closed).toBe(true);
  });

  it('asks only for the identity decision that is waiting and resolves it with the ETag', async () => {
    const pending = capture<{ items: BuyerAction[] }>('action-pending');
    const action = pending.body.items[0];
    const calls = routes(pending.body);
    mockApi({
      [`GET /cases/${caseId}/runs/${runId}`]: () => ({ body: finished.body }),
      [`GET /cases/${caseId}/runs/${runId}/attempts`]: () => ({ body: attempts.body }),
      [`GET /cases/${caseId}/actions?state=pending`]: () => ({ body: pending.body }),
      [`POST /cases/${caseId}/actions/${action.id}/resolve`]: () => ({ status: 202, body: { ...action, state: 'resolved' } }),
    });
    void calls;
    const user = userEvent.setup();
    render(<CollectionProgress caseId={caseId} runId={runId} revisionId={revision.id} suppliers={revision.suppliers} />);
    expect(await screen.findByText('Needs your attention')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /Yes, this is the same supplier/ }));
    const fetchMock = vi.mocked(fetch);
    await waitFor(() => {
      const post = fetchMock.mock.calls.find(([url, init]) => String(url).endsWith('/resolve') && (init as RequestInit).method === 'POST');
      expect(post).toBeTruthy();
      expect(new Headers((post![1] as RequestInit).headers).get('If-Match')).toBe(action.etag);
    });
  });
});
