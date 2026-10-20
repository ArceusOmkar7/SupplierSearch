import { useState, type FormEvent } from 'react';
import { ApiError } from '../api/client';
import { recordDecision } from '../api/cases';
import type { CaseSummary, DecisionView, Snapshot } from '../api/types';

interface Props {
  caseSummary: CaseSummary;
  snapshot: Snapshot;
  onRecorded: (decision: DecisionView) => void;
}

/** An explicit choice attached to the displayed snapshot; it never changes any verdict. */
export function SupplierDecision({ caseSummary, snapshot, onRecorded }: Props) {
  const [supplier, setSupplier] = useState('');
  const [decision, setDecision] = useState<'select' | 'reject' | 'no_selection'>('select');
  const [reason, setReason] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const chosen = snapshot.content.suppliers.find(s => s.supplier_id === supplier);
  const needsReason = decision === 'select' && chosen?.status === 'follow_up';
  const names = new Map(snapshot.content.suppliers.map(s => [s.supplier_id, s.display_name]));

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      const result = await recordDecision(caseSummary, {
        snapshot_id: snapshot.id, decision,
        supplier_id: decision === 'no_selection' ? undefined : supplier,
        reason: reason.trim() || undefined,
      });
      onRecorded(result.decision);
      setReason('');
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : 'The decision could not be saved.');
    } finally { setBusy(false); }
  }

  return <form className="panel" onSubmit={submit} aria-labelledby="decision-title" aria-busy={busy}>
    <h2 id="decision-title">Your decision</h2>
    <p className="muted">
      Recorded against snapshot {snapshot.sequence}. Choosing a supplier does not contact them or alter any evidence.
    </p>
    {snapshot.decisions.length > 0 && <ul aria-label="Decisions already recorded">{snapshot.decisions.map(d => <li key={d.id}>
      {d.decision === 'no_selection' ? 'No supplier selected' : `${d.decision === 'select' ? 'Selected' : 'Rejected'} ${names.get(d.supplier_id ?? '') ?? 'a supplier'}`}
      {d.reason ? ` — ${d.reason}` : ''} <span className="muted">({new Date(d.created_at).toLocaleString()})</span>
    </li>)}</ul>}
    <fieldset disabled={busy}>
      <legend>What do you want to do?</legend>
      <label><input type="radio" name="decision" checked={decision === 'select'} onChange={() => setDecision('select')} /> Select a supplier</label>
      <label><input type="radio" name="decision" checked={decision === 'reject'} onChange={() => setDecision('reject')} /> Reject a supplier</label>
      <label><input type="radio" name="decision" checked={decision === 'no_selection'} onChange={() => setDecision('no_selection')} /> Select none of them</label>
    </fieldset>
    {decision !== 'no_selection' && <div className="field">
      <label htmlFor="decision-supplier">Supplier</label>
      <select id="decision-supplier" value={supplier} onChange={e => setSupplier(e.target.value)} disabled={busy} required>
        <option value="">Choose a supplier…</option>
        {snapshot.content.suppliers.filter(s => decision === 'reject' || s.status !== 'excluded').map(s =>
          <option key={s.supplier_id} value={s.supplier_id}>
            {s.display_name} ({s.status === 'qualified' ? 'qualified' : s.status === 'follow_up' ? 'follow-up' : 'excluded'})
          </option>)}
      </select>
    </div>}
    <div className="field">
      <label htmlFor="decision-reason">Reason{needsReason ? ' (required: this supplier still has unproven required claims)' : ' (optional)'}</label>
      <textarea id="decision-reason" rows={2} value={reason} onChange={e => setReason(e.target.value)} disabled={busy} required={needsReason} />
    </div>
    {error && <p role="alert">{error}</p>}
    <button type="submit" disabled={busy || (decision !== 'no_selection' && !supplier)}>Record decision</button>
  </form>;
}
