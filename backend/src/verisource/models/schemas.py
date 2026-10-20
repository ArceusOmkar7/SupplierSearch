"""Model output contracts. Output is a proposal: every value must quote its source text.

A value whose quote cannot be found verbatim on the cited page is dropped into
`uncertainties`; a schema-valid answer is never trusted as a citation or a verdict.
"""

import re
from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

Short = Annotated[str, Field(max_length=400)]


class Located(BaseModel):
    """One extracted value with the page and exact quotation that support it."""

    model_config = ConfigDict(extra="forbid")
    value: Short
    page: int = Field(ge=1)
    quote: Short


class CertificateExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    certificate_number: Located | None = None
    holder_name: Located | None = None
    issuer: Located | None = None
    standard: Located | None = None
    scope: Located | None = None
    site_address: Located | None = None
    issue_date: Located | None = None
    expiry_date: Located | None = None
    uncertainties: list[Short] = Field(default_factory=list)


class SupplierMention(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Short
    quote: Short


class RequirementInterpretation(BaseModel):
    """Draft-only reading of buyer text; the buyer edits and explicitly confirms it."""

    model_config = ConfigDict(extra="forbid")
    part_description: Located | None = None
    materials: list[Located] = Field(default_factory=list)
    processes: list[Located] = Field(default_factory=list)
    certifications: list[Located] = Field(default_factory=list)
    standards: list[Located] = Field(default_factory=list)
    suppliers: list[SupplierMention] = Field(default_factory=list)
    uncertainties: list[Short] = Field(default_factory=list)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def quote_supported(quote: str, page_text: str | None) -> bool:
    """True only when the quotation occurs verbatim (whitespace/case-insensitive)."""
    return (
        bool(quote.strip()) and page_text is not None and _normalize(quote) in _normalize(page_text)
    )


def verify_located(
    item: Located | None, pages: dict[int, str], label: str, uncertainties: list[str]
) -> Located | None:
    if item is None:
        return None
    if quote_supported(item.quote, pages.get(item.page)):
        return item
    uncertainties.append(f"{label}: quotation not found on page {item.page}; value discarded")
    return None


def verify_certificate(
    extraction: CertificateExtraction, pages: dict[int, str]
) -> CertificateExtraction:
    notes = list(extraction.uncertainties)
    checked = {
        name: verify_located(getattr(extraction, name), pages, name, notes)
        for name in (
            "certificate_number",
            "holder_name",
            "issuer",
            "standard",
            "scope",
            "site_address",
            "issue_date",
            "expiry_date",
        )
    }
    # Dates must parse; a malformed date stays unknown rather than being guessed.
    for name in ("issue_date", "expiry_date"):
        located = checked[name]
        if located is not None and parse_date(located.value) is None:
            notes.append(f"{name}: unreadable date; left unknown")
            checked[name] = None
    return CertificateExtraction(**checked, uncertainties=notes)


_DATE_FORMATS = (
    "%Y-%m-%d",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%d.%m.%Y",
    "%d %B %Y",
    "%d %b %Y",
    "%B %d, %Y",
)


def parse_date(value: str) -> date | None:
    from datetime import datetime

    text = value.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None
