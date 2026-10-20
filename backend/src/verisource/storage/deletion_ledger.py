"""Append-only, fsynced deletion tombstone journal that lives outside snapshot restore.

Each line is a JSON entry chained to the previous one by SHA-256, so edits, reordering and
mid-file truncation are detected. Entries hold only a random case UUID, a write generation and
timestamps: never an owner identity, title, input or evidence. A missing or inconsistent
ledger fails closed; callers must not serve or restore cases without a verified ledger.
"""

import hashlib
import json
import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

GENESIS = "0" * 64
_LOCAL = threading.Lock()


class LedgerUnavailable(RuntimeError):
    """The ledger is missing or inconsistent; deletion state cannot be trusted."""


@dataclass(frozen=True)
class TombstoneState:
    sequence: int
    case_uuid: UUID
    write_generation: int
    accepted_at: str
    active_purge_completed_at: str | None
    managed_snapshots_purged_at: str | None

    @property
    def complete(self) -> bool:
        return (
            self.active_purge_completed_at is not None
            and self.managed_snapshots_purged_at is not None
        )


def _digest(previous: str, body: dict[str, Any]) -> str:
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256((previous + canonical).encode("utf-8")).hexdigest()


class DeletionLedger:
    def __init__(self, path: Path) -> None:
        self.path = path

    # ---- reading and verification -------------------------------------------------------

    def _read(self) -> tuple[list[dict[str, Any]], str]:
        try:
            raw = self.path.read_text(encoding="utf-8")
        except OSError as exc:
            raise LedgerUnavailable("The deletion ledger is missing or unreadable") from exc
        if raw and not raw.endswith("\n"):
            raise LedgerUnavailable("The deletion ledger ends with a partial entry")
        entries: list[dict[str, Any]] = []
        previous = GENESIS
        for number, line in enumerate(raw.splitlines(), start=1):
            try:
                entry = json.loads(line)
            except ValueError as exc:
                raise LedgerUnavailable(f"Ledger line {number} is malformed") from exc
            if (
                number == 1
                and "entry_hash" not in entry
                and entry.get("type") == "ledger_initialized"
            ):
                previous = _digest(GENESIS, entry)  # Header written before chaining existed.
                entries.append(entry)
                continue
            try:
                stored = entry.pop("entry_hash")
                chained = entry.pop("previous_hash")
            except KeyError as exc:
                raise LedgerUnavailable(f"Ledger line {number} is malformed") from exc
            if chained != previous or _digest(previous, entry) != stored:
                raise LedgerUnavailable(f"Ledger line {number} fails verification")
            previous = stored
            entries.append(entry)
        if not entries or entries[0].get("type") != "ledger_initialized":
            raise LedgerUnavailable("The deletion ledger has no initialization entry")
        return entries, previous

    def _lines(self) -> list[dict[str, Any]]:
        return self._read()[0]

    @classmethod
    def initialize(cls, path: Path, installation_id: str) -> DeletionLedger:
        """Create a new ledger; refuses to touch an existing one."""
        path.parent.mkdir(parents=True, exist_ok=True)
        body = {
            "type": "ledger_initialized",
            "schema_version": 1,
            "installation_id": installation_id,
            "created_at": datetime.now(UTC).isoformat(),
        }
        record = {**body, "previous_hash": GENESIS, "entry_hash": _digest(GENESIS, body)}
        with path.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(record) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        return cls(path)

    def verify(self) -> int:
        """Return the highest tombstone sequence after checking chain and ordering."""
        highest = 0
        for entry in self._lines():
            if entry["type"] == "tombstone":
                if entry["sequence"] != highest + 1:
                    raise LedgerUnavailable("Tombstone sequence has a gap or repeats")
                highest = entry["sequence"]
        return highest

    def states(self) -> dict[UUID, TombstoneState]:
        self.verify()
        states: dict[UUID, TombstoneState] = {}
        by_sequence: dict[int, UUID] = {}
        for entry in self._lines():
            if entry["type"] == "tombstone":
                case = UUID(entry["random_case_uuid"])
                by_sequence[entry["sequence"]] = case
                states[case] = TombstoneState(
                    entry["sequence"],
                    case,
                    entry["write_generation"],
                    entry["accepted_at"],
                    None,
                    None,
                )
            elif entry["type"] == "progress":
                case = by_sequence[entry["sequence"]]
                current = states[case]
                states[case] = TombstoneState(
                    current.sequence,
                    case,
                    current.write_generation,
                    current.accepted_at,
                    entry.get("active_purge_completed_at") or current.active_purge_completed_at,
                    entry.get("managed_snapshots_purged_at") or current.managed_snapshots_purged_at,
                )
        return states

    def tombstoned(self) -> set[UUID]:
        return set(self.states())

    # ---- appending ----------------------------------------------------------------------

    def _append(self, build: Callable[[list[dict[str, Any]]], dict[str, Any] | None]) -> int | None:
        """Verify, build the next entry from the verified history and fsync it, atomically."""
        with _LOCAL, _FileLock(self.path.with_suffix(".lock")):
            entries, previous = self._read()  # Verify before every append.
            body = build(entries)
            if body is None:
                return None
            record = {**body, "previous_hash": previous}
            record["entry_hash"] = _digest(previous, body)
            descriptor = os.open(self.path, os.O_WRONLY | os.O_APPEND)
            try:
                os.write(
                    descriptor, (json.dumps(record, ensure_ascii=False) + "\n").encode("utf-8")
                )
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            return int(body.get("sequence", 0))

    def append_tombstone(self, case_uuid: UUID, write_generation: int) -> int:
        """Durably record an accepted deletion; idempotent per case. Returns its sequence."""
        found: list[int] = []

        def build(entries: list[dict[str, Any]]) -> dict[str, Any] | None:
            tombstones = [e for e in entries if e["type"] == "tombstone"]
            for entry in tombstones:
                if entry["random_case_uuid"] == str(case_uuid):
                    found.append(entry["sequence"])
                    return None
            return {
                "type": "tombstone",
                "sequence": len(tombstones) + 1,
                "random_case_uuid": str(case_uuid),
                "write_generation": write_generation,
                "accepted_at": datetime.now(UTC).isoformat(),
            }

        written = self._append(build)
        return written if written is not None else found[0]

    def record_progress(
        self,
        sequence: int,
        *,
        active_purge_completed_at: datetime | None = None,
        managed_snapshots_purged_at: datetime | None = None,
    ) -> None:
        self._append(
            lambda _entries: {
                "type": "progress",
                "sequence": sequence,
                "active_purge_completed_at": active_purge_completed_at.isoformat()
                if active_purge_completed_at
                else None,
                "managed_snapshots_purged_at": managed_snapshots_purged_at.isoformat()
                if managed_snapshots_purged_at
                else None,
            }
        )


class _FileLock:
    """Cross-process lock via an exclusively created file; stale locks expire."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def __enter__(self) -> None:
        deadline = time.monotonic() + 30
        while True:
            try:
                descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(descriptor)
                return
            except FileExistsError:
                try:
                    if time.time() - self.path.stat().st_mtime > 30:
                        self.path.unlink(missing_ok=True)
                        continue
                except OSError:
                    pass
                if time.monotonic() > deadline:
                    raise LedgerUnavailable("The deletion ledger is locked") from None
                time.sleep(0.02)

    def __exit__(self, *_exc: object) -> None:
        self.path.unlink(missing_ok=True)
