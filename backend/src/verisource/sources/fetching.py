"""One policy-checked GET (robots, prohibited hosts, egress) that reports each real attempt."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from urllib.parse import urljoin

import httpx

from verisource.country_packs.contracts import AttemptSpec
from verisource.security.egress import EgressDenied, GuardedFetch
from verisource.sources.policy import host_prohibited, robots_decision


@dataclass
class PermittedFetch:
    response: httpx.Response | None = None
    final_url: str = ""
    attempts: list[AttemptSpec] = field(default_factory=list)
    gap: str | None = None


def classify(response: httpx.Response) -> tuple[str, str | None]:
    status = response.status_code
    if status == 200:
        return "success", None
    if status in {401, 403}:
        return "blocked", "permission_unverified"
    if status == 429:
        return "blocked", "quota_exhausted"
    if status in {404, 410}:
        return "no_record", None
    return "unavailable", None


def permitted_get(
    fetcher: GuardedFetch, url: str, *, max_bytes: int = 5 * 1024 * 1024
) -> PermittedFetch:
    result = PermittedFetch()

    def record(
        target: str,
        *,
        dispatched: bool,
        outcome: str,
        reason: str | None = None,
        status: int | None = None,
        kind: str = "remote_request",
        began: datetime | None = None,
    ) -> None:
        stamp = datetime.now(UTC)
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
            )
        )

    if host_prohibited(url):
        record(
            url,
            dispatched=False,
            outcome="skipped",
            reason="not_supported",
            kind="capability_check",
        )
        result.gap = "This host is not fetched automatically."
        return result
    began = datetime.now(UTC)
    robots_url = urljoin(url, "/robots.txt")
    robots_text, robots_status = None, None
    try:
        robots, _ = fetcher.get(robots_url, max_bytes=512 * 1024)
        robots_status = robots.status_code
        robots_text = robots.text if robots_status == 200 else None
        record(
            robots_url,
            dispatched=True,
            outcome="success"
            if robots_status == 200
            else "no_record"
            if robots_status in {404, 410}
            else "unavailable",
            status=robots_status,
            began=began,
        )
    except EgressDenied:
        record(
            url,
            dispatched=False,
            outcome="skipped",
            reason="not_supported",
            kind="capability_check",
        )
        result.gap = "The address is not an eligible public destination."
        return result
    except httpx.TimeoutException:
        record(robots_url, dispatched=True, outcome="timeout", began=began)
    except httpx.HTTPError:
        record(robots_url, dispatched=True, outcome="unavailable", began=began)
    decision = robots_decision(robots_text, robots_status, url)
    if not decision.allowed:
        record(
            url,
            dispatched=False,
            outcome="skipped",
            reason=decision.reason_code,
            kind="capability_check",
        )
        result.gap = "Crawling permission could not be established; the page was not requested."
        return result
    began = datetime.now(UTC)
    try:
        response, final = fetcher.get(url, max_bytes=max_bytes)
    except EgressDenied:
        record(
            url,
            dispatched=False,
            outcome="skipped",
            reason="not_supported",
            kind="capability_check",
        )
        result.gap = "The address is not an eligible public destination."
        return result
    except httpx.TimeoutException:
        record(url, dispatched=True, outcome="timeout", began=began)
        result.gap = "The source timed out."
        return result
    except httpx.HTTPError:
        record(url, dispatched=True, outcome="transient_error", began=began)
        result.gap = "The source could not be reached."
        return result
    outcome, reason = classify(response)
    record(
        final,
        dispatched=True,
        outcome=outcome,
        reason=reason,
        status=response.status_code,
        began=began,
    )
    if outcome == "success":
        result.response, result.final_url = response, final
    else:
        result.gap = f"The source answered HTTP {response.status_code}."
    return result
