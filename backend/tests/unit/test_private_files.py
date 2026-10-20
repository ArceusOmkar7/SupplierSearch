"""Storage boundary checks using a genuine saved official PDF; no generated documents."""

from pathlib import Path
from uuid import uuid4

import pytest
from records import load_record

from verisource.storage.filesystem import PrivateFileStore


@pytest.mark.real_records
def test_real_document_round_trip_and_case_scoped_delete(tmp_path: Path) -> None:
    manifest, content = load_record(Path(".local/records/bis-licences.manifest.json"))
    store = PrivateFileStore(tmp_path / "private")
    first, second = uuid4(), uuid4()  # Storage namespaces are test control metadata.
    saved = store.put(first, content)
    retained = store.put(second, content)
    assert saved.sha256 == manifest["sha256"]
    assert store.read(saved.storage_key, saved.sha256) == content
    assert store.list(first) == [saved.storage_key]
    store.delete(saved.storage_key)
    store.delete(saved.storage_key)
    assert store.list(first) == []
    assert store.read(retained.storage_key, retained.sha256) == content
    assert not tuple(store.root.rglob("*.part"))


@pytest.mark.parametrize("key", ["../.env", "/etc/passwd", "case/artifact", "a/b/c", "a\\b"])
def test_invalid_paths_never_reach_filesystem(tmp_path: Path, key: str) -> None:
    store = PrivateFileStore(tmp_path / "private")
    with pytest.raises(ValueError):
        store.read(key)
    with pytest.raises(ValueError):
        store.delete(key)


@pytest.mark.real_records
def test_hash_mismatch_rejected(tmp_path: Path) -> None:
    _manifest, content = load_record(Path(".local/records/bis-licences.manifest.json"))
    store = PrivateFileStore(tmp_path / "private")
    saved = store.put(uuid4(), content)
    with pytest.raises(ValueError, match="hash mismatch"):
        store.read(saved.storage_key, "0" * 64)  # Invalid control hash, not source truth.
