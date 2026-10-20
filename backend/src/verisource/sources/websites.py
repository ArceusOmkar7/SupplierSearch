"""Bounded supplier-website traversal. Everything captured is the supplier's self-report.

Respects robots, one request at a time per domain, depth/page/PDF limits, a per-request
timeout, one transient retry and an overall deadline. Never visits IndiaMART, never solves a
CAPTCHA and never follows instructions found in page text.
"""

import hashlib
import re
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

from verisource.country_packs.contracts import AttemptSpec, Observation
from verisource.security.egress import EgressDenied, GuardedFetch
from verisource.sources.policy import AGENT, RobotsDecision, host_prohibited, robots_decision
from verisource.sources.quotas import LIMITS

CAPTCHA_MARKERS = ("captcha", "are you a robot", "verify you are human", "cf-challenge")
CERT_WORDS = ("certificate", "certification", "iso", "licence", "license", "bis", "iec", "nabcb")
PIN_CODE = re.compile(r"\b[1-9]\d{5}\b")
SKIP_EXTENSIONS = (
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".svg",
    ".zip",
    ".mp4",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".css",
    ".js",
    ".ico",
)


@dataclass
class PageCapture:
    url: str
    status: int
    content_type: str
    body: bytes
    text: str = ""
    title: str = ""


@dataclass
class TraversalResult:
    attempts: list[AttemptSpec] = field(default_factory=list)
    observations: list[Observation] = field(default_factory=list)
    pdfs: list[PageCapture] = field(default_factory=list)
    pages: list[PageCapture] = field(default_factory=list)
    coverage_gaps: list[str] = field(default_factory=list)


def _host_key(url: str) -> str:
    return (urlsplit(url).hostname or "").lower().removeprefix("www.")


def normalize_start(value: str) -> str:
    text = value.strip()
    if "//" not in text:
        text = "https://" + text
    parts = urlsplit(text)
    return urlunsplit((parts.scheme, parts.netloc, parts.path or "/", "", ""))


CHALLENGE_TITLES = (
    "just a moment",
    "attention required",
    "access denied",
    "are you a robot",
    "verify you are human",
    "security check",
    "captcha",
)


def is_challenge_page(body: bytes) -> bool:
    """A challenge interstitial, not an ordinary page that merely embeds a CAPTCHA form."""
    lowered = body[:200_000].lower()
    if not any(marker.encode() in lowered for marker in CAPTCHA_MARKERS):
        return False
    soup = BeautifulSoup(body[:200_000], "html.parser")
    title = " ".join(soup.title.get_text().split()).lower() if soup.title else ""
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    visible = " ".join(soup.get_text(" ").split())
    return any(phrase in title for phrase in CHALLENGE_TITLES) or len(visible) < 600


def _classify(response: httpx.Response) -> tuple[str, str | None]:
    status = response.status_code
    if status == 200:
        return ("blocked", "captcha") if is_challenge_page(response.content) else ("success", None)
    if status in {401, 403}:
        return "blocked", "permission_unverified"
    if status == 429:
        return "blocked", "quota_exhausted"
    if status in {404, 410}:
        return "no_record", None
    return "unavailable", None


def _text_and_links(body: bytes, base: str) -> tuple[str, str, list[tuple[str, str]]]:
    soup = BeautifulSoup(body, "html.parser")
    title = " ".join(soup.title.get_text().split()) if soup.title else ""
    links = [
        (urljoin(base, str(a["href"])).split("#")[0], " ".join(a.get_text().split()))
        for a in soup.find_all("a", href=True)
    ]
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = " ".join(soup.get_text(" ").split())
    return title, text, links


_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_PHONE = re.compile(r"(?<!\w)\+?\d[\d\s().-]{8,}\d(?!\w)")


def redact_contacts(text: str) -> str:
    """Personal contact details are not needed as evidence and are not retained in excerpts."""
    return _PHONE.sub("[contact removed]", _EMAIL.sub("[contact removed]", text))


def _excerpt(text: str, term: str | None, width: int = 600) -> str:
    if term:
        position = text.casefold().find(term.casefold())
        if position >= 0:
            start = max(position - width // 2, 0)
            return text[start : start + width]
    return text[:width]


def traverse(
    start_url: str,
    *,
    tag_terms: dict[str, str],
    fetcher: GuardedFetch,
    renderer: Callable[[str], tuple[int, bytes] | None] | None = None,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> TraversalResult:
    """Walk one supplier site; `tag_terms` maps buyer requirement text to assertion tags."""
    result = TraversalResult()
    start = normalize_start(start_url)
    started = clock()

    def now() -> datetime:
        return datetime.now(UTC)

    def attempt(
        target: str,
        *,
        dispatched: bool,
        outcome: str,
        reason: str | None,
        status: int | None = None,
        kind: str = "remote_request",
        began: datetime | None = None,
        retry_of: int | None = None,
    ) -> None:
        stamp = now()
        result.attempts.append(
            AttemptSpec(
                kind=kind,
                target=target,
                requested_at=began or stamp,
                finished_at=stamp,
                request_dispatched=dispatched,
                outcome=outcome,
                reason_code=reason,
                http_status=status,
                started_at=began,
                retry_of=retry_of,
            )
        )

    if host_prohibited(start):
        attempt(
            start,
            dispatched=False,
            outcome="skipped",
            reason="not_supported",
            kind="capability_check",
        )
        result.coverage_gaps.append("Marketplace listings are never fetched automatically.")
        return result

    robots_text, robots_status = None, None
    began = now()
    robots_url = urljoin(start, "/robots.txt")
    try:
        response, _final = fetcher.get(robots_url, max_bytes=512 * 1024)
        robots_status = response.status_code
        robots_text = response.text if response.status_code == 200 else None
        attempt(
            robots_url,
            dispatched=True,
            outcome="success"
            if robots_status == 200
            else "no_record"
            if robots_status in {404, 410}
            else "unavailable",
            reason=None,
            status=robots_status,
            began=began,
        )
    except EgressDenied:
        attempt(
            robots_url,
            dispatched=False,
            outcome="skipped",
            reason="not_supported",
            kind="capability_check",
        )
        result.coverage_gaps.append("The site address is not an eligible public destination.")
        return result
    except httpx.TimeoutException:
        attempt(robots_url, dispatched=True, outcome="timeout", reason=None, began=began)
    except httpx.HTTPError:
        attempt(robots_url, dispatched=True, outcome="unavailable", reason=None, began=began)
    decision: RobotsDecision = robots_decision(robots_text, robots_status, start)
    if not decision.allowed:
        attempt(
            start,
            dispatched=False,
            outcome="skipped",
            reason=decision.reason_code,
            kind="capability_check",
        )
        result.coverage_gaps.append(
            "Crawling permission could not be established; no pages were requested."
        )
        return result
    parser = RobotFileParser()
    parser.parse((robots_text or "").splitlines())
    delay = max(float(parser.crawl_delay(AGENT) or 1.0), 1.0)
    can_fetch = parser.can_fetch

    queue: deque[tuple[str, int]] = deque([(start, 0)])
    seen = {start}
    pdf_links: list[tuple[str, str]] = []
    last_request = 0.0
    host = _host_key(start)
    while queue and len(result.pages) < LIMITS.pages_per_supplier:
        if clock() - started > LIMITS.website_deadline_seconds:
            attempt(
                start, dispatched=False, outcome="skipped", reason="deadline", kind="deadline_check"
            )
            result.coverage_gaps.append(
                "The website deadline was reached before all pages were read."
            )
            break
        url, depth = queue.popleft()
        if not can_fetch(AGENT, url):
            continue
        wait = delay - (clock() - last_request)
        if last_request and wait > 0:
            sleep(wait)
        previous: int | None = None
        for _tries in range(1 + LIMITS.transient_retries):
            began = now()
            last_request = clock()
            try:
                response, final = fetcher.get(url, max_bytes=2 * 1024 * 1024)
            except EgressDenied:
                attempt(
                    url,
                    dispatched=False,
                    outcome="skipped",
                    reason="not_supported",
                    kind="capability_check",
                )
                break
            except httpx.TimeoutException:
                attempt(
                    url,
                    dispatched=True,
                    outcome="timeout",
                    reason=None,
                    began=began,
                    retry_of=previous,
                )
                previous = len(result.attempts) - 1
                continue
            except httpx.HTTPError:
                attempt(
                    url,
                    dispatched=True,
                    outcome="transient_error",
                    reason=None,
                    began=began,
                    retry_of=previous,
                )
                previous = len(result.attempts) - 1
                continue
            outcome, reason = _classify(response)
            attempt(
                final,
                dispatched=True,
                outcome=outcome,
                reason=reason,
                status=response.status_code,
                began=began,
                retry_of=previous,
            )
            if outcome == "success":
                kind = response.headers.get("content-type", "").split(";")[0].strip().lower()
                capture = PageCapture(final, response.status_code, kind, response.content)
                if kind == "text/html":
                    capture.title, capture.text, links = _text_and_links(response.content, final)
                    if (
                        renderer
                        and len(capture.text) < 200
                        and b"<script" in response.content.lower()
                    ):
                        rendered = renderer(final)
                        if rendered is not None:
                            capture.body = rendered[1]
                            capture.title, capture.text, links = _text_and_links(rendered[1], final)
                    result.pages.append(capture)
                    for link, anchor in links:
                        parts = urlsplit(link)
                        if parts.scheme not in {"http", "https"} or host_prohibited(link):
                            continue
                        if _host_key(link) != host:
                            continue
                        if parts.path.lower().endswith(".pdf"):
                            if any(w in (anchor + parts.path).casefold() for w in CERT_WORDS):
                                pdf_links.append((link, anchor))
                            continue
                        if parts.path.lower().endswith(SKIP_EXTENSIONS):
                            continue
                        if link not in seen and depth < LIMITS.crawl_depth:
                            seen.add(link)
                            queue.append((link, depth + 1))
                elif kind == "application/pdf":
                    result.pdfs.append(capture)
            break

    for link, anchor in pdf_links[: LIMITS.certificate_pdfs_per_supplier]:
        if clock() - started > LIMITS.website_deadline_seconds or not can_fetch(AGENT, link):
            continue
        wait = delay - (clock() - last_request)
        if wait > 0:
            sleep(wait)
        began = now()
        last_request = clock()
        try:
            response, final = fetcher.get(link, max_bytes=20 * 1024 * 1024)
        except EgressDenied, httpx.HTTPError:
            attempt(
                link,
                dispatched=False,
                outcome="skipped",
                reason="not_supported",
                kind="capability_check",
            )
            continue
        outcome, reason = _classify(response)
        attempt(
            final,
            dispatched=True,
            outcome=outcome,
            reason=reason,
            status=response.status_code,
            began=began,
        )
        if outcome == "success" and response.content.startswith(b"%PDF-"):
            result.pdfs.append(
                PageCapture(final, 200, "application/pdf", response.content, title=anchor)
            )

    collected = now()
    for page in result.pages:
        tags = sorted(
            {tag for term, tag in tag_terms.items() if term.casefold() in page.text.casefold()}
        )
        first_term = next((t for t in tag_terms if t.casefold() in page.text.casefold()), None)
        excerpt = redact_contacts(_excerpt(page.text, first_term))
        if not excerpt:
            continue
        pin = PIN_CODE.search(page.text)
        if pin:
            tags.append("address")
        result.observations.append(
            Observation(
                source_id="in.supplier-website",
                source_version=1,
                source_ref=page.url,
                locator=page.url,
                observation=f"{page.title}: {excerpt}" if page.title else excerpt,
                collected_at=collected,
                authority_role="supplier",
                origin_lineage=f"supplier-website:{host}",
                self_reported=True,
                content_hash=hashlib.sha256(page.body).hexdigest(),
                assertion_tags=tuple(tags),
            )
        )
    for pdf in result.pdfs:
        result.observations.append(
            Observation(
                source_id="in.supplier-website",
                source_version=1,
                source_ref=pdf.url,
                locator=pdf.url,
                observation=f"Supplier page links a certificate-like document: {pdf.title or pdf.url}",
                collected_at=collected,
                authority_role="supplier",
                origin_lineage=f"supplier-website:{host}",
                self_reported=True,
                content_hash=hashlib.sha256(pdf.body).hexdigest(),
                assertion_tags=("certificate_link",),
            )
        )
    if not result.pages:
        result.coverage_gaps.append("No supplier website page could be read.")
    return result
