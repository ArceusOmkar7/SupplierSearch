"""Bounded, isolated PDF reading. Extracted certificate fields are never proof by themselves."""

import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Any

from verisource.models.ollama import ModelUnavailable, chunk_pages
from verisource.models.router import ModelRouter
from verisource.models.schemas import CertificateExtraction, Located, verify_certificate

MAX_BYTES = 20 * 1024 * 1024
MAX_PAGES = 50
PARSE_TIMEOUT_SECONDS = 60


@dataclass(frozen=True)
class PdfInspection:
    page_count: int | None
    text_pages: list[int] = field(default_factory=list)
    scanned_pages: list[int] = field(default_factory=list)
    pages: dict[int, str] = field(default_factory=dict)
    failure_reason: str | None = None


def inspect_pdf(content: bytes) -> PdfInspection:
    """Parse in a child process with no secrets or network-bound configuration."""
    if len(content) > MAX_BYTES:
        return PdfInspection(None, failure_reason="too_large")
    environment = {key: os.environ[key] for key in ("SYSTEMROOT", "PATH") if key in os.environ}
    try:
        completed = subprocess.run(
            [sys.executable, "-I", "-m", "verisource.documents.pdf_worker"],
            input=content,
            capture_output=True,
            timeout=PARSE_TIMEOUT_SECONDS,
            env=environment,
            check=False,
        )
        data = json.loads(completed.stdout)
    except subprocess.TimeoutExpired, ValueError, OSError:
        return PdfInspection(None, failure_reason="malformed_document")
    return PdfInspection(
        page_count=data["page_count"],
        text_pages=data["text_pages"],
        scanned_pages=data["scanned_pages"],
        pages={int(page): text for page, text in data["pages"].items()},
        failure_reason=data["failure_reason"],
    )


# ---- field extraction ---------------------------------------------------------------------

SCHEMA_VERSION = "certificate-v1"
_INSTRUCTIONS = (
    "Read this certificate or licence text. Extract the certificate number, issuer, standard, "
    "scope, site address, issue date and expiry date. Quote exact text and the page number."
)
_STANDARD = re.compile(r"\b(?:IS|ISO|IEC|EN|BS)\s?\d{2,6}(?:[:\-]\d{2,4})?(?:\s?\(Part\s?\d+\))?")
_EXPIRY = re.compile(
    r"(?:valid\s*(?:until|upto|up\s*to|till)|expiry\s*date|expires?\s*on|date\s*of\s*expiry)"
    r"\s*[:\-]?\s*(\d{1,2}[./-]\d{1,2}[./-]\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}\s+[A-Za-z]+\s+\d{4})",
    re.IGNORECASE,
)
_ISSUE = re.compile(
    r"(?:date\s*of\s*issue|issued\s*on|issue\s*date|date\s*of\s*grant)"
    r"\s*[:\-]?\s*(\d{1,2}[./-]\d{1,2}[./-]\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}\s+[A-Za-z]+\s+\d{4})",
    re.IGNORECASE,
)
_VALID_RANGE = re.compile(
    r"valid\s*[:\-]?\s*(\d{1,2}\s+[A-Za-z]+\s+\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}[./-]\d{1,2}[./-]\d{4})"
    r"\s*[–—-]\s*"
    r"(\d{1,2}\s+[A-Za-z]+\s+\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}[./-]\d{1,2}[./-]\d{4})",
    re.IGNORECASE,
)
_NUMBER = re.compile(
    r"(?:certificate|licen[cs]e|registration|cm/l)\s*(?:no\.?|number)\s*[:\-]?\s*([A-Z0-9][A-Z0-9/\-]{3,})",
    re.IGNORECASE,
)


def ocr_available() -> bool:
    return shutil.which("tesseract") is not None


def rule_extract(pages: dict[int, str]) -> CertificateExtraction:
    """Deterministic, quotation-backed extraction; ambiguity stays unknown."""
    found: dict[str, Located] = {}
    for number, text in sorted(pages.items()):
        flat = " ".join(text.split())
        for name, pattern, group in (
            ("certificate_number", _NUMBER, 1),
            ("expiry_date", _EXPIRY, 1),
            ("issue_date", _ISSUE, 1),
            ("standard", _STANDARD, 0),
        ):
            match = pattern.search(flat)
            if name in {"issue_date", "expiry_date"} and name not in found:
                span = _VALID_RANGE.search(flat)
                if span:
                    group = 1 if name == "issue_date" else 2
                    found[name] = Located(
                        value=span.group(group), page=number, quote=span.group(0)[:400]
                    )
                    continue
            if match and name not in found:
                found[name] = Located(
                    value=match.group(group)[:400], page=number, quote=match.group(0)[:400]
                )
    return CertificateExtraction(**found)  # type: ignore[arg-type]


def extract_certificate(
    router: ModelRouter | None, inspection: PdfInspection
) -> tuple[CertificateExtraction, str, list[str]]:
    """Return (verified fields, method label, missing field names). Never a verdict."""
    notes: list[str] = []
    for page in inspection.scanned_pages:
        notes.append(
            f"page {page}: scanned image"
            + ("" if ocr_available() else "; OCR is unavailable, content unread")
        )
    base = rule_extract(inspection.pages)
    method = "rule"
    merged: dict[str, Any] = {
        k: v for k, v in base.model_dump().items() if v and k != "uncertainties"
    }
    if router is not None and inspection.pages:
        try:
            for chunk in chunk_pages(inspection.pages):
                proposal, backend = router.extract(
                    CertificateExtraction,
                    _INSTRUCTIONS,
                    "\n\n".join(f"[page {n}]\n{t}" for n, t in chunk.items()),
                    data_class="unknown",
                )
                method = f"model:{backend}"
                for key, value in proposal.model_dump().items():
                    if key == "uncertainties":
                        notes.extend(value)
                    elif value and key not in merged:
                        merged[key] = value
        except ModelUnavailable as exc:
            notes.append(f"model unavailable: {exc}")
    checked = verify_certificate(
        CertificateExtraction.model_validate(merged),
        inspection.pages,
    )
    names = (
        "certificate_number",
        "holder_name",
        "issuer",
        "standard",
        "scope",
        "site_address",
        "issue_date",
        "expiry_date",
    )
    missing = [name for name in names if getattr(checked, name) is None]
    checked.uncertainties.extend(notes)
    return checked, method, missing
