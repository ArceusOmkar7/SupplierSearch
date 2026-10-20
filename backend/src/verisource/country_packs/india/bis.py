"""BIS Quality Control Order catalogue ingestion and product-applicability candidates.

The captured Scheme-I page lists IS numbers, products and order notifications; the linked
order PDFs (scope, exemptions, implementation dates) are not read here, so coverage is
`partial`. An absent catalogue hit never establishes non-applicability, and blocked current
licence lookups remain gaps.
"""

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from bs4 import BeautifulSoup, Tag
from sqlalchemy import select
from sqlalchemy.orm import Session

from verisource.db.models import QcoRecord, SourceDataset
from verisource.sources.manifests import load_record
from verisource.storage.filesystem import PrivateFileStore

SCHEMA_VERSION = "bis-qco-scheme1-v1"
_IS_CODE = re.compile(r"\bIS\s*(\d{2,6})(?:\s*\((?:Part|PART)\s*([\w/]+)\))?", re.IGNORECASE)
_ORDER_NUMBER = re.compile(r"S\.?\s?O\.?\s*(?:No\.?)?\s*(\d{1,5})\s*\(?\s*E?\s*\)?", re.IGNORECASE)
_MONTHS = {
    name: number
    for number, names in enumerate(
        [
            ("jan", "january"),
            ("feb", "february"),
            ("mar", "march"),
            ("apr", "april"),
            ("may",),
            ("jun", "june"),
            ("jul", "july"),
            ("aug", "august"),
            ("sep", "sept", "september"),
            ("oct", "october"),
            ("nov", "november"),
            ("dec", "december"),
        ],
        start=1,
    )
    for name in names
}
_DATE = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)?[\s./-]+(\d{1,2}|[A-Za-z]{3,9})[\s./-]+(\d{4})\b")


@dataclass(frozen=True)
class QcoCandidate:
    order_number: str
    standard_codes: list[str]
    product_scope: str
    issued_on: datetime | None
    coverage_state: str
    basis: str


def find_dates(text: str) -> list[datetime]:
    dates: list[datetime] = []
    for day, month, year in _DATE.findall(text):
        number = int(month) if month.isdigit() else _MONTHS.get(month.casefold())
        try:
            if number:
                dates.append(datetime(int(year), number, int(day), tzinfo=UTC))
        except ValueError:
            continue
    return dates


def standard_codes(text: str) -> list[str]:
    codes = []
    for number, part in _IS_CODE.findall(text):
        codes.append(f"IS {number}" + (f" (Part {part})" if part else ""))
    return sorted(set(codes))


def _cells(row: Tag) -> list[Tag]:
    return [c for c in row.find_all(["th", "td"]) if isinstance(c, Tag)]


def parse_scheme1(html: bytes) -> list[dict[str, Any]]:
    """Rows of the Scheme-I table, resolving the notification cell's rowspan inheritance."""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if not isinstance(table, Tag):
        return []
    category = ""
    carried_text, carried_remaining = "", 0
    records: list[dict[str, Any]] = []
    for index, row in enumerate(table.find_all("tr"), start=1):
        cells = _cells(row)
        if len(cells) == 1:
            category = " ".join(cells[0].get_text(" ").split())
            carried_text, carried_remaining = "", 0
            continue
        if len(cells) < 3 or cells[1].get_text(strip=True).upper().startswith("IS NO"):
            continue
        codes_text = " ".join(cells[1].get_text(" ").split())
        product = " ".join(cells[2].get_text(" ").split())
        if len(cells) >= 4:
            notification = " ".join(cells[3].get_text(" ").split())
            span = int(str(cells[3].get("rowspan", "1")) or 1)
            carried_text, carried_remaining = notification, span - 1
            links = [str(a["href"]) for a in cells[3].find_all("a", href=True)]
        else:
            notification = carried_text if carried_remaining > 0 else ""
            carried_remaining = max(carried_remaining - 1, 0)
            links = []
        records.append(
            {
                "locator": f"table 1, row {index}",
                "category": category,
                "is_codes_text": codes_text,
                "product": product,
                "notification": notification,
                "links": links,
            }
        )
    return records


def ingest_qco_catalog(
    db: Session, store: PrivateFileStore, manifest_path: Path, *, records_root: Path | None = None
) -> tuple[SourceDataset, int]:
    manifest, content = load_record(manifest_path, records_root)
    existing = db.scalar(
        select(SourceDataset).where(
            SourceDataset.sha256 == manifest["sha256"],
            SourceDataset.schema_version == SCHEMA_VERSION,
        )
    )
    if existing is not None:
        return existing, existing.imported_count
    rows = parse_scheme1(content)
    dataset_id = uuid4()
    stored = store.put(dataset_id, content)
    dataset = SourceDataset(
        id=dataset_id,
        source_version=f"{manifest['publisher']}@{manifest['obtained_at']}",
        publisher=manifest["publisher"],
        original_url=manifest["original_url"],
        licence_attribution=f"{manifest['rights']} | {manifest['attribution']}",
        obtained_at=datetime.fromisoformat(manifest["obtained_at"]),
        publication_cutoff=None
        if manifest["publication_cutoff"] is None
        else datetime.fromisoformat(manifest["publication_cutoff"]),
        cutoff_unknown_reason=manifest["cutoff_unknown_reason"],
        coverage=manifest["coverage"],
        local_storage_key=stored.storage_key,
        sha256=stored.sha256,
        format="html",
        schema_version=SCHEMA_VERSION,
        state="imported" if rows else "quarantined",
        imported_count=len(rows),
        quarantined_count=0,
        imported_at=datetime.now(UTC),
    )
    db.add(dataset)
    db.flush()
    for row in rows:
        notification = row["notification"]
        dates = find_dates(notification)
        order = _ORDER_NUMBER.search(notification)
        db.add(
            QcoRecord(
                source_document_id=dataset.id,
                order_number=(f"S.O. {order.group(1)}(E)" if order else notification[:120])
                or "unstated",
                standard_codes=standard_codes(row["is_codes_text"]) or [row["is_codes_text"]],
                product_scope=f"{row['category']} — {row['product']}",
                exclusions=[],
                issued_on=dates[0] if dates else None,
                effective_on=None,  # Implementation dates live in the unread order PDFs.
                amended_on=[d.date().isoformat() for d in dates[1:]],
                supersedes_ref=None,
                coverage_state="partial",
                extracted_basis=f"{row['locator']}: {notification[:400]}",
            )
        )
    db.flush()
    return dataset, len(rows)


def applicability_candidates(
    db: Session, *, standards: list[str], product_text: str
) -> list[QcoCandidate]:
    """Candidate orders by exact IS number or product phrase; never a non-applicability proof."""
    wanted = {code.upper().replace(" ", "") for s in standards for code in standard_codes(s)}
    needle = " ".join(product_text.casefold().split())
    candidates: list[QcoCandidate] = []
    for record in db.scalars(select(QcoRecord)):
        record_codes = {code.upper().replace(" ", "") for code in record.standard_codes}
        product = " ".join(record.product_scope.casefold().split())
        by_code = bool(wanted & record_codes)
        by_phrase = bool(needle) and len(needle) >= 6 and needle in product
        if by_code or by_phrase:
            candidates.append(
                QcoCandidate(
                    order_number=record.order_number,
                    standard_codes=list(record.standard_codes),
                    product_scope=record.product_scope,
                    issued_on=record.issued_on,
                    coverage_state=record.coverage_state,
                    basis=record.extracted_basis,
                )
            )
    return candidates
