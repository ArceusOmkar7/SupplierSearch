import { useCallback, useEffect, useState } from 'react';
import { ApiError } from '../../api/client';
import { getCase, getSnapshot, listSnapshots } from '../../api/cases';
import { openCaseEvents } from '../../api/events';
import type { CaseSummary, DecisionView, Snapshot, SnapshotSummary } from '../../api/types';
import { EvidenceMatrix } from '../../components/EvidenceMatrix';
import { Shortlist } from '../../components/Shortlist';
import { SupplierDecision } from '../../components/SupplierDecision';

/**
 * Reviews one immutable snapshot at a time. A newer snapshot arriving in the background is only
 * announced; the snapshot being inspected (and decided against) never changes underneath the buyer.
 */
export function AssessmentReview({ caseId }: { caseId: string }) {
  const [summaries, setSummaries] = useState<SnapshotSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [caseSummary, setCaseSummary] = useState<CaseSummary | null>(null);
  const [newer, setNewer] = useState(false);
  const [error, setError] = useState('');

  const refreshList = useCallback(async () => {
    try {
      const items = await listSnapshots(caseId);
      setSummaries(items);
      setCaseSummary(await getCase(caseId));
      setSelectedId(current => current ?? items[0]?.id ?? null);
      setNewer(shown => shown || false);
      return items;
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : 'Assessments could not be loaded.');
      return [];
    }
  }, [caseId]);

  useEffect(() => {
    void refreshList();
    return openCaseEvents(caseId, {
      onEvent: event => { if (event.type === 'snapshot.ready') void refreshList().then(items => {
        setSelectedId(current => { if (current && items[0] && items[0].id !== current) setNewer(true); return current; });
      }); },
      onReset: () => void refreshList(),
      onStatus: () => undefined,
    });
  }, [caseId, refreshList]);

  useEffect(() => {
    if (!selectedId) return;
    let live = true;
    getSnapshot(caseId, selectedId).then(next => { if (live) setSnapshot(next); })
      .catch(failure => { if (live) setError(failure instanceof ApiError ? failure.message : 'This snapshot could not be loaded.'); });
    return () => { live = false; };
  }, [caseId, selectedId]);

  function recorded(decision: DecisionView) {
    setSnapshot(current => current ? { ...current, decisions: [...current.decisions, decision] } : current);
    void getCase(caseId).then(setCaseSummary);
  }

  if (error) return <p role="alert">{error}</p>;
  if (summaries.length === 0) return <section className="panel" aria-labelledby="review-title">
    <h2 id="review-title">Assessment</h2>
    <p>No assessment has been published yet. Results appear here as each supplier’s checks finish.</p>
  </section>;
  return <div>
    <section className="panel" aria-labelledby="review-title">
      <h2 id="review-title">Assessment</h2>
      <div className="field">
        <label htmlFor="snapshot-select">Snapshot being reviewed</label>
        <select id="snapshot-select" value={selectedId ?? ''} onChange={e => { setSelectedId(e.target.value); setNewer(false); setSnapshot(null); }}>
          {summaries.map(item => <option key={item.id} value={item.id}>
            Snapshot {item.sequence} — {new Date(item.created_at).toLocaleString()} ({item.trigger}{item.partial ? ', partial' : ''})
          </option>)}
        </select>
      </div>
      {newer && <p role="status" className="notice">
        A newer snapshot is available. You are still viewing the one you selected.{' '}
        <button type="button" className="secondary" onClick={() => { setSelectedId(summaries[0].id); setSnapshot(null); setNewer(false); }}>
          View the newest snapshot
        </button>
      </p>}
    </section>
    {snapshot && caseSummary && <>
      <Shortlist snapshot={snapshot} />
      <EvidenceMatrix snapshot={snapshot} />
      <SupplierDecision caseSummary={caseSummary} snapshot={snapshot} onRecorded={recorded} />
    </>}
  </div>;
}
