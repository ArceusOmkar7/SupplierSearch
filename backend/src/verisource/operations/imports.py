"""Operator-local dataset import. Never an arbitrary-path buyer API, never seeds data."""

from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from verisource.config import Settings
from verisource.country_packs.india.bis import ingest_qco_catalog
from verisource.db.session import create_database_engine
from verisource.sources.imports import import_source_dataset
from verisource.sources.manifests import load_record
from verisource.storage.filesystem import PrivateFileStore


def run_import(settings: Settings, manifest_path: Path, *, kind: str = "auto") -> dict[str, Any]:
    """Import one genuine capture. Missing, altered or provenance-incomplete input raises."""
    manifest, _content = load_record(manifest_path)  # Schema, containment and hash checked.
    if kind == "auto":
        kind = "bis-qco" if any("QCO" in c for c in manifest["coverage"]) else "tabular"
    store = PrivateFileStore(settings.data_root / "corpus")
    engine = create_database_engine(settings)
    try:
        with Session(engine) as db, db.begin():
            if kind == "bis-qco":
                dataset, count = ingest_qco_catalog(db, store, manifest_path)
                return {
                    "kind": kind,
                    "dataset_id": str(dataset.id),
                    "imported": count,
                    "quarantined": 0,
                    "publication_cutoff": None,
                    "coverage_state": "partial",
                    "issues": ["Linked order PDFs were not read."],
                }
            result = import_source_dataset(db, store, manifest_path)
            return {
                "kind": kind,
                "dataset_id": str(result.dataset_id),
                "imported": result.imported,
                "quarantined": result.quarantined,
                "publication_cutoff": manifest["publication_cutoff"],
                "issues": result.issues[:20],
            }
    finally:
        engine.dispose()
