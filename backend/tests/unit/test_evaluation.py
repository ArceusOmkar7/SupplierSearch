"""Evaluation mechanics. No audit label or timing in this file is a real measurement.

Timing arithmetic and agreement maths run on abstract values to test the formulas only (disclosed
controls). The pipeline tests use the actual supplier list and prove the key honesty rule: with
no real independent labels or per-supplier timings, every criterion is `unmeasured`.
"""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from jsonschema import ValidationError
from sqlalchemy import create_engine
from support import licence_rows

from verisource.operations.evaluation import (
    agreement,
    consensus,
    evaluate,
    load_manifest,
    merge_intervals,
    supplier_timings,
    total,
)

T0 = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)


def minutes(n: int) -> datetime:
    return T0 + timedelta(minutes=n)


def test_overlapping_intervals_are_never_double_counted() -> None:
    spans = [(minutes(0), minutes(10)), (minutes(5), minutes(20)), (minutes(30), minutes(40))]
    assert merge_intervals(spans) == [(minutes(0), minutes(20)), (minutes(30), minutes(40))]
    assert total(spans) == timedelta(minutes=30)
    with pytest.raises(ValueError):
        merge_intervals([(minutes(5), minutes(1))])


def test_shared_case_time_is_divided_equally_across_the_cases_suppliers() -> None:
    manifest = {
        "timings": [
            {
                "case_ref": "C",
                "suppliers": ["a", "b", "c", "d", "e"],
                "intervals": [
                    {
                        "activity": "intake",
                        "started_at": minutes(0).isoformat(),
                        "ended_at": minutes(30).isoformat(),
                    },
                    {
                        "activity": "correction",
                        "started_at": minutes(20).isoformat(),
                        "ended_at": minutes(45).isoformat(),
                    },
                ],
            }
        ]
    }
    totals = supplier_timings(manifest)
    assert set(totals) == {"a", "b", "c", "d", "e"}
    assert all(value == timedelta(minutes=9) for value in totals.values())  # 45 min / 5


def test_agreement_is_reported_overall_and_by_verdict() -> None:
    pairs = [
        ("proven", "proven"),
        ("unproven", "unproven"),
        ("unproven", "proven"),
        ("contradicted", "contradicted"),
    ]
    report = agreement(pairs)
    assert report["overall"] == 0.75
    assert report["by_system_verdict"]["unproven"] == {"claims": 2, "agreement": 0.5}
    assert report["confusion"]["unproven->proven"] == 1
    assert agreement([])["overall"] is None


def test_split_auditors_are_a_dispute_not_a_resolved_label() -> None:
    assert consensus([{"label": "proven"}, {"label": "proven"}, {"label": "unproven"}]) == (
        "proven",
        True,
    )
    assert consensus([{"label": "proven"}, {"label": "unproven"}]) == (None, True)
    assert consensus([]) == (None, False)


def base_manifest(count: int) -> dict[str, object]:
    rows = licence_rows()[:count]
    return {
        "schema_version": 1,
        "dataset": {
            "name": "actual BIS licence-list suppliers, no labels or timings recorded",
            "created_at": datetime.now(UTC).isoformat(),
            "suppliers_expected": 30,
            "cases_expected": 6,
            "suppliers_per_case": 5,
        },
        "auditors": [],
        "suppliers": [
            {
                "supplier_ref": row.licence_no,
                "case_ref": f"case-{index // 5}",
                "case_id": str(uuid4()),
                "supplier_id": str(uuid4()),
                "source_records": ["bis-licences.manifest.json"],
            }
            for index, row in enumerate(rows)
        ],
        "labels": [],
        "timings": [],
    }


def test_without_real_labels_and_timings_every_criterion_is_unmeasured(
    test_database_url: str, tmp_path: Path
) -> None:
    for count in (5, 29):  # a five-supplier run cannot pass; neither can 29 of 30
        path = tmp_path / f"audit-{count}.json"
        path.write_text(json.dumps(base_manifest(count)), encoding="utf-8")
        engine = create_engine(test_database_url, hide_parameters=True)
        result = evaluate(path, engine)
        engine.dispose()
        statuses = {item["criterion"]: item for item in result["results"]}
        assert statuses["SC-002"]["status"] == "unmeasured"
        assert statuses["SC-003"]["status"] == "unmeasured"
        assert any("30 required suppliers" in reason for reason in statuses["SC-003"]["unmet"])
        assert any("No independent human auditor" in r for r in statuses["SC-002"]["unmet"])
        assert statuses["SC-003"]["maximum_seconds"] is None


def test_the_schema_rejects_model_generated_labels_and_non_human_auditors(tmp_path: Path) -> None:
    manifest = base_manifest(1)
    manifest["labels"] = [
        {
            "supplier_ref": "x", "claim_id": str(uuid4()), "claim_type": "manufacturer",
            "auditor_id": "model", "label": "proven", "rationale": "generated",
            "labelled_at": datetime.now(UTC).isoformat(), "source": "model",
        }
    ]  # fmt: skip
    path = tmp_path / "bad-labels.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValidationError):
        load_manifest(path)
    manifest["labels"] = []
    manifest["auditors"] = [
        {"auditor_id": "bot", "human": False, "independent": True, "independence_statement": "x"}
    ]
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValidationError):
        load_manifest(path)
