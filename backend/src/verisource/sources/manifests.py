"""Provenance-checked genuine capture manifests; missing or altered bytes raise, never default."""

import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from verisource.config import REPO_ROOT

SCHEMA_PATH = REPO_ROOT / "tests/records/manifest.schema.json"
DEFAULT_RECORDS_ROOT = REPO_ROOT / ".local/records"


def load_record(
    manifest_path: Path, records_root: Path | None = None
) -> tuple[dict[str, Any], bytes]:
    """Validate the manifest schema, containment and original-byte hash; return the capture."""
    root = (records_root or DEFAULT_RECORDS_ROOT).resolve()
    manifest_path = manifest_path.resolve(strict=True)
    if not manifest_path.is_relative_to(root):
        raise ValueError("Manifest outside protected records root")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(manifest)
    relative = Path(manifest["file"])
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("Record file must be a contained relative path")
    source = (manifest_path.parent / relative).resolve(strict=True)
    if not source.is_relative_to(root):
        raise ValueError("Source bytes outside protected records root")
    content = source.read_bytes()
    if hashlib.sha256(content).hexdigest() != manifest["sha256"]:
        raise ValueError("Source bytes do not match original capture hash")
    return manifest, content
