import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { clearPrivateState } from '../../api/client';
import type { CaseSummary, DecisionView, Snapshot, SnapshotSummary } from '../../api/types';
import { AssessmentReview } from '../../features/cases/AssessmentReview';
import { EvidenceMatrix } from '../EvidenceMatrix';
import { Shortlist } from '../Shortlist';
import { SupplierDecision } from '../SupplierDecision';
import { capture, FakeEventSource, mockApi } from './captures';

const recorded = capture<Snapshot>('snapshot-detail');
const snapshot = recorded.body;
const detail = capture<CaseSummary>('case-detail');
const caseId = String(detail.body.id);
const escape = (text: string) => text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const buttonFor = (assertion: string) => screen.getByRole('button', { name: new RegExp(escape(assertion)) });

beforeEach(() => { vi.stubGlobal('EventSource', FakeEventSource); FakeEventSource.instances = []; });
afterEach(() => { cleanup(); clearPrivateState(); vi.unstubAllGlobals(); });

describe('evidence matrix (actual recorded snapshot)', () => {
  it('has semantic headers and exactly one permitted verdict per evaluated cell', () => {
    render(<EvidenceMatrix snapshot={snapshot} />);
    expect(screen.getByRole('table')).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'Supplier' })).toBeInTheDocument();
    for (const supplier of snapshot.content.suppliers) {
      expect(screen.getByRole('rowheader', { name: new RegExp(supplier.display_name.slice(0, 12)) })).toBeInTheDocument();
    }
    const buttons = screen.getAllByRole('button', { expanded: false });
    expect(buttons.length).toBeGreaterThan(0);
    for (const button of buttons) {
      expect(button.textContent).toMatch(/Proven|Unproven|Contradicted|Not yet evaluated/);
      const verdicts = (button.textContent ?? '').match(/Proven|Unproven|Contradicted/g) ?? [];
      expect(verdicts.length).toBeLessThanOrEqual(1);
    }
    // Verdict is conveyed by text and a mark, not by colour alone.
    expect(buttons[0].textContent).toMatch(/[✓?✕…]/);
  });

  it('expands a cell with keyboard activation and returns focus when it closes', async () => {
    const user = userEvent.setup();
    render(<EvidenceMatrix snapshot={snapshot} />);
    const claim = snapshot.content.suppliers[0].claims.find(c => !c.parent_claim_id && c.type === 'regulatory')!;
    const trigger = buttonFor(claim.assertion);
    trigger.focus();
    await user.keyboard('{Enter}');
    expect(trigger).toHaveAttribute('aria-expanded', 'true');
    const region = screen.getByRole('region', { name: `Details: ${claim.assertion}` });
    expect(within(region).getByText('Checks that were tried')).toBeInTheDocument();
    expect(within(region).getByText('Evidence used')).toBeInTheDocument();
    // Source gaps and the records that could not be used are shown, with plain reasons.
    expect(region.textContent).toMatch(/not used because|No admissible evidence/i);
    expect(region.textContent).toMatch(/nothing was sent|request sent/);
    await user.keyboard('{Enter}');
    expect(trigger).toHaveAttribute('aria-expanded', 'false');
    await waitFor(() => expect(trigger).toHaveFocus());
  });

  it('shows original source dates and labels a historical export record', async () => {
    const user = userEvent.setup();
    render(<EvidenceMatrix snapshot={snapshot} />);
    const claim = snapshot.content.suppliers[0].claims.find(c => !c.parent_claim_id && c.considered.length > 0)!;
    await user.click(buttonFor(claim.assertion));
    const region = screen.getByRole('region', { name: `Details: ${claim.assertion}` });
    expect(region.textContent).toContain(claim.considered[0].observation.slice(0, 30));
    expect(region.textContent).toMatch(/cutoff 2020-08-27|2020/);
  });

  it('keeps processing state separate from the verdict', () => {
    const waiting: Snapshot = structuredClone(snapshot);
    waiting.content.suppliers[0].processing_state = 'waiting_input';
    render(<EvidenceMatrix snapshot={waiting} />);
    expect(screen.getAllByText('Waiting for you').length).toBeGreaterThan(0);
    expect(screen.getAllByRole('button', { expanded: false })[0].textContent).not.toMatch(/Waiting/);
  });
});

describe('shortlist, explicit empty states and decisions', () => {
  it('shows the empty qualified state and follow-up reasons without padding', () => {
    render(<Shortlist snapshot={snapshot} />);
    const qualified = screen.getByRole('region', { name: 'Qualified' });
    expect(qualified.textContent).toMatch(/No supplier is qualified/);
    const followUp = screen.getByRole('region', { name: 'Follow-up candidates' });
    expect(within(followUp).getAllByText(/Unproven:/).length).toBeGreaterThan(0);
    expect(screen.getByRole('region', { name: /Excluded/ }).textContent).toMatch(/No supplier is excluded/);
  });

  it('requires a reason to select a follow-up supplier and sends the case ETag', async () => {
    const created = capture<{ decision: DecisionView }>('decision-created');
    const calls = mockApi({
      [`POST /cases/${caseId}/decisions`]: () => ({ status: 201, body: created.body, etag: created.etag }),
    });
    const onRecorded = vi.fn();
    const user = userEvent.setup();
    render(<SupplierDecision caseSummary={{ ...detail.body, etag: '"case-etag"' }} snapshot={snapshot} onRecorded={onRecorded} />);
    const chosen = snapshot.content.suppliers[0];
    await user.selectOptions(screen.getByLabelText('Supplier'), chosen.supplier_id);
    expect(screen.getByLabelText(/Reason \(required/)).toBeRequired();
    await user.type(screen.getByLabelText(/Reason/), 'Request the missing certificate');
    await user.click(screen.getByRole('button', { name: 'Record decision' }));
    await waitFor(() => expect(onRecorded).toHaveBeenCalled());
    const post = calls.find(call => call.method === 'POST')!;
    expect(post.headers.get('If-Match')).toBe('"case-etag"');
    expect(post.body).toMatchObject({ snapshot_id: snapshot.id, decision: 'select', supplier_id: chosen.supplier_id });
  });

  it('does not offer a contradicted supplier for selection', () => {
    const excluded: Snapshot = structuredClone(snapshot);
    excluded.content.suppliers[0].status = 'excluded';
    render(<SupplierDecision caseSummary={detail.body} snapshot={excluded} onRecorded={vi.fn()} />);
    const options = within(screen.getByLabelText('Supplier')).getAllByRole('option').map(o => o.textContent);
    expect(options.some(text => text?.includes(excluded.content.suppliers[0].display_name))).toBe(false);
  });
});

describe('assessment review keeps the inspected snapshot stable', () => {
  it('announces a newer snapshot without replacing the one being reviewed', async () => {
    const list = capture<{ items: SnapshotSummary[] }>('snapshots-list');
    const newest: SnapshotSummary = { ...list.body.items[0], id: '00000000-0000-4000-8000-0000000000aa', sequence: 99 };
    let current = list.body.items;
    mockApi({
      [`GET /cases/${caseId}/snapshots`]: () => ({ body: { items: current, next_cursor: null } }),
      [`GET /cases/${caseId}/snapshots/${snapshot.id}`]: () => ({ body: snapshot }),
      [`GET /cases/${caseId}`]: () => ({ body: detail.body, etag: detail.etag }),
    });
    render(<AssessmentReview caseId={caseId} />);
    await screen.findByRole('heading', { name: 'Shortlist' });
    expect(screen.getByLabelText('Snapshot being reviewed')).toHaveValue(snapshot.id);
    current = [newest, ...list.body.items];
    FakeEventSource.instances[0].emit('snapshot.ready', {
      sequence: 500, type: 'snapshot.ready', case_id: caseId, revision_id: null, run_id: null, created_at: '', payload: {},
    });
    expect(await screen.findByText(/A newer snapshot is available/)).toBeInTheDocument();
    expect(screen.getByLabelText('Snapshot being reviewed')).toHaveValue(snapshot.id);
  });
});
