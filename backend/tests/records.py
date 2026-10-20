"""Read genuine captures only after schema, containment and byte-hash verification."""

from verisource.config import REPO_ROOT
from verisource.sources.manifests import SCHEMA_PATH, load_record

__all__ = ["REPO_ROOT", "SCHEMA_PATH", "load_record"]
