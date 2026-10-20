import { useState } from 'react';
import { ApiError } from '../api/client';
import { resolveAction, uploadDocument } from '../api/cases';
import type { BuyerAction, RunTask, SupplierEntry } from '../api/types';

interface Props {
  caseId: string;
  revisionId: string;
  actions: BuyerAction[];
  tasks: RunTask[];
  suppliers: SupplierEntry[];
  onResolved: () => void;
}

/** Only the two permitted dependent actions; never a portal, CAPTCHA or scraping instruction. */
export function HumanAction({ caseId, revisionId, actions, tasks, suppliers, onResolved }: Props) {
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState('');

  async function decide(action: BuyerAction, decision: 'confirm' | 'reject') {
    setBusy(action.id);
    setError('');
    try { await resolveAction(caseId, action, { decision }); onResolved(); }
    catch (failure) { setError(failure instanceof ApiError ? failure.message : 'The decision could not be saved.'); }
    finally { setBusy(null); }
  }

  async function replace(action: BuyerAction, supplierId: string, file: File | undefined) {
    if (!file) return;
    setBusy(action.id);
    setError('');
    try {
      const uploaded = await uploadDocument(caseId, supplierId, revisionId, file);
      await resolveAction(caseId, action, { replacement_document_id: uploaded.document.id });
      onResolved();
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : 'The replacement could not be used.');
    } finally { setBusy(null); }
  }

  return <section aria-labelledby="actions-title" className="notice">
    <h3 id="actions-title">Needs your attention</h3>
    <p className="muted">Only the checks listed here are waiting. Everything else keeps running.</p>
    {error && <p role="alert">{error}</p>}
    <ul>{actions.map(action => {
      const affected = tasks.filter(t => action.affected_task_ids.includes(t.id));
      const supplier = suppliers.find(s => s.supplier_id === affected[0]?.supplier_id);
      return <li key={action.id}>
        {action.type === 'resolve_identity' ? <>
          <p>Please confirm whether the records found belong to <strong>{supplier?.display_name ?? 'this supplier'}</strong>.
            {' '}{affected.length} check{affected.length === 1 ? ' is' : 's are'} waiting for this.</p>
          <div className="actions">
            <button type="button" disabled={busy === action.id} onClick={() => void decide(action, 'confirm')}>
              Yes, this is the same supplier
            </button>
            <button type="button" className="secondary" disabled={busy === action.id} onClick={() => void decide(action, 'reject')}>
              No, ignore these records
            </button>
          </div>
        </> : <>
          <p>A certificate you uploaded for <strong>{supplier?.display_name ?? 'this supplier'}</strong> is locked or unreadable.
            Upload an unlocked copy.</p>
          <label htmlFor={`replace-${action.id}`}>Replacement PDF (up to 20 MiB, 50 pages)</label>
          <input id={`replace-${action.id}`} type="file" accept="application/pdf" disabled={busy === action.id}
            onChange={e => void replace(action, supplier?.supplier_id ?? '', e.target.files?.[0])} />
        </>}
      </li>;
    })}</ul>
  </section>;
}
