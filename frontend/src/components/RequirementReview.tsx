import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { ApiError } from '../api/client';
import { confirmRevision, getRevision, patchRevision, type NewSupplier } from '../api/cases';
import type { Revision } from '../api/types';
import { FIELD_LABELS, IDENTIFIER_TYPES } from './labels';

interface Props {
  caseId: string;
  revision: Revision;
  onChange: (revision: Revision) => void;
}

interface SupplierDraft {
  supplier_id?: string;
  display_name: string;
  identifiers: { type: string; value: string }[];
  address: string;
  address_role: string;
}

const list = (value: string) => value.split(',').map(item => item.trim()).filter(Boolean);

function toDrafts(revision: Revision): SupplierDraft[] {
  return revision.suppliers.map(supplier => ({
    supplier_id: supplier.supplier_id,
    display_name: supplier.display_name,
    identifiers: supplier.identifiers.map(({ type, value }) => ({ type, value })),
    address: supplier.address ?? '',
    address_role: supplier.address_role ?? 'unknown',
  }));
}

function Provenance({ revision, field }: { revision: Revision; field: string }) {
  const entry = revision.field_provenance[field];
  if (!entry) return null;
  return entry.source === 'model_proposed'
    ? <span className="tag proposed" title={entry.quote ? `Quoted from your message: “${entry.quote}”` : undefined}>
        Proposed from your message — check it
      </span>
    : <span className="tag">Entered by you</span>;
}

export function RequirementReview({ caseId, revision, onChange }: Props) {
  const locked = revision.status !== 'draft';
  const [part, setPart] = useState('');
  const [materials, setMaterials] = useState('');
  const [processes, setProcesses] = useState('');
  const [certifications, setCertifications] = useState('');
  const [standards, setStandards] = useState('');
  const [tolerance, setTolerance] = useState('');
  const [qtyValue, setQtyValue] = useState('');
  const [qtyUnit, setQtyUnit] = useState('');
  const [qtyPeriod, setQtyPeriod] = useState('');
  const [country, setCountry] = useState('');
  const [reference, setReference] = useState('');
  const [radiusValue, setRadiusValue] = useState('');
  const [radiusUnit, setRadiusUnit] = useState('km');
  const [suppliers, setSuppliers] = useState<SupplierDraft[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [conflict, setConflict] = useState(false);

  useEffect(() => {
    const r = revision.requirements;
    setPart(r.part_description ?? '');
    setMaterials(r.materials.join(', '));
    setProcesses(r.processes.join(', '));
    setCertifications(r.certifications.join(', '));
    setStandards(r.standards.join(', '));
    setTolerance(r.tolerance ?? '');
    setQtyValue(r.quantity ? String(r.quantity.value) : '');
    setQtyUnit(r.quantity?.unit ?? '');
    setQtyPeriod(r.quantity?.period ?? '');
    setCountry(revision.location.country ?? '');
    setReference(revision.location.reference_location ?? '');
    setRadiusValue(revision.location.radius ? String(revision.location.radius.value) : '');
    setRadiusUnit(revision.location.radius?.unit ?? 'km');
    setSuppliers(toDrafts(revision));
    setConflict(false);
  }, [revision]);

  const missing = useMemo(() => {
    const problems: string[] = [];
    if (!part.trim()) problems.push('Describe the part or equipment you need.');
    if (!suppliers.some(s => s.display_name.trim() || s.identifiers.some(i => i.value.trim()))) {
      problems.push('Add at least one supplier to verify.');
    }
    return problems;
  }, [part, suppliers]);

  function body() {
    const quantity = qtyValue.trim()
      ? { value: Number(qtyValue), unit: qtyUnit.trim(), period: qtyPeriod.trim() || null }
      : null;
    const radius = radiusValue.trim() ? { value: Number(radiusValue), unit: radiusUnit } : null;
    const payload: NewSupplier[] = suppliers.map(s => ({
      supplier_id: s.supplier_id,
      display_name: s.display_name.trim() || undefined,
      identifiers: s.identifiers.filter(i => i.value.trim()).map(i => ({ type: i.type, value: i.value.trim() })),
      address: s.address.trim() || null,
      address_role: s.address_role,
    }));
    return {
      requirements: {
        part_description: part.trim() || null,
        materials: list(materials),
        processes: list(processes),
        certifications: list(certifications),
        standards: list(standards),
        tolerance: tolerance.trim() || null,
        quantity,
      },
      location: {
        country: country.trim() || null,
        reference_location: reference.trim() || null,
        radius,
      },
      suppliers: payload,
    };
  }

  async function run(action: (current: Revision) => Promise<Revision>, saveFirst: boolean) {
    setBusy(true);
    setError('');
    try {
      let current = revision;
      if (saveFirst) current = await patchRevision(caseId, current, body());
      onChange(await action(current));
    } catch (failure) {
      if (failure instanceof ApiError && failure.status === 412) setConflict(true);
      setError(failure instanceof ApiError ? failure.message : 'The request could not be completed.');
    } finally { setBusy(false); }
  }

  async function reload() {
    setBusy(true);
    try { onChange(await getRevision(caseId, revision.id)); setError(''); }
    catch { setError('Could not reload this requirement.'); }
    finally { setBusy(false); }
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    void run(current => Promise.resolve(current), true);
  }

  const updateSupplier = (index: number, patch: Partial<SupplierDraft>) =>
    setSuppliers(items => items.map((item, i) => (i === index ? { ...item, ...patch } : item)));

  return <form className="panel" aria-labelledby="requirements-title" onSubmit={submit} aria-busy={busy}>
    <h2 id="requirements-title">
      Requirements <span className="tag">{locked ? `Confirmed (revision ${revision.sequence})` : `Draft (revision ${revision.sequence})`}</span>
    </h2>
    {!locked && <p>Nothing is verified until you confirm these requirements and then the checklist. Every field below is editable.</p>}
    {revision.review_flags.length > 0 && <p role="alert" className="notice">
      Some suppliers share a name or registry identifier. They are kept separate; review them before confirming.
    </p>}
    {revision.missing_fields.length > 0 && !locked && <p className="muted">
      Not provided: {revision.missing_fields.map(field => FIELD_LABELS[field] ?? field).join(', ')}. Missing values are never guessed.
    </p>}

    <div className="field">
      <label htmlFor="part">{FIELD_LABELS.part_description} <Provenance revision={revision} field="part_description" /></label>
      <textarea id="part" rows={3} value={part} disabled={locked || busy} onChange={e => setPart(e.target.value)} />
    </div>
    <div className="grid two">
      <div className="field"><label htmlFor="materials">{FIELD_LABELS.materials} (comma separated)</label>
        <input id="materials" value={materials} disabled={locked || busy} onChange={e => setMaterials(e.target.value)} /></div>
      <div className="field"><label htmlFor="processes">{FIELD_LABELS.processes} (comma separated)</label>
        <input id="processes" value={processes} disabled={locked || busy} onChange={e => setProcesses(e.target.value)} /></div>
      <div className="field"><label htmlFor="certs">{FIELD_LABELS.certifications} (comma separated)</label>
        <input id="certs" value={certifications} disabled={locked || busy} onChange={e => setCertifications(e.target.value)} /></div>
      <div className="field"><label htmlFor="standards">{FIELD_LABELS.standards} (comma separated)</label>
        <input id="standards" value={standards} disabled={locked || busy} onChange={e => setStandards(e.target.value)} /></div>
      <div className="field"><label htmlFor="tolerance">{FIELD_LABELS.tolerance}</label>
        <input id="tolerance" value={tolerance} disabled={locked || busy} onChange={e => setTolerance(e.target.value)} /></div>
    </div>

    <fieldset disabled={locked || busy}>
      <legend>Quantity</legend>
      <div className="grid three">
        <div className="field"><label htmlFor="qty">Amount</label>
          <input id="qty" inputMode="decimal" value={qtyValue} onChange={e => setQtyValue(e.target.value)} /></div>
        <div className="field"><label htmlFor="qty-unit">Unit</label>
          <input id="qty-unit" value={qtyUnit} onChange={e => setQtyUnit(e.target.value)} /></div>
        <div className="field"><label htmlFor="qty-period">Period (optional)</label>
          <input id="qty-period" value={qtyPeriod} onChange={e => setQtyPeriod(e.target.value)} /></div>
      </div>
    </fieldset>

    <fieldset disabled={locked || busy}>
      <legend>Location</legend>
      <div className="grid three">
        <div className="field"><label htmlFor="country">Country code (for example IN)</label>
          <input id="country" value={country} onChange={e => setCountry(e.target.value)} /></div>
        <div className="field"><label htmlFor="reference">Reference location</label>
          <input id="reference" value={reference} onChange={e => setReference(e.target.value)} /></div>
        <div className="field"><label htmlFor="radius">Radius</label>
          <div className="inline">
            <input id="radius" inputMode="decimal" value={radiusValue} onChange={e => setRadiusValue(e.target.value)} />
            <select aria-label="Radius unit" value={radiusUnit} onChange={e => setRadiusUnit(e.target.value)}>
              <option value="km">km</option><option value="mi">mi</option><option value="m">m</option>
            </select>
          </div></div>
      </div>
    </fieldset>

    <fieldset disabled={locked || busy}>
      <legend>Suppliers to verify</legend>
      {suppliers.length === 0 && <p className="muted">No suppliers yet.</p>}
      {suppliers.map((supplier, index) => <div className="card" key={supplier.supplier_id ?? `new-${index}`}>
        <div className="field"><label htmlFor={`name-${index}`}>Supplier {index + 1} name</label>
          <input id={`name-${index}`} value={supplier.display_name} onChange={e => updateSupplier(index, { display_name: e.target.value })} /></div>
        {supplier.identifiers.map((identifier, position) => <div className="inline" key={position}>
          <select aria-label={`Supplier ${index + 1} identifier type ${position + 1}`} value={identifier.type}
            onChange={e => updateSupplier(index, { identifiers: supplier.identifiers.map((item, i) => i === position ? { ...item, type: e.target.value } : item) })}>
            {IDENTIFIER_TYPES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
          <input aria-label={`Supplier ${index + 1} identifier value ${position + 1}`} value={identifier.value}
            onChange={e => updateSupplier(index, { identifiers: supplier.identifiers.map((item, i) => i === position ? { ...item, value: e.target.value } : item) })} />
          <button type="button" className="secondary" aria-label={`Remove identifier ${position + 1} from supplier ${index + 1}`}
            onClick={() => updateSupplier(index, { identifiers: supplier.identifiers.filter((_, i) => i !== position) })}>Remove</button>
        </div>)}
        <button type="button" className="secondary"
          onClick={() => updateSupplier(index, { identifiers: [...supplier.identifiers, { type: 'website', value: '' }] })}>
          Add an identifier to supplier {index + 1}
        </button>
        <div className="grid two">
          <div className="field"><label htmlFor={`address-${index}`}>Address as published</label>
            <input id={`address-${index}`} value={supplier.address} onChange={e => updateSupplier(index, { address: e.target.value })} /></div>
          <div className="field"><label htmlFor={`role-${index}`}>This address is a</label>
            <select id={`role-${index}`} value={supplier.address_role} onChange={e => updateSupplier(index, { address_role: e.target.value })}>
              <option value="unknown">Not stated</option><option value="registered_office">Registered office</option>
              <option value="production_site">Production site</option><option value="other">Other</option>
            </select></div>
        </div>
        <button type="button" className="secondary" onClick={() => setSuppliers(items => items.filter((_, i) => i !== index))}>
          Remove supplier {index + 1}
        </button>
      </div>)}
      <button type="button" className="secondary"
        onClick={() => setSuppliers(items => [...items, { display_name: '', identifiers: [{ type: 'name', value: '' }], address: '', address_role: 'unknown' }])}>
        Add a supplier
      </button>
    </fieldset>

    {error && <p role="alert">{error}{conflict && <> <button type="button" className="secondary" onClick={reload}>Reload the latest version</button></>}</p>}
    {!locked && <div className="actions">
      <button type="submit" disabled={busy}>Save draft</button>
      <button type="button" disabled={busy || missing.length > 0} aria-describedby="confirm-help"
        onClick={() => void run(current => confirmRevision(caseId, current), true)}>
        Confirm requirements
      </button>
      <p id="confirm-help" className="muted">{missing.length ? missing.join(' ') : 'Confirming freezes this revision; later changes become a new revision.'}</p>
    </div>}
    {locked && revision.confirmed_at && <p className="muted">Confirmed {new Date(revision.confirmed_at).toLocaleString()}.</p>}
  </form>;
}
