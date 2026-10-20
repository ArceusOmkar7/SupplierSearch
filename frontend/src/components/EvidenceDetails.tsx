import type { SnapshotClaim } from '../api/types';
import { OUTCOME_LABELS, REASON_LABELS } from './labels';

export const VERDICT_LABELS: Record<string, { text: string; mark: string }> = {
  proven: { text: 'Proven', mark: '✓' },
  unproven: { text: 'Unproven', mark: '?' },
  contradicted: { text: 'Contradicted', mark: '✕' },
};

const AUTHORITY: Record<string, string> = {
  official_registry: 'official registry',
  official_publication: 'official publication',
  issuer: 'certificate issuer',
  accreditation_body: 'accreditation body',
  supplier: 'the supplier',
  third_party: 'third party',
  buyer: 'you',
};

const day = (value: string | null) => (value ? new Date(value).toLocaleDateString() : 'not stated');

interface Props {
  claim: SnapshotClaim;
  subclaims: SnapshotClaim[];
  /** Why the whole snapshot may be incomplete (pending checks), shown beside the verdict. */
  pending?: string;
}

/** Expanded view of one evaluated cell: reasoning, criteria, originals, dates and attempts. */
export function EvidenceDetails({ claim, subclaims, pending }: Props) {
  return <div className="details-body">
    <p><strong>{claim.assertion}</strong>{claim.required ? <span className="tag">Required for the shortlist</span> : null}</p>
    {claim.reasoning && <p>{claim.reasoning}</p>}
    {pending && <p className="muted">{pending}</p>}

    {claim.criterion_results.length > 0 && <>
      <h4>Criteria</h4>
      <ul>{claim.criterion_results.map(result => <li key={result.criterion_id}>
        <span className="tag">{result.outcome === 'satisfied' ? 'Met' : result.outcome === 'refuted' ? 'Refuted' : 'Not met'}</span>
        {' '}{result.label ?? result.criterion_id}: {result.reasoning}
      </li>)}</ul>
    </>}

    {subclaims.length > 0 && <>
      <h4>Parts of this claim</h4>
      <ul>{subclaims.map(sub => <li key={sub.claim_id}>
        <span aria-hidden="true">{VERDICT_LABELS[sub.verdict ?? 'unproven'].mark} </span>
        {VERDICT_LABELS[sub.verdict ?? 'unproven'].text}: {sub.assertion}
      </li>)}</ul>
    </>}

    <h4>Evidence used</h4>
    {claim.evidence.length === 0
      ? <p className="muted">No admissible evidence supports or refutes this claim.</p>
      : <ul>{claim.evidence.map(item => <li key={item.id}>
        <blockquote>{item.observation}</blockquote>
        <p className="muted">
          From {AUTHORITY[item.authority_role] ?? item.authority_role}
          {item.self_reported ? ' (the supplier’s own statement)' : ''}
          {' · '}source dated {day(item.issued_at)}{' · '}retrieved {day(item.collected_at)}
          {item.expires_at ? ` · valid until ${day(item.expires_at)}` : ''}
          {item.replay ? ' · replay of a previously captured record' : ''}
          {' · '}identity {item.identity_state ?? 'unresolved'}
          {' · '}<a href={item.source_ref} rel="noreferrer noopener" target="_blank">original source</a>
        </p>
      </li>)}</ul>}

    {claim.considered.length > 0 && <>
      <h4>Records looked at but not used</h4>
      <ul>{claim.considered.map(record => <li key={`${record.evidence_id}-${record.criterion_id}`}>
        <blockquote>{record.observation}</blockquote>
        <p className="muted">Not used because: {record.reason}.</p>
      </li>)}</ul>
    </>}

    {claim.gaps.length > 0 && <>
      <h4>What is missing</h4>
      <ul>{claim.gaps.filter(gap => !gap.includes('record not used')).map(gap => <li key={gap}>{gap}</li>)}</ul>
    </>}

    <h4>Checks that were tried</h4>
    {claim.attempts.length === 0 ? <p className="muted">No check was recorded for this claim.</p>
      : <ul>{claim.attempts.map(attempt => <li key={attempt.id}>
        {OUTCOME_LABELS[attempt.outcome] ?? attempt.outcome}
        {attempt.reason_code ? ` — ${REASON_LABELS[attempt.reason_code] ?? attempt.reason_code}` : ''}
        {attempt.request_dispatched ? ` (request sent${attempt.http_status ? `, HTTP ${attempt.http_status}` : ''})` : ' (nothing was sent)'}
      </li>)}</ul>}
  </div>;
}
