"""Isolated PDF parser child process: reads PDF bytes on stdin, prints one JSON result.

Runs with a scrubbed environment and no application imports, so a hostile document cannot
reach credentials; the parent applies a wall-clock timeout.
"""

import json
import sys

MAX_PAGES = 50
MIN_TEXT_CHARACTERS = 20


def inspect(data: bytes) -> dict[str, object]:
    result: dict[str, object] = {
        "page_count": None,
        "text_pages": [],
        "scanned_pages": [],
        "pages": {},
        "failure_reason": None,
    }
    if not data.startswith(b"%PDF-"):
        result["failure_reason"] = "malformed_document"
        return result
    import pypdfium2 as pdfium

    try:
        document = pdfium.PdfDocument(data)
    except pdfium.PdfiumError as exc:
        locked = "password" in str(exc).lower()
        result["failure_reason"] = "locked_document" if locked else "malformed_document"
        return result
    try:
        count = len(document)
        result["page_count"] = count
        if count < 1:
            result["failure_reason"] = "malformed_document"
            return result
        if count > MAX_PAGES:
            result["failure_reason"] = "too_large"
            return result
        text_pages: list[int] = []
        scanned: list[int] = []
        pages: dict[str, str] = {}
        for index in range(count):
            page = document[index]
            try:
                text = page.get_textpage().get_text_range()
            finally:
                page.close()
            if len("".join(text.split())) >= MIN_TEXT_CHARACTERS:
                text_pages.append(index + 1)
                pages[str(index + 1)] = text
            else:
                scanned.append(index + 1)
        result.update(text_pages=text_pages, scanned_pages=scanned, pages=pages)
    except Exception:  # noqa: BLE001 -- a hostile file must fail closed, not crash the parent.
        result["failure_reason"] = "malformed_document"
    finally:
        document.close()
    return result


if __name__ == "__main__":
    print(json.dumps(inspect(sys.stdin.buffer.read())))
