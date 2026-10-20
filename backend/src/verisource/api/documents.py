"""Private PDF upload, metadata and authorized content streaming (no public URL)."""

import re
from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from sqlalchemy import select

from verisource.api.dependencies import (
    Database,
    MutationSession,
    SignedIn,
    owned_case,
    owned_child,
)
from verisource.api.errors import reject
from verisource.db.models import DocumentArtifact, RequirementRevision, Supplier
from verisource.documents.certificates import MAX_BYTES, inspect_pdf
from verisource.domain.commands import append_event
from verisource.orchestration.jobs import enqueue
from verisource.storage.filesystem import PrivateFileStore

router = APIRouter(prefix="/api/v1")


def present_document(document: DocumentArtifact) -> dict[str, Any]:
    return {
        "id": str(document.id),
        "case_id": str(document.case_id),
        "revision_id": str(document.revision_id) if document.revision_id else None,
        "supplier_id": str(document.supplier_id) if document.supplier_id else None,
        "origin": document.origin,
        "sha256": document.sha256,
        "media_type": document.media_type,
        "byte_count": document.byte_count,
        "page_count": document.page_count,
        "state": document.state,
        "state_reason": document.state_reason,
        "collected_at": document.collected_at.isoformat(),
        "source_url": document.source_url,
    }


async def read_limited(upload: UploadFile) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while chunk := await upload.read(1024 * 1024):
        total += len(chunk)
        if total > MAX_BYTES:
            raise reject(413, "file_too_large", "PDF files are limited to 20 MiB.")
        chunks.append(chunk)
    return b"".join(chunks)


@router.post("/cases/{case_id}/documents", status_code=202)
def upload_document(
    case_id: UUID,
    request: Request,
    session: MutationSession,
    db: Database,
    file: Annotated[UploadFile, File()],
    supplier_id: Annotated[UUID, Form()],
    revision_id: Annotated[UUID, Form()],
) -> JSONResponse:
    case = owned_case(db, case_id, session.buyer_id)
    owned_child(db, RequirementRevision, revision_id, case_id=case.id, buyer_id=session.buyer_id)
    supplier = db.get(Supplier, supplier_id)
    if supplier is None or supplier.case_id != case.id:
        raise reject(404, "not_found", "This resource is unavailable.")
    chunks: list[bytes] = []
    total = 0
    while chunk := file.file.read(1024 * 1024):
        total += len(chunk)
        if total > MAX_BYTES:
            raise reject(413, "file_too_large", "PDF files are limited to 20 MiB.")
        chunks.append(chunk)
    content = b"".join(chunks)
    if file.content_type != "application/pdf" or not content.startswith(b"%PDF-"):
        raise reject(415, "unsupported_type", "Only PDF documents are supported.")
    inspection = inspect_pdf(content)
    if inspection.failure_reason == "too_large":
        raise reject(413, "too_many_pages", "PDF files are limited to 50 pages.")
    store = PrivateFileStore(request.app.state.settings.data_root)
    stored = store.put(case.id, content)
    duplicate = db.scalar(
        select(DocumentArtifact).where(
            DocumentArtifact.case_id == case.id,
            DocumentArtifact.supplier_id == supplier.id,
            DocumentArtifact.sha256 == stored.sha256,
        )
    )
    if duplicate is not None:  # Same bytes for the same supplier are one artifact.
        store.delete(stored.storage_key)
        return JSONResponse({"document": present_document(duplicate)}, status_code=202)
    quarantined = inspection.failure_reason is not None
    document = DocumentArtifact(
        case_id=case.id,
        revision_id=revision_id,
        supplier_id=supplier.id,
        origin="buyer_upload",
        storage_key=stored.storage_key,
        sha256=stored.sha256,
        media_type="application/pdf",
        byte_count=stored.byte_count,
        page_count=inspection.page_count,
        collected_at=datetime.now(UTC),
        state="quarantined" if quarantined else "queued",
        state_reason=inspection.failure_reason,
    )
    db.add(document)
    db.flush()
    append_event(
        db,
        case.id,
        "revision.updated",
        f"document:{document.id}",
        {"document_id": str(document.id), "state": document.state},
        revision_id=revision_id,
    )
    if not quarantined:
        enqueue(
            db,
            case,
            kind="extract_document",
            operation_key=f"extract:{document.id}",
            references={"document_id": str(document.id)},
        )
    return JSONResponse({"document": present_document(document)}, status_code=202)


@router.get("/cases/{case_id}/documents/{document_id}")
def read_document(
    case_id: UUID, document_id: UUID, session: SignedIn, db: Database
) -> dict[str, Any]:
    document = owned_child(
        db, DocumentArtifact, document_id, case_id=case_id, buyer_id=session.buyer_id
    )
    return {"document": present_document(document)}


_RANGE = re.compile(r"^bytes=(\d*)-(\d*)$")


@router.get("/cases/{case_id}/documents/{document_id}/content")
def document_content(
    case_id: UUID, document_id: UUID, request: Request, session: SignedIn, db: Database
) -> Response:
    document = owned_child(
        db, DocumentArtifact, document_id, case_id=case_id, buyer_id=session.buyer_id
    )
    if document.state == "quarantined":
        raise reject(409, "quarantined", "This document is quarantined.")
    store = PrivateFileStore(request.app.state.settings.data_root)
    content = store.read(document.storage_key, document.sha256)
    headers = {
        "Content-Disposition": f'attachment; filename="{document.id}.pdf"',
        "Cache-Control": "no-store",
        "Accept-Ranges": "bytes",
    }
    requested = request.headers.get("Range")
    if requested:
        match = _RANGE.match(requested)
        if not match or not (match.group(1) or match.group(2)):
            raise reject(416, "bad_range", "The byte range is not valid.")
        total = len(content)
        if match.group(1):
            start = int(match.group(1))
            end = int(match.group(2)) if match.group(2) else total - 1
        else:
            start, end = max(total - int(match.group(2)), 0), total - 1
        end = min(end, total - 1)
        if start > end or start >= total:
            raise reject(416, "bad_range", "The byte range is not valid.")
        headers["Content-Range"] = f"bytes {start}-{end}/{total}"
        return Response(
            content[start : end + 1],
            status_code=206,
            headers=headers,
            media_type="application/pdf",
        )
    return Response(content, headers=headers, media_type="application/pdf")
