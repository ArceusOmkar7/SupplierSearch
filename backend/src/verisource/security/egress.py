"""Destination, redirect and resolved-address guards for every outbound source request.

Source pages are untrusted: this guard blocks loopback, private, link-local and metadata
targets, credentialed URLs and non-HTTP schemes, and re-checks each redirect hop and the
peer address actually connected to. A page's text can never widen these rules.
"""

import ipaddress
import socket
import threading
from collections.abc import Callable
from contextlib import contextmanager
from urllib.parse import SplitResult, urljoin, urlsplit

import httpx

Resolver = Callable[[str], list[str]]
ALLOWED_PORTS = {None, 80, 443}
BLOCKED_SUFFIXES = (".local", ".internal", ".localhost", ".lan", ".home.arpa")
MAX_REDIRECTS = 5


_GLOBAL_REQUESTS = threading.BoundedSemaphore(4)  # four outbound requests across all sources
_HOST_LOCKS: dict[str, threading.Lock] = {}
_HOST_GUARD = threading.Lock()


@contextmanager
def request_slot(host: str):  # type: ignore[no-untyped-def]
    """Hold one global slot and the single per-domain slot for the duration of a request."""
    with _HOST_GUARD:
        lock = _HOST_LOCKS.setdefault(host.lower().removeprefix("www."), threading.Lock())
    with lock, _GLOBAL_REQUESTS:
        yield


class EgressDenied(Exception):
    """Raised before any request when a destination is not an eligible public target."""


def system_resolver(host: str) -> list[str]:
    try:
        return sorted(
            {str(info[4][0]) for info in socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)}
        )
    except socket.gaierror as exc:
        raise EgressDenied("Host could not be resolved") from exc


def _check_address(text: str) -> None:
    address = ipaddress.ip_address(text.split("%", 1)[0])
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        address = address.ipv4_mapped
    if not address.is_global or address.is_multicast:
        raise EgressDenied("Destination address is not a public address")


def validate_destination(url: str, *, resolver: Resolver = system_resolver) -> SplitResult:
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"}:
        raise EgressDenied("Only HTTP and HTTPS sources are eligible")
    if parts.username is not None or parts.password is not None:
        raise EgressDenied("Credentialed URLs are not eligible")
    host = parts.hostname
    if not host:
        raise EgressDenied("A host is required")
    try:
        port = parts.port
    except ValueError as exc:
        raise EgressDenied("Invalid port") from exc
    if port not in ALLOWED_PORTS:
        raise EgressDenied("Port is not eligible")
    lowered = host.lower().rstrip(".")
    if lowered == "localhost" or lowered.endswith(BLOCKED_SUFFIXES):
        raise EgressDenied("Local host names are not eligible")
    try:
        ipaddress.ip_address(lowered)
        literal = True
    except ValueError:
        literal = False
    addresses = [lowered] if literal else resolver(lowered)
    if not addresses:
        raise EgressDenied("Host resolved to no address")
    for address in addresses:
        _check_address(address)
    return parts


class GuardedFetch:
    """Manual redirect following with a guard on every hop and on the connected peer."""

    def __init__(
        self,
        *,
        timeout: float = 20.0,
        user_agent: str = "VeriSourceBot/0.1 (local buyer verification; respects robots.txt)",
        resolver: Resolver = system_resolver,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._resolver = resolver
        self._client = httpx.Client(
            timeout=timeout,
            follow_redirects=False,
            trust_env=False,
            headers={"User-Agent": user_agent},
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def get(self, url: str, *, max_bytes: int = 25 * 1024 * 1024) -> tuple[httpx.Response, str]:
        """Return (response with body, final URL). Raises EgressDenied for ineligible hops."""
        current = url
        for _hop in range(MAX_REDIRECTS + 1):
            validate_destination(current, resolver=self._resolver)
            with (
                request_slot(urlsplit(current).hostname or ""),
                self._client.stream("GET", current) as response,
            ):
                stream = response.extensions.get("network_stream")
                peer = stream.get_extra_info("server_addr") if stream is not None else None
                if peer:
                    _check_address(str(peer[0]))
                if response.is_redirect and "location" in response.headers:
                    current = urljoin(current, response.headers["location"])
                    continue
                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > max_bytes:
                        raise EgressDenied("Response exceeds the size limit")
                # Body bytes are already decoded; drop encoding headers so they are not re-decoded.
                headers = [
                    (k, v)
                    for k, v in response.headers.multi_items()
                    if k.lower() not in {"content-encoding", "content-length", "transfer-encoding"}
                ]
                finished = httpx.Response(
                    response.status_code,
                    headers=headers,
                    content=bytes(body),
                    request=response.request,
                )
                return finished, current
        raise EgressDenied("Too many redirects")
