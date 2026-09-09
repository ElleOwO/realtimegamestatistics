"""Authenticated CanadaWest playback discovery. No credentials leave this module.

Playwright is deliberately a lazy dependency: CPU contracts use fake sessions.
The provider's private API is not assumed stable; resolve through its normal UI.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from urllib.parse import urlsplit


class SourceError(RuntimeError):
    """A safe, operator-facing error (never a raw browser/network exception)."""


def validate_event_url(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("Enter a CanadaWest game link.")
    parsed = urlsplit(value.strip())
    if (parsed.scheme != "https" or parsed.hostname not in {"canadawest.tv", "www.canadawest.tv"}
            or parsed.username or parsed.password or parsed.port not in (None, 443)):
        raise ValueError("Enter an HTTPS game link from canadawest.tv.")
    if len(value) > 2048 or any(ord(c) < 32 for c in value):
        raise ValueError("Invalid game link.")
    return value.strip()


@dataclass(repr=False)
class Playback:
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    cookies: str = ""


class CanadaWestConnector:
    def __init__(self, event_url: str, email: str, password: str):
        self.event_url = validate_event_url(event_url)
        self.email, self.password = email, password
        self.driver = self.browser = self.context = self.page = None

    def resolve(self) -> Playback:
        if not self.email or not self.password:
            raise SourceError("CanadaWest account is not configured. Ask the RTGS administrator to connect it.")
        try:
            return self._resolve()
        except SourceError:
            raise
        except Exception:
            raise SourceError("Could not connect to CanadaWest playback. Check account access and retry.") from None

    def _resolve(self) -> Playback:
        from playwright.sync_api import sync_playwright

        if self.page is None:
            self.driver = sync_playwright().start()
            self.browser = self.driver.chromium.launch(headless=True)
            self.context = self.browser.new_context(viewport={"width": 1280, "height": 720})
            self.page = self.context.new_page()
        page = self.page
        found: list[Playback] = []

        def request(route):
            req = route.request
            # Intercept the player's manifest, then delegate media consumption to
            # the demuxer. Never run a second browser video decoder alongside it.
            if re.search(r"\.(m3u8|mpd)(?:[?#]|$)", req.url, re.I):
                headers = {k: v for k, v in req.all_headers().items()
                           if k.lower() in {"authorization", "referer", "origin", "user-agent"}}
                found.append(Playback(req.url, headers))
                route.abort()
            else:
                route.continue_()

        page.route("**/*", request)
        try:
            page.goto(self.event_url, wait_until="domcontentloaded", timeout=45000)
            deadline = time.monotonic() + 60
            submitted = False
            while time.monotonic() < deadline:
                if found:
                    result = found[0]
                    cookies = self.context.cookies([result.url])
                    result.cookies = "\n".join(
                        f"{c['name']}={c['value']}; path={c.get('path', '/')}; domain={c['domain']};"
                        for c in cookies
                    )
                    return result
                text = page.locator("body").inner_text(timeout=5000).lower()
                if "too many people" in text or "simultaneous" in text and "limit" in text:
                    raise SourceError("CanadaWest device limit reached. Close another playback session and retry.")
                if "incorrect password" in text or "invalid credentials" in text:
                    raise SourceError("CanadaWest sign-in failed. Update the connected account.")
                password = page.locator('input[type="password"]')
                if password.count() and password.first.is_visible() and not submitted:
                    email = page.locator('input[type="email"], input[name="email"], input[autocomplete="username"]')
                    if not email.count():
                        raise SourceError("CanadaWest sign-in has changed. The connector needs an update.")
                    email.first.fill(self.email)
                    password.first.fill(self.password)
                    password.first.press("Enter")
                    submitted = True
                else:
                    for pattern in (r"^(log\s?in|sign in)$", r"^(watch|watch live|play|play video|watch event)$"):
                        control = page.get_by_role("button", name=re.compile(pattern, re.I)).or_(
                            page.get_by_role("link", name=re.compile(pattern, re.I)))
                        if control.count() and control.first.is_visible():
                            control.first.click(timeout=3000)
                            break
                page.wait_for_timeout(1000)
            raise SourceError("No playable stream yet. Check the event start time and account entitlement; playback compatibility is not verified.")
        finally:
            page.unroute("**/*", request)
            # Network activity for login/renewal only; no provider media playback.
            page.goto("about:blank")

    def refresh(self) -> Playback:
        return self.resolve()

    def close(self):
        if self.browser:
            self.browser.close()
        if self.driver:
            self.driver.stop()
        self.driver = self.browser = self.context = self.page = None
