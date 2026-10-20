import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { ApiError, registerPrivateCleanup, requestWithMetadata } from '../api/client';
import {
  createCase, getChecklist, getRevision, listCases, proposeChecklist, startRun,
  type NewSupplier,
} from '../api/cases';
import type { CaseSummary, Checklist, Revision } from '../api/types';
import { ClaimChecklist } from '../components/ClaimChecklist';
import { CollectionProgress } from '../components/CollectionProgress';
import { RequirementReview } from '../components/RequirementReview';
import { AssessmentReview } from '../features/cases/AssessmentReview';

interface CaseDetail extends CaseSummary {
  active_checklist_id?: string | null;
  active_checklist_status?: string | null;
}

function NewCase({ onCreated }: { onCreated: (id: string) => void }) {
  const [title, setTitle] = useState('');
  const [text, setText] = useState('');
  const [names, setNames] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      const suppliers: NewSupplier[] = names.split('\n').map(line => line.trim()).filter(Boolean)
        .map(line => /^https?:\/\/|^www\./i.test(line)
          ? { identifiers: [{ type: 'website', value: line }] }
          : { display_name: line, identifiers: [{ type: 'name', value: line }] });
      const created = await createCase({ title: title.trim() || 'Untitled case', initial_text: text.trim() || undefined, suppliers });
      onCreated(created.case.id);
      setTitle(''); setText(''); setNames('');
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : 'The case could not be created.');
    } finally { setBusy(false); }
  }

  return <form className="panel" onSubmit={submit} aria-labelledby="new-case-title" aria-busy={busy}>
    <h2 id="new-case-title">Start a case</h2>
    <p>Describe what you need and list the suppliers you already know. Nothing is verified until you confirm.</p>
    <div className="field"><label htmlFor="case-title">Case title</label>
      <input id="case-title" value={title} onChange={e => setTitle(e.target.value)} disabled={busy} /></div>
    <div className="field"><label htmlFor="case-text">What do you need?</label>
      <textarea id="case-text" rows={4} value={text} onChange={e => setText(e.target.value)} disabled={busy} /></div>
    <div className="field"><label htmlFor="case-suppliers">Suppliers, one per line (a name or a website)</label>
      <textarea id="case-suppliers" rows={4} value={names} onChange={e => setNames(e.target.value)} disabled={busy} />
      <span className="muted">Marketplace links are kept as text and never opened.</span></div>
    {error && <p role="alert">{error}</p>}
    <button type="submit" disabled={busy}>Create case</button>
  </form>;
}

function Workspace({ caseId, onLeave }: { caseId: string; onLeave: () => void }) {
  const [detail, setDetail] = useState<CaseDetail | null>(null);
  const [revision, setRevision] = useState<Revision | null>(null);
  const [checklist, setChecklist] = useState<Checklist | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const { data, etag } = await requestWithMetadata<CaseDetail>(`/cases/${caseId}`);
      const merged: CaseDetail = { ...data, etag: etag ?? data.etag };
      setDetail(merged);
      const revisionId = merged.draft_revision_id ?? merged.active_revision_id;
      setRevision(revisionId ? await getRevision(caseId, revisionId) : null);
      setChecklist(merged.active_checklist_id ? await getChecklist(caseId, merged.active_checklist_id) : null);
      setError('');
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : 'This case could not be loaded.');
    }
  }, [caseId]);

  useEffect(() => {
    void load();
    return registerPrivateCleanup(() => { setDetail(null); setRevision(null); setChecklist(null); });
  }, [load]);

  async function propose() {
    if (!revision) return;
    setBusy(true);
    try { setChecklist(await proposeChecklist(caseId, revision.id)); setError(''); await load(); }
    catch (failure) { setError(failure instanceof ApiError ? failure.message : 'Claims could not be proposed.'); }
    finally { setBusy(false); }
  }

  async function start() {
    if (!detail || !revision || !checklist) return;
    setBusy(true);
    try { await startRun(detail, revision.id, checklist.id); setError(''); await load(); }
    catch (failure) { setError(failure instanceof ApiError ? failure.message : 'Verification could not start.'); }
    finally { setBusy(false); }
  }

  if (!detail) return <p role="status">{error || 'Opening the case…'}</p>;
  const confirmed = revision?.status === 'confirmed';
  const checklistConfirmed = checklist?.status === 'confirmed';
  return <section aria-labelledby="case-title">
    <p><button type="button" className="secondary" onClick={onLeave}>← All cases</button></p>
    <h2 id="case-title">{detail.title}</h2>
    {error && <p role="alert">{error}</p>}
    {revision && <RequirementReview caseId={caseId} revision={revision} onChange={setRevision} />}
    {confirmed && !checklist && <div className="panel">
      <h2>Claims</h2>
      <p>Next, review which claims to verify for each supplier.</p>
      <button type="button" disabled={busy} onClick={() => void propose()}>Propose claims to verify</button>
    </div>}
    {confirmed && revision && checklist && <ClaimChecklist caseId={caseId} checklist={checklist}
      suppliers={revision.suppliers} onChange={next => { setChecklist(next); void load(); }} />}
    {checklistConfirmed && !detail.latest_run_id && <div className="panel">
      <h2>Start verification</h2>
      <p>Public supplier pages and official records are checked automatically. Blocked or missing sources are reported as gaps; you will not be asked to browse or solve a CAPTCHA.</p>
      <button type="button" disabled={busy} onClick={() => void start()}>Start verification</button>
    </div>}
    {detail.latest_run_id && revision && <CollectionProgress caseId={caseId} runId={detail.latest_run_id}
      revisionId={revision.id} suppliers={revision.suppliers} />}
    {detail.latest_run_id && <AssessmentReview caseId={caseId} />}
  </section>;
}

export function CaseWorkspace() {
  const [cases, setCases] = useState<CaseSummary[] | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [error, setError] = useState('');

  const refresh = useCallback(async () => {
    try { setCases(await listCases()); setError(''); }
    catch (failure) { setError(failure instanceof ApiError ? failure.message : 'Cases could not be loaded.'); }
  }, []);

  useEffect(() => {
    void refresh();
    return registerPrivateCleanup(() => { setCases(null); setSelected(null); });
  }, [refresh]);

  if (selected) return <Workspace caseId={selected} onLeave={() => { setSelected(null); void refresh(); }} />;
  return <div>
    {error && <p role="alert">{error}</p>}
    <section className="panel" aria-labelledby="cases-title">
      <h2 id="cases-title">Your cases</h2>
      {cases === null ? <p role="status">Loading…</p>
        : cases.length === 0 ? <p>You have no cases yet. Start one below.</p>
        : <ul className="cases">{cases.map(c => <li key={c.id}>
          <button type="button" className="link" onClick={() => setSelected(c.id)}>{c.title}</button>
          <span className="tag">{c.state}</span>
        </li>)}</ul>}
    </section>
    <NewCase onCreated={id => { void refresh(); setSelected(id); }} />
  </div>;
}
