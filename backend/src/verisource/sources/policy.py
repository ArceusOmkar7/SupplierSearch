"""Source access policy: robots handling, prohibited hosts and reuse-rights separation.

Robots allowance is a crawling permission only; it never establishes a right to reuse or
retain content. Missing or unreadable robots policy is `permission_unverified`, not allowed.
"""

from dataclasses import dataclass
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

AGENT = "VeriSourceBot"
# Hosts the product never visits automatically (listing links stay opaque identifier text).
PROHIBITED_HOST_SUFFIXES = ("indiamart.com",)


@dataclass(frozen=True)
class RobotsDecision:
    allowed: bool
    reason_code: str | None
    reuse_rights_established: bool = False


def host_prohibited(url: str) -> bool:
    host = (urlsplit(url).hostname or "").lower().rstrip(".")
    return any(host == s or host.endswith("." + s) for s in PROHIBITED_HOST_SUFFIXES)


def robots_decision(robots_text: str | None, status: int | None, url: str) -> RobotsDecision:
    """RFC 9309 handling of the robots fetch outcome for one target URL."""
    if host_prohibited(url):
        return RobotsDecision(False, "not_supported")
    if status in {404, 410}:  # No robots file: crawling is not restricted by it.
        return RobotsDecision(True, None)
    if status != 200 or robots_text is None:  # 3xx unresolved, 5xx, network failure.
        return RobotsDecision(False, "permission_unverified")
    parser = RobotFileParser()
    parser.parse(robots_text.splitlines())
    if parser.can_fetch(AGENT, url):
        return RobotsDecision(True, None)
    return RobotsDecision(False, "robots_disallowed")
