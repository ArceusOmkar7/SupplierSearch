import { useId, useRef, useState } from 'react';
import type { Snapshot, SnapshotClaim } from '../api/types';
import { EvidenceDetails, VERDICT_LABELS } from './EvidenceDetails';
import { CLAIM_LABELS } from './labels';

const PROCESSING: Record<string, string> = {
  complete: 'Checks finished',
  queued: 'Waiting to start',
  running: 'Still checking',
  waiting_input: 'Waiting for you',
};

interface Props { snapshot: Snapshot }

/** Supplier rows by claim columns, bound to one immutable snapshot. */
export function EvidenceMatrix({ snapshot }: Props) {
  const { content } = snapshot;
  const columns = [...new Set(content.suppliers.flatMap(s => s.claims.filter(c => !c.parent_claim_id).map(c => c.type)))];
  const [open, setOpen] = useState<string | null>(null);
  const triggers = useRef(new Map<string, HTMLButtonElement>());
  const base = useId();

  function toggle(id: string) {
    const closing = open === id;
    setOpen(closing ? null : id);
    // Focus returns to the control that opened the details when they close.
    if (closing) queueMicrotask(() => triggers.current.get(id)?.focus());
  }

  return <section className="panel" aria-labelledby={`${base}-title`}>
    <h2 id={`${base}-title`}>Evidence by supplier and claim</h2>
    <p className="muted">
      Snapshot {snapshot.sequence}, taken {new Date(snapshot.created_at).toLocaleString()} ({snapshot.trigger}).
      {' '}{content.run.mode === 'replay' ? 'Replay of captured records. ' : ''}
      {snapshot.partial ? 'Some checks were still pending when this was taken. ' : ''}
      Each cell shows exactly one verdict; open it to see the reasoning, sources and dates.
    </p>
    <div className="scroll" tabIndex={0} role="region" aria-label="Evidence matrix, scrolls horizontally">
      <table>
        <caption className="visually-hidden">Verdicts for each supplier and claim in snapshot {snapshot.sequence}</caption>
        <thead><tr>
          <th scope="col">Supplier</th>
          {columns.map(type => <th scope="col" key={type}>{CLAIM_LABELS[type] ?? type}</th>)}
        </tr></thead>
        <tbody>{content.suppliers.map(supplier => <tr key={supplier.supplier_id}>
          <th scope="row">
            {supplier.display_name}
            <span className="muted block">{PROCESSING[supplier.processing_state] ?? supplier.processing_state}</span>
          </th>
          {columns.map(type => {
            const cells = supplier.claims.filter(c => c.type === type && !c.parent_claim_id);
            return <td key={type}>{cells.length === 0 ? <span className="muted">Not requested</span>
              : cells.map(claim => <Cell key={claim.claim_id} claim={claim} subclaims={supplier.claims.filter(c => c.parent_claim_id === claim.claim_id)}
                pending={supplier.processing_state !== 'complete' ? `This supplier is ${(PROCESSING[supplier.processing_state] ?? '').toLowerCase()}; the verdict may change in a later snapshot.` : undefined}
                open={open === claim.claim_id} regionId={`${base}-${claim.claim_id}`}
                onToggle={() => toggle(claim.claim_id)}
                register={node => { if (node) triggers.current.set(claim.claim_id, node); }} />)}</td>;
          })}
        </tr>)}</tbody>
      </table>
    </div>
  </section>;
}

function Cell({ claim, subclaims, pending, open, regionId, onToggle, register }: {
  claim: SnapshotClaim; subclaims: SnapshotClaim[]; pending?: string; open: boolean; regionId: string;
  onToggle: () => void; register: (node: HTMLButtonElement | null) => void;
}) {
  const verdict = claim.verdict ? VERDICT_LABELS[claim.verdict] : null;
  return <div className="cell">
    <button type="button" className="cell-button" aria-expanded={open} aria-controls={regionId} ref={register} onClick={onToggle}>
      <span aria-hidden="true">{verdict ? verdict.mark : '…'} </span>
      {verdict ? verdict.text : 'Not yet evaluated'}
      <span className="visually-hidden">: {claim.assertion}</span>
      {claim.required && <span className="tag">Required</span>}
    </button>
    <div id={regionId} role="region" aria-label={`Details: ${claim.assertion}`} hidden={!open}>
      {open && <EvidenceDetails claim={claim} subclaims={subclaims} pending={pending} />}
    </div>
  </div>;
}
