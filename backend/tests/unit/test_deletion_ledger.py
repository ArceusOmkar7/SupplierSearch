"""Deletion journal durability and tamper detection (random case UUIDs only; no real content)."""

import threading
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from verisource.storage.deletion_ledger import DeletionLedger, LedgerUnavailable


@pytest.fixture
def ledger(tmp_path: Path) -> DeletionLedger:
    return DeletionLedger.initialize(tmp_path / "ledger" / "deletions.jsonl", str(uuid4()))


def test_tombstones_are_sequenced_idempotent_and_track_progress(ledger: DeletionLedger) -> None:
    first, second = uuid4(), uuid4()
    one = ledger.append_tombstone(first, 3)
    two = ledger.append_tombstone(second, 1)
    assert (one, two) == (1, 2)
    assert ledger.append_tombstone(first, 9) == 1  # a retry never writes a second tombstone
    assert ledger.tombstoned() == {first, second}
    state = ledger.states()[first]
    assert state.write_generation == 3 and not state.complete
    ledger.record_progress(one, active_purge_completed_at=datetime.now(UTC))
    assert not ledger.states()[first].complete
    ledger.record_progress(one, managed_snapshots_purged_at=datetime.now(UTC))
    assert ledger.states()[first].complete and not ledger.states()[second].complete


def test_entries_never_contain_owner_or_content_fields(ledger: DeletionLedger) -> None:
    ledger.append_tombstone(uuid4(), 1)
    text = ledger.path.read_text(encoding="utf-8")
    for forbidden in ("owner", "title", "evidence", "email", "text"):
        assert forbidden not in text.lower().replace("random_case_uuid", "")


def test_missing_edited_reordered_or_truncated_ledgers_fail_closed(
    ledger: DeletionLedger, tmp_path: Path
) -> None:
    for _ in range(3):
        ledger.append_tombstone(uuid4(), 1)
    original = ledger.path.read_text(encoding="utf-8")
    lines = original.splitlines()

    def broken(content: str) -> DeletionLedger:
        path = tmp_path / "broken.jsonl"
        path.write_text(content, encoding="utf-8")
        return DeletionLedger(path)

    with pytest.raises(LedgerUnavailable):
        DeletionLedger(tmp_path / "absent.jsonl").verify()
    edited = lines.copy()
    edited[2] = edited[2].replace('"write_generation": 1', '"write_generation": 7')
    with pytest.raises(LedgerUnavailable):
        broken("\n".join(edited) + "\n").verify()
    with pytest.raises(LedgerUnavailable):  # reordered entries break the hash chain
        broken("\n".join([lines[0], lines[2], lines[1], lines[3]]) + "\n").verify()
    with pytest.raises(LedgerUnavailable):  # a partial last entry
        broken(original[:-20]).verify()
    with pytest.raises(LedgerUnavailable):  # a removed middle entry
        broken("\n".join([lines[0], lines[1], lines[3]]) + "\n").verify()
    assert DeletionLedger(ledger.path).verify() == 3  # the genuine file is still valid
    with pytest.raises(LedgerUnavailable):
        broken("").verify()


def test_legacy_header_without_chain_fields_is_accepted_and_extended(tmp_path: Path) -> None:
    path = tmp_path / "legacy.jsonl"
    path.write_text(
        '{"type": "ledger_initialized", "schema_version": 1, "installation_id": "x", '
        '"created_at": "2026-01-01T00:00:00+00:00"}\n',
        encoding="utf-8",
    )
    ledger = DeletionLedger(path)
    assert ledger.verify() == 0
    ledger.append_tombstone(uuid4(), 1)
    assert DeletionLedger(path).verify() == 1


def test_concurrent_appends_stay_contiguous(ledger: DeletionLedger) -> None:
    errors: list[Exception] = []

    def work() -> None:
        try:
            ledger.append_tombstone(uuid4(), 1)
        except Exception as exc:  # noqa: BLE001 -- surfaced by the assertion below
            errors.append(exc)

    threads = [threading.Thread(target=work) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(60)
    assert not errors
    assert ledger.verify() == 8 and len(ledger.tombstoned()) == 8
