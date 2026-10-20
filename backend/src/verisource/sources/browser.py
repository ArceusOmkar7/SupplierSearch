"""Eligible Playwright rendering for script-built supplier pages (one browser at a time).

Every browser request, including subresources and redirects, passes the same destination
guard as HTTP fetches. Downloads, permissions and dialogs are refused; no CAPTCHA is solved.
"""

import threading

from verisource.security.egress import EgressDenied, Resolver, system_resolver, validate_destination

_ONE_BROWSER = threading.Lock()
RENDER_TIMEOUT_MS = 20_000


def render(url: str, *, resolver: Resolver = system_resolver) -> tuple[int, bytes] | None:
    """Return (status, rendered HTML) or None when rendering is unavailable or ineligible."""
    try:
        validate_destination(url, resolver=resolver)
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except EgressDenied, ImportError:
        return None
    with _ONE_BROWSER:
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                try:
                    context = browser.new_context(
                        accept_downloads=False, permissions=[], service_workers="block"
                    )

                    def guard(route, request):  # type: ignore[no-untyped-def]
                        try:
                            validate_destination(request.url, resolver=resolver)
                        except EgressDenied:
                            route.abort("blockedbyclient")
                            return
                        route.continue_()

                    context.route("**/*", guard)
                    page = context.new_page()
                    page.on("dialog", lambda dialog: dialog.dismiss())
                    response = page.goto(url, timeout=RENDER_TIMEOUT_MS, wait_until="load")
                    page.wait_for_timeout(1500)
                    status = response.status if response else 0
                    html = page.content().encode("utf-8")
                    return status, html
                finally:
                    browser.close()
        except PlaywrightError:
            return None
