"""Execute one check task. External work happens here; persistence happens at acknowledgement.

Every executor returns real attempts and retrieved observations only. A skipped, blocked,
missing or empty check yields an attempt and a gap, never invented evidence, and never a
verdict: the shared evidence policy publishes verdicts from the persisted records.
"""

import hashlib
import re
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from verisource.config import Settings
from verisource.country_packs.contracts import (
    AttemptSpec,
    CheckResult,
    DependentAction,
    IdentityClaim,
    Observation,
)
from verisource.country_packs.india import bis as bis_pack
from verisource.country_packs.india.identity import REGISTRY_IDENTIFIERS, assess_candidate
from verisource.country_packs.india.registries import lookup_supplier, official_urls
from verisource.db.models import (
    CheckTask,
    Claim,
    DocumentArtifact,
    Extraction,
    RequirementRevision,
    SourceDataset,
    VerificationRun,
)
from verisource.documents.certificates import (
    SCHEMA_VERSION,
    PdfInspection,
    extract_certificate,
    inspect_pdf,
)
from verisource.domain.claims import present_claim, slug
from verisource.models.router import ModelRouter
from verisource.orchestration.persistence import (
    PendingArtifact,
    PendingExtraction,
    TaskOutcome,
)
from verisource.security.egress import GuardedFetch
from verisource.sources import browser, issuers, websites
from verisource.sources.fetching import permitted_get
from verisource.sources.manifests import DEFAULT_RECORDS_ROOT
from verisource.storage.filesystem import PrivateFileStore

_ID_PATTERNS = {
    "gstin": re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b"),
    "cin": re.compile(r"\b[LU]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}\b"),
    "llpin": re.compile(r"\b[A-Z]{3}-\d{4}\b"),
    "udyam": re.compile(r"\bUDYAM-[A-Z]{2}-\d{2}-\d{7}\b"),
}


@dataclass(frozen=True)
class TaskSpec:
    task_id: UUID
    case_id: UUID
    run_id: UUID
    supplier_id: UUID
    check_type: str
    source_id: str
    claim_ids: tuple[UUID, ...]
    mode: str
    revision_id: UUID
    requirements: dict[str, Any]
    supplier: dict[str, Any]
    claims: list[dict[str, Any]]
    country: str


def load_spec(db: Session, task_id: UUID) -> TaskSpec | None:
    task = db.get(CheckTask, task_id)
    if task is None:
        return None
    run = db.get(VerificationRun, task.run_id)
    revision = db.get(RequirementRevision, run.revision_id) if run else None
    if run is None or revision is None:
        return None
    supplier = next(
        (s for s in revision.supplier_set_json if s["supplier_id"] == str(task.supplier_id)), None
    )
    if supplier is None:
        return None
    claims = list(
        db.scalars(
            select(Claim).where(
                Claim.case_id == task.case_id,
                Claim.checklist_id == run.checklist_id,
                Claim.supplier_id == task.supplier_id,
            )
        )
    )
    return TaskSpec(
        task.id,
        task.case_id,
        run.id,
        task.supplier_id,
        task.check_type,
        task.source_id,
        tuple(task.claim_ids),
        run.mode,
        revision.id,
        dict(revision.requirements_json),
        dict(supplier),
        [present_claim(c) for c in claims],
        revision.location_json.get("country") or "IN",
    )


def _now() -> datetime:
    return datetime.now(UTC)


def _skip(reason: str, target: str, *, kind: str = "capability_check") -> AttemptSpec:
    stamp = _now()
    return AttemptSpec(kind, target, stamp, stamp, False, "skipped", reason)


def _local(outcome: str, target: str, reason: str | None = None) -> AttemptSpec:
    stamp = _now()
    return AttemptSpec("document_read", target, stamp, stamp, False, outcome, reason)


def _identifiers(supplier: dict[str, Any]) -> list[dict[str, str]]:
    return [{"type": i["type"], "value": i["normalized"]} for i in supplier.get("identifiers", [])]


def _scan_identity(
    supplier: dict[str, Any], text: str, candidate_ref: str, *, name: str | None = None
) -> IdentityClaim:
    """Confirm only when a typed identifier printed in the source equals the buyer's."""
    ours = _identifiers(supplier)
    found = {
        kind: sorted({m.upper() for m in pattern.findall(text.upper())})
        for kind, pattern in _ID_PATTERNS.items()
    }
    candidate = {kind: values[0] for kind, values in found.items() if values}
    for kind, values in found.items():
        for ours_item in ours:
            if ours_item["type"] == kind and ours_item["value"].upper() in values:
                candidate[kind] = ours_item["value"].upper()
    assessment = assess_candidate(supplier["display_name"], ours, name or "", candidate)
    if assessment.state == "confirmed":
        return IdentityClaim(
            candidate_ref,
            "confirmed",
            assessment.basis,
            tuple(assessment.identifier_matches),
            tuple(assessment.discrepancies),
            assessment.score,
        )
    score = assessment.score
    state = "proposed" if (score or 0) >= 0.6 else "ambiguous"
    if assessment.state == "rejected":
        state = "rejected"
    return IdentityClaim(
        candidate_ref,
        state,
        "buyer_supplied_website" if name is None else assessment.basis,
        tuple(assessment.identifier_matches),
        tuple(assessment.discrepancies),
        score,
    )


def _not_entity_specific(ref: str) -> IdentityClaim:
    return IdentityClaim(ref, "confirmed", "not_entity_specific")


class Executor:
    def __init__(
        self,
        settings: Settings,
        engine: Engine,
        *,
        fetcher_factory: Callable[[], GuardedFetch] = GuardedFetch,
        router: ModelRouter | None = None,
        renderer: Callable[[str], tuple[int, bytes] | None] | None = browser.render,
        records_root: Path = DEFAULT_RECORDS_ROOT,
    ) -> None:
        self.settings = settings
        self.engine = engine
        self.fetcher_factory = fetcher_factory
        self.router = router
        self.renderer = renderer
        self.records_root = records_root
        self.store = PrivateFileStore(settings.data_root)

    def execute(self, spec: TaskSpec) -> TaskOutcome:
        handler = {
            "local_export_lookup": self.local_export_lookup,
            "bis_applicability": self.bis_applicability,
            "website_traversal": self.website_traversal,
            "certificate_document": self.certificate_document,
            "certificate_issuer_lookup": self.issuer_lookup,
            "certificate_qr_follow": self.qr_follow,
            "coverage_unsupported": self.unsupported,
        }.get(spec.check_type)
        if handler is None:
            return TaskOutcome(
                CheckResult("failed", [_skip("not_supported", f"check:{spec.check_type}")]),
                final_state="failed",
            )
        return handler(spec)

    # ---- imported official exports ------------------------------------------------------

    def local_export_lookup(self, spec: TaskSpec) -> TaskOutcome:
        ids = [i for i in _identifiers(spec.supplier) if i["type"] in REGISTRY_IDENTIFIERS]
        if not ids:
            return TaskOutcome(
                CheckResult(
                    "no_evidence",
                    [_skip("missing_identifier", "local-export")],
                    coverage_gaps=[
                        "No registry identifier was supplied for an exact export lookup."
                    ],
                ),
                final_state="no_evidence",
            )
        with Session(self.engine) as db:
            hits = lookup_supplier(
                db, spec.supplier["display_name"], ids, address=spec.supplier.get("address")
            )
        if not hits:
            return TaskOutcome(
                CheckResult(
                    "no_evidence",
                    [_local("no_record", "local-export")],
                    coverage_gaps=[
                        (
                            "No imported official export lists this identifier; "
                            "that is not proof the entity does not exist."
                        )
                    ],
                ),
                final_state="no_evidence",
            )
        observations = []
        for hit in hits:
            base = hit.observation
            tags = (*base.assertion_tags, "supports:regulatory.licence")
            tagged = _with_tags(base, tags)
            site = spec.supplier.get("site_id")
            if hit.site_matched and site:
                tagged = replace(tagged, site_id=UUID(site))
            observations.append(tagged)
        return TaskOutcome(
            CheckResult("succeeded", [_local("success", "local-export")], observations)
        )

    def bis_applicability(self, spec: TaskSpec) -> TaskOutcome:
        attempts = [_skip("not_supported", "manak-current-licence-search")]
        gaps = [
            (
                "The current BIS licence search is CAPTCHA-protected and is never automated; "
                "licence coverage stays unproven."
            )
        ]
        with Session(self.engine) as db:
            has_catalogue = db.scalar(
                select(SourceDataset.id).where(
                    SourceDataset.schema_version == bis_pack.SCHEMA_VERSION,
                    SourceDataset.state == "imported",
                )
            )
            standards = [str(s) for s in spec.requirements.get("standards") or []]
            candidates = (
                bis_pack.applicability_candidates(
                    db,
                    standards=standards,
                    product_text=str(spec.requirements.get("part_description") or ""),
                )
                if has_catalogue
                else []
            )
        if not has_catalogue:
            attempts.append(_skip("not_configured", "bis-qco-catalogue"))
            gaps.append("No BIS order catalogue has been imported.")
            return TaskOutcome(
                CheckResult("no_evidence", attempts, coverage_gaps=gaps), final_state="no_evidence"
            )
        if not candidates:
            attempts.append(_local("no_record", "bis-qco-catalogue"))
            gaps.append(
                "No catalogue entry matched; an incomplete or stale catalogue cannot establish "
                "that no order applies."
            )
            return TaskOutcome(
                CheckResult("no_evidence", attempts, coverage_gaps=gaps), final_state="no_evidence"
            )
        attempts.append(_local("success", "bis-qco-catalogue"))
        observations = [
            Observation(
                source_id="in.bis-orders",
                source_version=1,
                source_ref="bis-qco-scheme1",
                locator=c.basis.split(":")[0],
                observation=(
                    f"BIS catalogue entry (order text not read; exemptions and implementation "
                    f"dates unknown): {c.product_scope}; {', '.join(c.standard_codes)}; "
                    f"order {c.order_number}"
                ),
                collected_at=_now(),
                authority_role="official_publication",
                origin_lineage="dataset:bis-qco-scheme1",
                self_reported=False,
                content_hash=hashlib.sha256(c.basis.encode()).hexdigest(),
                assertion_tags=("coverage:partial", "supports:regulatory.order"),
                issued_at=c.issued_on,
                identity=_not_entity_specific(f"qco:{c.order_number}"),
            )
            for c in candidates[:5]
        ]
        return TaskOutcome(CheckResult("succeeded", attempts, observations, coverage_gaps=gaps))

    # ---- supplier website ---------------------------------------------------------------

    def _tag_terms(self, spec: TaskSpec) -> dict[str, str]:
        terms: dict[str, str] = {"manufactur": "supports:manufacturer.site_activity"}
        for label, key in (("material", "materials"), ("process", "processes")):
            for value in spec.requirements.get(key) or []:
                terms[str(value)] = f"supports:capability.{label}.{slug(str(value))}"
        return terms

    def website_traversal(self, spec: TaskSpec) -> TaskOutcome:
        sites = [i["value"] for i in _identifiers(spec.supplier) if i["type"] == "website"]
        if not sites:
            return TaskOutcome(
                CheckResult(
                    "no_evidence",
                    [_skip("missing_identifier", "supplier-website")],
                    coverage_gaps=[
                        "No supplier website was provided; marketplace links are not fetched."
                    ],
                ),
                final_state="no_evidence",
            )
        if spec.mode == "replay":
            return self._replay_website(spec, sites[0])
        fetcher = self.fetcher_factory()
        try:
            traversed = websites.traverse(
                sites[0],
                tag_terms=self._tag_terms(spec),
                fetcher=fetcher,
                renderer=self.renderer,
            )
        finally:
            fetcher.close()
        artifacts: list[PendingArtifact] = []
        for page in [*traversed.pages, *traversed.pdfs]:
            stored = self.store.put(spec.case_id, page.body)
            artifacts.append(
                PendingArtifact(
                    stored.storage_key,
                    stored.sha256,
                    stored.byte_count,
                    page.content_type or "text/html",
                    source_url=page.url,
                )
            )
        combined = " ".join(p.text for p in traversed.pages)
        identity = _scan_identity(spec.supplier, combined, f"website:{sites[0]}")
        observations = [
            _with_identity(o, identity, artifact_ref=o.source_ref) for o in traversed.observations
        ]
        state = "succeeded" if observations else "no_evidence"
        return TaskOutcome(
            CheckResult(
                state,
                traversed.attempts,
                observations,
                coverage_gaps=traversed.coverage_gaps,
            ),
            artifacts,
            final_state=state,
        )

    def _replay_website(self, spec: TaskSpec, site: str) -> TaskOutcome:
        """Replay a genuine captured page of this host; labeled replay with its capture date."""
        import json

        from verisource.sources.manifests import load_record

        host = (urlsplit(site if "//" in site else f"https://{site}").hostname or "").removeprefix(
            "www."
        )
        for manifest_path in sorted(self.records_root.glob("*.manifest.json")):
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except ValueError:
                continue
            if (
                manifest.get("kind") == "supplier"
                and manifest.get("format") == "html"
                and (urlsplit(manifest["original_url"]).hostname or "").removeprefix("www.") == host
            ):
                manifest, content = load_record(manifest_path, self.records_root)
                title, text, _links = websites._text_and_links(content, manifest["original_url"])
                tags = sorted(
                    {
                        t
                        for term, t in self._tag_terms(spec).items()
                        if term.casefold() in text.casefold()
                    }
                )
                stored = self.store.put(spec.case_id, content)
                observed = datetime.fromisoformat(manifest["obtained_at"])
                observation = Observation(
                    "in.supplier-website",
                    1,
                    manifest["original_url"],
                    manifest["original_url"],
                    f"{title}: {text[:600]}",
                    observed,
                    "supplier",
                    f"supplier-website:{host}",
                    True,
                    hashlib.sha256(content).hexdigest(),
                    tuple(tags),
                    replay=True,
                    identity=_scan_identity(spec.supplier, text, f"website:{host}"),
                )
                return TaskOutcome(
                    CheckResult(
                        "succeeded",
                        [_local("success", f"replay:{manifest_path.name}")],
                        [observation],
                        coverage_gaps=[
                            f"Replay of a capture made {manifest['obtained_at']}; not live."
                        ],
                    ),
                    [
                        PendingArtifact(
                            stored.storage_key,
                            stored.sha256,
                            stored.byte_count,
                            "text/html",
                            source_url=manifest["original_url"],
                        )
                    ],
                )
        return TaskOutcome(
            CheckResult(
                "no_evidence",
                [_skip("not_configured", f"replay:{host}")],
                coverage_gaps=["No genuine capture exists for this site; nothing was substituted."],
            ),
            final_state="no_evidence",
        )

    # ---- certificates -------------------------------------------------------------------

    def _supplier_pdfs(self, spec: TaskSpec) -> list[tuple[DocumentArtifact, bytes]]:
        with Session(self.engine) as db:
            rows = list(
                db.scalars(
                    select(DocumentArtifact).where(
                        DocumentArtifact.case_id == spec.case_id,
                        DocumentArtifact.supplier_id == spec.supplier_id,
                        DocumentArtifact.media_type == "application/pdf",
                        DocumentArtifact.origin.in_(("buyer_upload", "source_fetch")),
                        DocumentArtifact.state != "failed",  # Superseded or unreadable copies.
                    )
                )
            )
        return [(row, self.store.read(row.storage_key, row.sha256)) for row in rows]

    def certificate_document(self, spec: TaskSpec) -> TaskOutcome:
        documents = self._supplier_pdfs(spec)
        if not documents:
            return TaskOutcome(
                CheckResult(
                    "no_evidence",
                    [_local("no_record", "certificate-documents")],
                    coverage_gaps=[
                        "No certificate document was uploaded or found on the supplier site."
                    ],
                ),
                final_state="no_evidence",
            )
        attempts: list[AttemptSpec] = []
        observations: list[Observation] = []
        extractions: list[PendingExtraction] = []
        gaps: list[str] = []
        action: DependentAction | None = None
        for artifact, content in documents:
            inspection = inspect_pdf(content)
            target = f"document:{artifact.sha256[:12]}"
            if inspection.failure_reason == "locked_document":
                attempts.append(_local("blocked", target, "locked_document"))
                if artifact.origin == "buyer_upload":
                    action = DependentAction("supply_unlocked_document", artifact.id, "self")
                else:
                    gaps.append(
                        f"{target}: downloaded document is locked; not unlocked or bypassed."
                    )
                continue
            if inspection.failure_reason:
                attempts.append(_local("invalid_input", target, inspection.failure_reason))
                gaps.append(f"{target}: unreadable ({inspection.failure_reason}).")
                continue
            if not inspection.text_pages:
                attempts.append(_local("invalid_input", target, "malformed_document"))
                gaps.append(f"{target}: scanned pages; OCR unavailable, content unread.")
                if artifact.origin == "buyer_upload":
                    action = DependentAction("supply_unlocked_document", artifact.id, "self")
                continue
            attempts.append(_local("success", target))
            observations_for, extraction, identity_state = self._read_certificate(
                spec, artifact, inspection
            )
            observations.extend(observations_for)
            extractions.append(extraction)
            if identity_state == "proposed" and action is None:
                action = DependentAction("resolve_identity", None, "dependents")
        if action is not None and action.affects == "self":
            return TaskOutcome(
                CheckResult(
                    "waiting_input",
                    attempts,
                    observations,
                    coverage_gaps=gaps,
                    dependent_action=action,
                ),
                extractions=extractions,
                final_state="waiting_input",
            )
        state = "succeeded" if observations else "no_evidence"
        return TaskOutcome(
            CheckResult(state, attempts, observations, coverage_gaps=gaps, dependent_action=action),
            extractions=extractions,
            final_state=state,
        )

    def _read_certificate(
        self, spec: TaskSpec, artifact: DocumentArtifact, inspection: PdfInspection
    ) -> tuple[list[Observation], PendingExtraction, str]:
        fields, method, missing = extract_certificate(self.router, inspection)
        text = "\n".join(inspection.pages.values())
        holder = fields.holder_name.value if fields.holder_name else None
        identity = _scan_identity(
            spec.supplier, text, f"document:{artifact.sha256}", name=holder or ""
        )
        data = {
            name: getattr(fields, name).model_dump()
            for name in (
                "certificate_number",
                "holder_name",
                "issuer",
                "standard",
                "scope",
                "site_address",
                "issue_date",
                "expiry_date",
            )
            if getattr(fields, name) is not None
        }
        data["official_urls"] = official_urls(text)
        extraction = PendingExtraction(
            artifact.sha256,
            sorted(inspection.pages),
            method,
            data,
            missing,
            list(fields.uncertainties),
            None if method == "rule" else method,
            SCHEMA_VERSION,
            hashlib.sha256(repr(sorted(data.items())).encode()).hexdigest(),
        )
        tags: list[str] = []
        if fields.scope:
            tags.append("supports:certificate.scope")
        if fields.site_address:
            tags.append("supports:certificate.site")
        if fields.expiry_date:
            tags.append("supports:certificate.validity")
        parts = [
            f"{label} {getattr(fields, name).value}"
            for label, name in (
                ("number", "certificate_number"),
                ("holder", "holder_name"),
                ("issuer", "issuer"),
                ("standard", "standard"),
                ("scope", "scope"),
                ("site", "site_address"),
                ("issued", "issue_date"),
                ("expires", "expiry_date"),
            )
            if getattr(fields, name) is not None
        ]
        observation = Observation(
            source_id="in.buyer-certificate",
            source_version=1,
            source_ref=artifact.source_url or f"document:{artifact.id}",
            locator=f"pages {sorted(inspection.pages)}",
            observation="Supplier-provided certificate states: " + "; ".join(parts)
            if parts
            else "Supplier-provided certificate text was read but no field could be quoted.",
            collected_at=_now(),
            authority_role="supplier",
            origin_lineage=f"document:{artifact.sha256}",
            self_reported=True,
            content_hash=artifact.sha256,
            assertion_tags=tuple(tags),
            artifact_id=artifact.id,
            identity=identity,
        )
        return [observation], extraction, identity.state

    def _extractions(self, spec: TaskSpec) -> list[dict[str, Any]]:
        with Session(self.engine) as db:
            rows = db.execute(
                select(Extraction, DocumentArtifact)
                .join(
                    DocumentArtifact,
                    (DocumentArtifact.id == Extraction.artifact_id)
                    & (DocumentArtifact.case_id == Extraction.case_id),
                )
                .where(
                    Extraction.case_id == spec.case_id,
                    DocumentArtifact.supplier_id == spec.supplier_id,
                )
            ).all()
        return [{**e.fields, "_sha": a.sha256, "_id": str(a.id)} for e, a in rows]

    def issuer_lookup(self, spec: TaskSpec) -> TaskOutcome:
        read = [e for e in self._extractions(spec) if e.get("issuer")]
        if not read:
            return TaskOutcome(
                CheckResult(
                    "no_evidence",
                    [_skip("missing_identifier", "issuer-pages")],
                    coverage_gaps=["No issuer name could be read from a certificate."],
                ),
                final_state="no_evidence",
            )
        attempts: list[AttemptSpec] = []
        observations: list[Observation] = []
        gaps: list[str] = []
        fetcher = self.fetcher_factory()
        try:
            for entry in read:
                number = (entry.get("certificate_number") or {}).get("value")
                checked = issuers.check_issuer(fetcher, entry["issuer"]["value"], number)
                attempts.extend(checked.attempts)
                gaps.extend(checked.gaps)
                for observation in checked.observations:
                    tags = list(observation.assertion_tags)
                    if "accreditation:issuer_listed" in tags:
                        tags.append("supports:certificate.accreditation")
                    identity = (
                        _not_entity_specific(observation.source_ref)
                        if "accreditation:issuer_listed" in tags
                        else IdentityClaim(
                            f"document:{entry['_sha']}", "proposed", "certificate_number_listed"
                        )
                    )
                    observations.append(
                        _with_tags(_with_identity(observation, identity), tuple(tags))
                    )
        finally:
            fetcher.close()
        state = "succeeded" if observations else "no_evidence"
        return TaskOutcome(
            CheckResult(state, attempts, observations, coverage_gaps=gaps), final_state=state
        )

    def qr_follow(self, spec: TaskSpec) -> TaskOutcome:
        urls = [u for e in self._extractions(spec) for u in e.get("official_urls", [])]
        if not urls:
            return TaskOutcome(
                CheckResult(
                    "no_evidence",
                    [_skip("missing_identifier", "official-links")],
                    coverage_gaps=[
                        "No printed official link was found; QR images are not decoded locally."
                    ],
                ),
                final_state="no_evidence",
            )
        attempts: list[AttemptSpec] = []
        observations: list[Observation] = []
        gaps: list[str] = []
        fetcher = self.fetcher_factory()
        try:
            for url in urls[:3]:
                if (urlsplit(url).hostname or "").lower() in issuers.PROFILE_HOSTS:
                    profile = issuers.read_profile(
                        fetcher,
                        url,
                        supplier_name=spec.supplier["display_name"],
                        supplier_identifiers=_identifiers(spec.supplier),
                    )
                    attempts.extend(profile.attempts)
                    observations.extend(profile.observations)
                    gaps.extend(profile.gaps)
                    continue
                fetched = permitted_get(fetcher, url, max_bytes=2 * 1024 * 1024)
                attempts.extend(fetched.attempts)
                if fetched.response is None:
                    gaps.append(f"{url}: {fetched.gap}")
                    continue
                _title, text, _ = websites._text_and_links(
                    fetched.response.content, fetched.final_url
                )
                observations.append(
                    Observation(
                        "in.issuer-pages",
                        1,
                        fetched.final_url,
                        fetched.final_url,
                        f"Official page linked from the certificate: {text[:600]}",
                        _now(),
                        "official_publication",
                        f"official-link:{urlsplit(fetched.final_url).hostname}",
                        False,
                        hashlib.sha256(fetched.response.content).hexdigest(),
                        ("official_link_content",),
                        identity=IdentityClaim(
                            f"link:{fetched.final_url}", "proposed", "printed_link"
                        ),
                    )
                )
        finally:
            fetcher.close()
        state = "succeeded" if observations else "no_evidence"
        return TaskOutcome(
            CheckResult(state, attempts, observations, coverage_gaps=gaps), final_state=state
        )

    def unsupported(self, spec: TaskSpec) -> TaskOutcome:
        return TaskOutcome(
            CheckResult(
                "no_evidence",
                [_skip("not_supported", f"jurisdiction:{spec.country}")],
                coverage_gaps=[f"No country pack covers {spec.country}; claims stay unproven."],
            ),
            final_state="no_evidence",
        )


def _with_tags(observation: Observation, tags: tuple[str, ...]) -> Observation:
    return replace(observation, assertion_tags=tuple(dict.fromkeys(tags)))


def _with_identity(
    observation: Observation, identity: IdentityClaim, *, artifact_ref: str | None = None
) -> Observation:
    del artifact_ref
    return replace(observation, identity=identity)
