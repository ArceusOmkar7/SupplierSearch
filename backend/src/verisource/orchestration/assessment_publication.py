"""Publish assessments and snapshots as each supplier finishes, independent of the others.

A supplier waiting on the buyer (or a slow source) never holds back the others: as soon as all of
a supplier's checks are resolved, its claims are assessed and a later snapshot is published. The
deadline and completion hooks in the graph publish the remaining state; identical states never
create duplicate assessments or snapshots, and closed or deleted generations cannot publish.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from verisource.db.models import Case, CheckTask, Claim, VerificationRun
from verisource.domain.evidence_policy import assess_checklist
from verisource.domain.snapshots import publish_snapshot
from verisource.orchestration.scheduling import RESOLVED


def publish_ready_suppliers(db: Session, case: Case, run: VerificationRun) -> bool:
    """Assess suppliers whose checks are all resolved; returns whether a snapshot was added."""
    if case.state in {"closed", "deleting"} or case.write_generation != run.generation:
        return False
    tasks = list(db.scalars(select(CheckTask).where(CheckTask.run_id == run.id)))
    pending = {t.supplier_id for t in tasks if t.state not in RESOLVED}
    ready = {t.supplier_id for t in tasks} - pending
    if not ready:
        return False
    claims = list(
        db.scalars(
            select(Claim).where(
                Claim.case_id == run.case_id,
                Claim.checklist_id == run.checklist_id,
                Claim.supplier_id.in_(ready),
            )
        )
    )
    assess_checklist(db, run, claims)
    before = case.latest_snapshot_id
    snapshot = publish_snapshot(db, case, run, "updated")
    return snapshot is not None and snapshot.id != before
