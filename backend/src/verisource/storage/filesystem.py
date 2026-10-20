"""Atomic immutable case files; generated keys only, with containment and link checks."""

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4


@dataclass(frozen=True)
class StoredFile:
    storage_key: str
    sha256: str
    byte_count: int


class PrivateFileStore:
    """Callers authorize cases before access; this class never accepts client filenames."""

    def __init__(self, root: Path) -> None:
        absolute = root.absolute()
        self._reject_links(absolute)
        absolute.mkdir(parents=True, exist_ok=True)
        self.root = absolute.resolve(strict=True)

    @staticmethod
    def _reject_links(path: Path) -> None:
        for item in (path, *path.parents):
            if item.is_symlink() or item.is_junction():
                raise ValueError("Linked storage paths are forbidden")

    def _path(self, key: str) -> Path:
        parts = key.split("/")
        if len(parts) != 2 or any(str(UUID(part)) != part for part in parts):
            raise ValueError("Storage key must contain canonical case/artifact UUIDs")
        candidate = self.root / parts[0] / parts[1]
        self._reject_links(candidate)
        if not candidate.resolve().is_relative_to(self.root):
            raise ValueError("Storage key escaped the private root")
        return candidate

    def put(self, case_id: UUID, content: bytes) -> StoredFile:
        key = f"{case_id}/{uuid4()}"
        target = self._path(key)
        target.parent.mkdir(exist_ok=True)
        self._reject_links(target.parent)
        temporary = target.with_suffix(".part")
        try:
            with temporary.open("xb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            self._reject_links(target)
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
        return StoredFile(key, hashlib.sha256(content).hexdigest(), len(content))

    def read(self, key: str, expected_hash: str | None = None) -> bytes:
        content = self._path(key).read_bytes()
        if expected_hash is not None and hashlib.sha256(content).hexdigest() != expected_hash:
            raise ValueError("Stored content hash mismatch")
        return content

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)

    def list(self, case_id: UUID) -> list[str]:
        directory = self.root / str(case_id)
        self._reject_links(directory)
        if not directory.exists():
            return []
        keys = []
        for file in directory.iterdir():
            if file.suffix == ".part":
                continue
            key = f"{case_id}/{file.name}"
            path = self._path(key)
            if not path.is_file():
                raise ValueError("Unexpected entry in private case storage")
            keys.append(key)
        return sorted(keys)
