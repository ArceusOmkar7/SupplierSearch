import { useEffect, useMemo, useState } from 'react';
import { ApiError } from '../api/client';
import { confirmChecklist, getChecklist, patchChecklist } from '../api/cases';
import type { Checklist, Claim, SupplierEntry } from '../api/types';
import { CLAIM_LABELS } from './labels';

interface Props {
  caseId: string;
  checklist: Checklist;
  suppliers: SupplierEntry[];
  onChange: (checklist: Checklist) => void;
}

export function ClaimChecklist({ caseId, checklist, suppliers, onChange }: Props) {
  const locked = checklist.status !== 'draft';
  const [required, setRequired] = useState<Record<string, boolean>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [conflict, setConflict] = useState(false);

  useEffect(() => {
    setRequired(Object.fromEntries(checklist.claims.map(claim => [claim.id, claim.required_for_shortlist])));
    setConflict(false);
  }, [checklist]);

  const anyRequired = useMemo(() => Object.values(required).some(Boolean), [required]);
  const bySupplier = useMemo(() => suppliers.map(supplier => ({
    supplier,
    parents: checklist.claims.filter(c => c.supplier_id === supplier.supplier_id && !c.parent_claim_id),
  })), [suppliers, checklist.claims]);
  const children = (parent: Claim) => checklist.claims.filter(c => c.parent_claim_id === parent.id);

  async function confirm() {
    setBusy(true);
    setError('');
    try {
      let current = checklist;
      const changed = checklist.claims
        .filter(claim => required[claim.id] !== claim.required_for_shortlist)
        .map(claim => ({ id: claim.id, required_for_shortlist: required[claim.id] }));
      if (changed.length) current = await patchChecklist(caseId, current, { claims: changed });
      onChange(await confirmChecklist(caseId, current));
    } catch (failure) {
      if (failure instanceof ApiError && failure.status === 412) setConflict(true);
      setError(failure instanceof ApiError ? failure.message : 'The checklist could not be confirmed.');
    } finally { setBusy(false); }
  }

  async function reload() {
    setBusy(true);
    try { onChange(await getChecklist(caseId, checklist.id)); setError(''); }
    catch { setError('Could not reload the checklist.'); }
    finally { setBusy(false); }
  }

  function row(claim: Claim, nested: boolean) {
    const id = `claim-${claim.id}`;
    return <li key={claim.id} className={nested ? 'nested' : undefined}>
      <div className="claim">
        <input id={id} type="checkbox" checked={required[claim.id] ?? false} disabled={locked || busy}
          onChange={e => setRequired(current => ({ ...current, [claim.id]: e.target.checked }))} />
        <label htmlFor={id}>
          <span className="tag">{CLAIM_LABELS[claim.type] ?? claim.type}</span> {claim.assertion}
          <span className="visually-hidden"> — required for the shortlist</span>
        </label>
      </div>
      <details>
        <summary>What counts as proof</summary>
        <ul>{claim.proof_criteria.criteria.map(criterion => <li key={criterion.criterion_id}>
          {criterion.assertion}. Accepted sources: {criterion.authority.join(', ') || 'any attributable source'}.
          {criterion.independent_corroboration ? ' Needs independent corroboration.' : ''}
          {' '}If missing: {criterion.missing_evidence_condition}.
        </li>)}</ul>
      </details>
      {children(claim).length > 0 && <ul>{children(claim).map(child => row(child, true))}</ul>}
    </li>;
  }

  return <section className="panel" aria-labelledby="checklist-title" aria-busy={busy}>
    <h2 id="checklist-title">
      Claims to verify <span className="tag">{locked ? 'Confirmed' : 'Draft'}</span>
    </h2>
    {!locked && <p>
      Tick the claims a supplier must prove to be shortlisted. These are proposals: nothing is checked until you confirm.
      At least one claim must be required.
    </p>}
    {bySupplier.map(({ supplier, parents }) => <section key={supplier.supplier_id} aria-label={supplier.display_name}>
      <h3>{supplier.display_name}</h3>
      <ul className="claims">{parents.map(claim => row(claim, false))}</ul>
    </section>)}
    {error && <p role="alert">{error}{conflict && <> <button type="button" className="secondary" onClick={reload}>Reload the latest version</button></>}</p>}
    {!locked && <div className="actions">
      <button type="button" disabled={busy || !anyRequired} aria-describedby="checklist-help" onClick={() => void confirm()}>
        Confirm checklist
      </button>
      <p id="checklist-help" className="muted">
        {anyRequired ? 'Confirming starts no work by itself; you start verification next.' : 'Select at least one required claim to continue.'}
      </p>
    </div>}
  </section>;
}
