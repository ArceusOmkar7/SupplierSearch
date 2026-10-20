"""Evaluation against actual independent human audit labels and observed buyer timings.

Nothing here generates labels, verdicts or timings. A criterion is `passed` or `failed` only when
every required real input exists; otherwise it is `unmeasured` and lists exactly what is missing.
Model output is never accepted as ground truth, and a five-supplier timing run or an average
cannot satisfy the per-supplier timing criterion.
"""

import json
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

from jsonschema import Draft202012Validator, FormatChecker
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from verisource.config import REPO_ROOT
from verisource.db.models import Assessment, Claim, VerificationRun

SCHEMA_PATH = REPO_ROOT / "tests/records/audit-manifest.schema.json"
VERDICTS = ("proven", "unproven", "contradicted")
CLAIM_TYPES = (
    "legal_existence",
    "manufacturer",
    "part_capability",
    "certificate",
    "regulatory",
    "capacity",
)
AGREEMENT_TARGET = 0.80
PER_SUPPLIER_LIMIT = timedelta(hours=1)
LIMITATIONS = (
    "The manual-effort baseline remains an unverified estimate.",
    "Agreement is measured only on claims an independent human auditor labelled.",
)


def load_manifest(path: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(manifest)
    return manifest  # type: ignore[no-any-return]


def parse(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(UTC)


def merge_intervals(spans: list[tuple[datetime, datetime]]) -> list[tuple[datetime, datetime]]:
    """Union of spans: overlapping time is never counted twice."""
    merged: list[tuple[datetime, datetime]] = []
    for start, end in sorted(spans):
        if end < start:
            raise ValueError("An interval ends before it starts")
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def total(spans: list[tuple[datetime, datetime]]) -> timedelta:
    return sum((end - start for start, end in merge_intervals(spans)), timedelta())


def supplier_timings(manifest: dict[str, Any]) -> dict[str, timedelta]:
    """Active time per supplier: each case's merged active time divided equally by its suppliers."""
    result: dict[str, timedelta] = {}
    for case in manifest["timings"]:
        spans = [(parse(i["started_at"]), parse(i["ended_at"])) for i in case["intervals"]]
        share = total(spans) / len(case["suppliers"])
        for supplier in case["suppliers"]:
            result[supplier] = result.get(supplier, timedelta()) + share
    return result


def agreement(pairs: list[tuple[str, str]]) -> dict[str, Any]:
    """`pairs` are (system verdict, auditor consensus label); overall and per-class rates."""
    if not pairs:
        return {
            "claims": 0,
            "overall": None,
            "by_system_verdict": {},
            "by_auditor_label": {},
            "confusion": {},
        }
    matches = sum(1 for system, label in pairs if system == label)

    def rate(key: int) -> dict[str, Any]:
        groups: dict[str, list[bool]] = defaultdict(list)
        for pair in pairs:
            groups[pair[key]].append(pair[0] == pair[1])
        return {
            k: {"claims": len(v), "agreement": sum(v) / len(v)} for k, v in sorted(groups.items())
        }

    return {
        "claims": len(pairs),
        "overall": matches / len(pairs),
        "by_system_verdict": rate(0),
        "by_auditor_label": rate(1),
        "confusion": {f"{s}->{label}": n for (s, label), n in sorted(Counter(pairs).items())},
    }


def consensus(labels: list[dict[str, Any]]) -> tuple[str | None, bool]:
    """Majority of independent auditors; (label, disputed). A tie is disputed, not resolved."""
    counts = Counter(item["label"] for item in labels)
    if not counts:
        return None, False
    (top, n), *rest = counts.most_common()
    if rest and rest[0][1] == n:
        return None, True
    return top, len(counts) > 1


def evaluate_accuracy(manifest: dict[str, Any], engine: Engine) -> dict[str, Any]:
    independent = {a["auditor_id"] for a in manifest["auditors"] if a["independent"]}
    unmet: list[str] = []
    suppliers = {s["supplier_ref"]: s for s in manifest["suppliers"]}
    cases = defaultdict(list)
    for s in manifest["suppliers"]:
        cases[s["case_ref"]].append(s["supplier_ref"])
    if len(suppliers) != 30:
        unmet.append(f"Only {len(suppliers)} of the 30 required suppliers are present.")
    if len(cases) != 6 or any(len(v) != 5 for v in cases.values()):
        unmet.append("The suppliers are not arranged as six cases of five suppliers.")
    if not independent:
        unmet.append("No independent human auditor is recorded.")
    by_claim: dict[str, list[dict[str, Any]]] = defaultdict(list)
    ignored = 0
    for label in manifest["labels"]:
        if label["auditor_id"] in independent and label["supplier_ref"] in suppliers:
            by_claim[label["claim_id"]].append(label)
        else:
            ignored += 1
    pairs: list[tuple[str, str]] = []
    disputed: list[str] = []
    claim_types: Counter[str] = Counter()
    label_classes: Counter[str] = Counter()
    with Session(engine) as db:
        wanted = {UUID(s["supplier_id"]) for s in suppliers.values()}
        system_claims = list(
            db.scalars(select(Claim).where(Claim.supplier_id.in_(wanted))) if wanted else []
        )
        for claim in system_claims:
            if str(claim.id) not in by_claim:
                continue
            latest = db.scalar(
                select(Assessment)
                .where(Assessment.claim_id == claim.id)
                .order_by(Assessment.created_at.desc(), Assessment.sequence.desc())
                .limit(1)
            )
            label, is_disputed = consensus(by_claim[str(claim.id)])
            if is_disputed:
                disputed.append(str(claim.id))
            if label is None or latest is None:
                continue
            pairs.append((latest.verdict, label))
            claim_types[claim.type] += 1
            label_classes[label] += 1
        unlabelled = sum(1 for c in system_claims if str(c.id) not in by_claim)
        modes = sorted({r.mode for r in db.scalars(select(VerificationRun))})
    if unlabelled:
        unmet.append(f"{unlabelled} evaluated claims have no independent human label.")
    missing_classes = [v for v in VERDICTS if label_classes[v] == 0]
    if missing_classes:
        unmet.append(
            f"No auditor label exists for verdict class(es): {', '.join(missing_classes)}."
        )
    missing_types = [t for t in CLAIM_TYPES if claim_types[t] == 0]
    if missing_types:
        unmet.append(f"No labelled claim of type(s): {', '.join(missing_types)}.")
    report = agreement(pairs)
    if unmet:
        status = "unmeasured"
    else:
        status = "passed" if (report["overall"] or 0) >= AGREEMENT_TARGET else "failed"
    return {
        "criterion": "SC-002",
        "status": status,
        "unmet": unmet,
        "target": AGREEMENT_TARGET,
        "agreement": report,
        "labels_ignored_not_independent": ignored,
        "disputed_claims": disputed,
        "label_classes": dict(label_classes),
        "labelled_claim_types": dict(claim_types),
        "run_modes_in_database": modes,
    }


def evaluate_timing(manifest: dict[str, Any]) -> dict[str, Any]:
    refs = {s["supplier_ref"] for s in manifest["suppliers"]}
    totals = supplier_timings(manifest)
    unmet: list[str] = []
    missing = sorted(refs - set(totals))
    if len(refs) != 30:
        unmet.append(f"Only {len(refs)} of the 30 required suppliers are present.")
    if missing:
        unmet.append(
            f"No observed timing for {len(missing)} supplier(s): {', '.join(missing[:10])}."
        )
    per_supplier = {ref: totals[ref].total_seconds() for ref in sorted(totals)}
    maximum = max(totals.values()) if totals else None
    waits = timedelta()
    unattended = timedelta()
    for case in manifest["timings"]:
        waits += total(
            [(parse(w["started_at"]), parse(w["ended_at"])) for w in case.get("excluded_waits", [])]
        )
        unattended += total(
            [
                (parse(w["started_at"]), parse(w["ended_at"]))
                for w in case.get("unattended_collection", [])
            ]
        )
    if unmet:
        status = "unmeasured"
    else:
        assert maximum is not None
        status = "passed" if all(t < PER_SUPPLIER_LIMIT for t in totals.values()) else "failed"
    return {
        "criterion": "SC-003",
        "status": status,
        "unmet": unmet,
        "per_supplier_seconds": per_supplier,
        "maximum_seconds": maximum.total_seconds() if maximum else None,
        "limit_seconds": PER_SUPPLIER_LIMIT.total_seconds(),
        "unattended_collection_seconds": unattended.total_seconds(),
        "excluded_wait_seconds": waits.total_seconds(),
    }


def evaluate(manifest_path: Path, engine: Engine) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    return {
        "executed_at": datetime.now(UTC).isoformat(),
        "profile": "local-free",
        "dataset": manifest["dataset"]["name"],
        "results": [evaluate_accuracy(manifest, engine), evaluate_timing(manifest)],
        "limitations": list(LIMITATIONS),
    }


def write_result(result: dict[str, Any], output: Path) -> Path:
    """Protected, dated result file; existing results are never overwritten."""
    output.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    target = output / f"evaluation-{stamp}.json"
    target.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    return target
