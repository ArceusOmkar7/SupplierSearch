"""Typed boundary between the shared core and a country pack.

A pack plans checks, normalizes identities, executes checks and proposes regulation
interpretations. It never returns a verdict, owner identifier or buyer message; the shared
evidence policy alone publishes verdicts. Every envelope carries the case-scoped context.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID


@dataclass(frozen=True)
class Envelope:
    case_id: UUID
    run_id: UUID
    revision_id: UUID
    checklist_id: UUID
    supplier_id: UUID
    site_id: UUID | None
    country_pack_version: str
    policy_version: str
    operation_key: str
    write_generation: int


@dataclass(frozen=True)
class SourceCapability:
    source_id: str
    version: int
    enabled: bool
    claim_types: tuple[str, ...]
    access_mode: str
    disabled_reason: str | None = None  # Plain explanation; never a purchase prompt.


@dataclass(frozen=True)
class PlannedCheck:
    key: str  # Local to the plan; dependency_keys refer to other keys.
    check_type: str
    source_id: str
    claim_ids: tuple[UUID, ...]
    supplier_id: UUID
    dependency_keys: tuple[str, ...] = ()


@dataclass(frozen=True)
class AttemptSpec:
    kind: str
    target: str
    requested_at: datetime
    finished_at: datetime
    request_dispatched: bool
    outcome: str
    reason_code: str | None = None
    http_status: int | None = None
    started_at: datetime | None = None
    artifact_refs: tuple[str, ...] = ()
    retry_of: int | None = None  # Index of the earlier attempt this one retries.


@dataclass(frozen=True)
class IdentityClaim:
    """How an observation was tied to the supplier. Only exact typed identifiers confirm."""

    candidate_ref: str
    state: str  # proposed | confirmed | ambiguous | rejected
    basis: str
    matches: tuple[dict[str, str], ...] = ()
    discrepancies: tuple[str, ...] = ()
    score: float | None = None


@dataclass(frozen=True)
class Observation:
    source_id: str
    source_version: int
    source_ref: str
    locator: str
    observation: str
    collected_at: datetime
    authority_role: str
    origin_lineage: str
    self_reported: bool
    content_hash: str
    assertion_tags: tuple[str, ...] = ()
    issued_at: datetime | None = None
    expires_at: datetime | None = None
    effective_at: datetime | None = None
    artifact_id: UUID | None = None
    replay: bool = False
    identity: IdentityClaim | None = None
    site_id: UUID | None = None  # Set only when the record's address matches a supplier site.


@dataclass(frozen=True)
class DependentAction:
    type: str  # supply_unlocked_document | resolve_identity
    requested_document_ref: UUID | None = None
    affects: str = "self"  # "self" | "dependents": which tasks wait for the buyer


@dataclass
class CheckResult:
    processing_state: str  # succeeded | no_evidence | waiting_input | failed
    attempts: list[AttemptSpec] = field(default_factory=list)
    observations: list[Observation] = field(default_factory=list)
    artifact_ids: list[UUID] = field(default_factory=list)
    missing_fields: list[str] = field(default_factory=list)
    coverage_gaps: list[str] = field(default_factory=list)
    identity_candidates: list[dict[str, Any]] = field(default_factory=list)
    dependent_action: DependentAction | None = None


class CountryPack(Protocol):
    jurisdiction: str
    version: str

    def capabilities(self) -> list[SourceCapability]: ...

    def plan_checks(
        self,
        requirements: dict[str, Any],
        supplier: dict[str, Any],
        claims: list[dict[str, Any]],
    ) -> list[PlannedCheck]: ...

    def normalize_identity(
        self, name: str, identifiers: list[dict[str, str]]
    ) -> dict[str, Any]: ...

    def execute_check(self, executor: Any, spec: Any) -> Any:
        """Run one planned check through the shared executor; no verdict, owner or message."""
        ...

    def interpret_regulation(
        self, db: Any, *, standards: list[str], product_text: str
    ) -> list[Any]:
        """Proposed applicability candidates with their order basis; policy validates them."""
        ...

    def warning_patterns(
        self, evidence: Any, addresses: dict[Any, list[tuple[str, str]]] | None = None
    ) -> list[Any]:
        """Attributable review indicators; never a conclusive verdict."""
        ...
