import type { Snapshot, SnapshotSupplier } from '../api/types';

function Group({ title, empty, suppliers, why }: {
  title: string; empty: string; suppliers: SnapshotSupplier[]; why: 'none' | 'gaps' | 'excluded';
}) {
  return <section aria-label={title}>
    <h3>{title} <span className="tag">{suppliers.length}</span></h3>
    {suppliers.length === 0 ? <p className="muted">{empty}</p> : <ul>{suppliers.map(supplier => <li key={supplier.supplier_id}>
      <strong>{supplier.display_name}</strong>
      {supplier.processing_state !== 'complete' && <span className="tag">Checks not finished</span>}
      {why !== 'none' && <ul>{supplier.reasons.map(reason => <li key={reason}>{reason}</li>)}</ul>}
      {supplier.indicators.length > 0 && <ul aria-label={`Review prompts for ${supplier.display_name}`}>{supplier.indicators.map(indicator => <li key={indicator.family}>
        <span className="tag">Review prompt</span> {indicator.message}
      </li>)}</ul>}
    </li>)}</ul>}
  </section>;
}

/** Qualified, follow-up and excluded suppliers derived from the snapshot; never padded. */
export function Shortlist({ snapshot }: { snapshot: Snapshot }) {
  const by = (status: SnapshotSupplier['status']) => snapshot.content.suppliers.filter(s => s.status === status);
  return <section className="panel" aria-labelledby="shortlist-title">
    <h2 id="shortlist-title">Shortlist</h2>
    <p className="muted">
      A supplier is qualified only when every claim you marked required is proven. Review prompts are
      pointers for your own judgement; they never prove or disprove anything.
    </p>
    <Group title="Qualified" suppliers={by('qualified')} why="none"
      empty="No supplier is qualified. The required claims are not all proven for any supplier yet; the list is not filled to look complete." />
    <Group title="Follow-up candidates" suppliers={by('follow_up')} why="gaps"
      empty="No supplier needs follow-up." />
    <Group title="Excluded (a required claim is contradicted)" suppliers={by('excluded')} why="excluded"
      empty="No supplier is excluded." />
  </section>;
}
