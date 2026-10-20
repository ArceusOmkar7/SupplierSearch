import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { getRun, listActions } from '../api/cases';
import { openCaseEvents, type StreamStatus } from '../api/events';
import { request } from '../api/client';
import type { BuyerAction, Run, RunTask, SupplierEntry } from '../api/types';
import { HumanAction } from './HumanAction';
import { CHECK_LABELS, OUTCOME_LABELS, REASON_LABELS, TASK_STATE_LABELS } from './labels';

interface Attempt {
  id: string; task_id: string; supplier_id: string; kind: string; target: string; outcome: string;
  reason_code: string | null; request_dispatched: boolean; http_status: number | null; retry_of: string | null;
}

interface Props {
  caseId: string;
  runId: string;
  revisionId: string;
  suppliers: SupplierEntry[];
  mode?: string;
}

export function CollectionProgress({ caseId, runId, revisionId, suppliers, mode }: Props) {
  const [run, setRun] = useState<Run | null>(null);
  const [tasks, setTasks] = useState<RunTask[]>([]);
  const [attempts, setAttempts] = useState<Attempt[]>([]);
  const [actions, setActions] = useState<BuyerAction[]>([]);
  const [status, setStatus] = useState<StreamStatus>('connecting');
  const [error, setError] = useState('');
  const [announce, setAnnounce] = useState('');
  const lastState = useRef('');

  const refresh = useCallback(async () => {
    try {
      const [detail, attemptList, pending] = await Promise.all([
        getRun(caseId, runId),
        request<{ items: Attempt[] }>(`/cases/${caseId}/runs/${runId}/attempts`),
        listActions(caseId, 'pending'),
      ]);
      setRun(detail.run);
      setTasks(detail.tasks);
      setAttempts(attemptList.items);
      setActions(pending);
      setError('');
      const summary = `${detail.run.state.replace('_', ' ')}`;
      if (summary !== lastState.current) { lastState.current = summary; setAnnounce(`Verification ${summary}.`); }
    } catch { setError('Progress could not be refreshed. It will retry when the connection returns.'); }
  }, [caseId, runId]);

  useEffect(() => {
    void refresh();
    const stop = openCaseEvents(caseId, {
      onEvent: () => void refresh(),
      onReset: () => void refresh(),
      onStatus: setStatus,
    });
    // A safety refresh in case an event is missed while reconnecting.
    const timer = window.setInterval(() => void refresh(), 15000);
    return () => { stop(); window.clearInterval(timer); };
  }, [caseId, refresh]);

  const names = useMemo(() => new Map(suppliers.map(s => [s.supplier_id, s.display_name])), [suppliers]);
  const finished = run && ['completed', 'completed_with_gaps', 'cancelled', 'failed'].includes(run.state);

  return <section className="panel" aria-labelledby="progress-title">
    <h2 id="progress-title">Verification progress</h2>
    <p role="status" className="visually-hidden">{announce}</p>
    {run && <p>
      {finished
        ? run.state === 'completed' ? 'All checks finished.' : run.state === 'cancelled' ? 'This run was cancelled.'
          : 'Checks finished. Some sources gave no evidence — see the details below.'
        : 'Checks run on their own. You do not need to visit any website or solve any CAPTCHA.'}
      {' '}{mode === 'replay' || run.mode === 'replay' ? 'Replay of previously captured records. ' : 'Live retrieval. '}
      <span className="muted">Updates: {status === 'open' ? 'live' : status === 'reconnecting' ? 'reconnecting — showing the last known state' : status}.</span>
    </p>}
    {error && <p role="alert">{error}</p>}
    {actions.length > 0 && <HumanAction caseId={caseId} revisionId={revisionId} actions={actions} tasks={tasks}
      suppliers={suppliers} onResolved={() => void refresh()} />}
    {suppliers.map(supplier => {
      const own = tasks.filter(t => t.supplier_id === supplier.supplier_id);
      return <section key={supplier.supplier_id} aria-label={`${supplier.display_name} checks`}>
        <h3>{supplier.display_name}</h3>
        <table>
          <caption className="visually-hidden">Checks for {supplier.display_name}</caption>
          <thead><tr><th scope="col">Check</th><th scope="col">Status</th><th scope="col">What happened</th></tr></thead>
          <tbody>{own.map(task => {
            const label = TASK_STATE_LABELS[task.state] ?? { text: task.state, mark: '?' };
            const own = attempts.filter(a => a.task_id === task.id);
            return <tr key={task.id}>
              <th scope="row">{CHECK_LABELS[task.check_type] ?? task.check_type}</th>
              <td><span aria-hidden="true">{label.mark} </span>{label.text}</td>
              <td>{own.length === 0 ? <span className="muted">Not started</span> : <ul>{own.map(a => <li key={a.id}>
                {OUTCOME_LABELS[a.outcome] ?? a.outcome}
                {a.reason_code ? ` — ${REASON_LABELS[a.reason_code] ?? a.reason_code}` : ''}
                {a.request_dispatched ? '' : ' (nothing was sent)'}
                {a.retry_of ? ' (retry)' : ''}
              </li>)}</ul>}</td>
            </tr>;
          })}</tbody>
        </table>
      </section>;
    })}
    {run && names.size === 0 && <p className="muted">No suppliers in this run.</p>}
  </section>;
}
