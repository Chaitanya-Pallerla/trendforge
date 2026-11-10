"""HTTP helpers with retries, plus an optional camofox-browser fallback.

Plain `requests` is used first (fast, cheap). When a site blocks it (403/429 or
bot walls) and CAMOFOX_URL is set, the page is loaded in a real Camoufox
browser via the camofox-browser REST API and its content is read back.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import requests

from .config import CONFIG

log = logging.getLogger("trendforge.net")

USER_AGENT = "TrendForge/0.1 (open-source trend tracker; +https://github.com/topics/trendforge)"

_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT})


class FetchError(RuntimeError):
    pass


def get(url: str, *, params: dict | None = None, headers: dict | None = None,
        timeout: float = 25, retries: int = 2) -> requests.Response:
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            resp = _session.get(url, params=params, headers=headers, timeout=timeout)
            if resp.status_code in (429, 500, 502, 503, 504) and attempt < retries:
                wait = float(resp.headers.get("Retry-After", 2 ** (attempt + 1)))
                log.warning("HTTP %s from %s, retrying in %.0fs", resp.status_code, url, wait)
                time.sleep(min(wait, 60))
                continue
            return resp
        except requests.RequestException as exc:  # network errors
            last_exc = exc
            time.sleep(2 ** (attempt + 1))
    raise FetchError(f"GET {url} failed: {last_exc}")


def get_json(url: str, **kwargs: Any) -> Any:
    resp = get(url, **kwargs)
    if resp.status_code != 200:
        raise FetchError(f"GET {url} -> HTTP {resp.status_code}")
    return resp.json()


# ---------------------------------------------------------------------------
# camofox-browser client
# ---------------------------------------------------------------------------

class Camofox:
    """Tiny client for the camofox-browser REST API (see camofox AGENTS.md)."""

    def __init__(self, base_url: str, api_key: str = "", user_id: str = "trendforge"):
        self.base = base_url.rstrip("/")
        self.user_id = user_id
        self._tabs: dict[str, str] = {}
        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"

    def available(self) -> bool:
        try:
            return requests.get(f"{self.base}/health", timeout=5).status_code == 200
        except requests.RequestException:
            return False

    def _post(self, path: str, body: dict, timeout: float = 90) -> dict:
        resp = requests.post(f"{self.base}{path}", json=body, headers=self.headers, timeout=timeout)
        if resp.status_code >= 400:
            raise FetchError(f"camofox {path} -> HTTP {resp.status_code}: {resp.text[:200]}")
        return resp.json()

    def evaluate_on(self, url: str, expression: str, settle_seconds: float = 2.0) -> Any:
        """Open `url` in a fresh tab, run `expression`, close the tab, return the result."""
        tab = self._post("/tabs", {"userId": self.user_id, "sessionKey": "trendforge", "url": url})
        tab_id = tab.get("tabId")
        if not tab_id:
            raise FetchError(f"camofox did not return a tabId: {tab}")
        try:
            time.sleep(settle_seconds)
            out = self._post(f"/tabs/{tab_id}/evaluate", {"userId": self.user_id, "expression": expression})
            return out.get("result")
        finally:
            try:
                requests.delete(f"{self.base}/tabs/{tab_id}", params={"userId": self.user_id},
                                headers=self.headers, timeout=15)
            except requests.RequestException:
                pass

    def page_text(self, url: str) -> str:
        return str(self.evaluate_on(url, "document.body ? document.body.innerText : ''") or "")

    def page_html(self, url: str) -> str:
        return str(self.evaluate_on(url, "document.documentElement.outerHTML") or "")

    # -- same-origin fetch through a real browser tab (reused per origin) --

    def _origin_tab(self, origin: str) -> str:
        tab_id = self._tabs.get(origin)
        if tab_id:
            return tab_id
        tab = self._post("/tabs", {"userId": self.user_id, "sessionKey": "trendforge", "url": origin + "/"})
        tab_id = tab.get("tabId")
        if not tab_id:
            raise FetchError(f"camofox did not return a tabId: {tab}")
        time.sleep(3)  # let the first page settle (cookies, bot checks)
        self._tabs[origin] = tab_id
        return tab_id

    def fetch_text(self, url: str) -> str:
        """GET `url` with window.fetch() from a tab on the same origin.

        Requests carry the browser's real fingerprint and cookies, and the raw
        response body is returned (no Firefox JSON-viewer wrapping).
        """
        parts = requests.utils.urlparse(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        tab_id = self._origin_tab(origin)
        expr = (
            f"fetch({json.dumps(url)}, {{credentials: 'include'}})"
            ".then(async r => ({status: r.status, body: await r.text()}))"
        )
        out = self._post(f"/tabs/{tab_id}/evaluate", {"userId": self.user_id, "expression": expr})
        result = out.get("result") or {}
        if result.get("status") != 200:
            raise FetchError(f"camofox fetch {url} -> HTTP {result.get('status')}")
        return result.get("body") or ""

    def scrape(self, url: str, expression: str, settle_seconds: float = 3.0) -> Any:
        """Navigate a reusable tab to `url` and evaluate `expression` (may return a Promise)."""
        tab_id = self._tabs.get("__scrape__")
        if tab_id is None:
            tab = self._post("/tabs", {"userId": self.user_id, "sessionKey": "trendforge", "url": url})
            tab_id = tab.get("tabId")
            if not tab_id:
                raise FetchError(f"camofox did not return a tabId: {tab}")
            self._tabs["__scrape__"] = tab_id
        else:
            self._post(f"/tabs/{tab_id}/navigate", {"userId": self.user_id, "url": url})
        time.sleep(settle_seconds)
        out = self._post(f"/tabs/{tab_id}/evaluate", {"userId": self.user_id, "expression": expression})
        return out.get("result")

    def close(self) -> None:
        for tab_id in self._tabs.values():
            try:
                requests.delete(f"{self.base}/tabs/{tab_id}", params={"userId": self.user_id},
                                headers=self.headers, timeout=15)
            except requests.RequestException:
                pass
        self._tabs.clear()


_camofox: Camofox | None = None
_camofox_checked = False


def camofox() -> Camofox | None:
    """Return a live camofox client, or None if not configured / not reachable."""
    global _camofox, _camofox_checked
    if _camofox_checked:
        return _camofox
    _camofox_checked = True
    if CONFIG.camofox_url:
        client = Camofox(CONFIG.camofox_url, CONFIG.camofox_api_key)
        if client.available():
            _camofox = client
            log.info("camofox-browser available at %s", CONFIG.camofox_url)
        else:
            log.warning("CAMOFOX_URL set but %s is not reachable; continuing without it", CONFIG.camofox_url)
    return _camofox


def close_camofox() -> None:
    if _camofox is not None:
        _camofox.close()


def get_json_with_fallback(url: str, *, browser_first: bool = False, **kwargs: Any) -> Any:
    """Fetch JSON; if blocked, retry through a real browser via camofox.

    browser_first=True skips the plain attempt for hosts known to block scripts.
    """
    client = camofox()
    if not (browser_first and client):
        try:
            return get_json(url, **kwargs)
        except FetchError as exc:
            if client is None:
                raise
            log.info("plain fetch blocked (%s); retrying via camofox", exc)
    full = requests.Request("GET", url, params=kwargs.get("params")).prepare().url
    return json.loads(client.fetch_text(full))


def get_html_with_fallback(url: str, **kwargs: Any) -> str:
    resp = get(url, **kwargs)
    if resp.status_code == 200 and len(resp.text) > 2000:
        return resp.text
    client = camofox()
    if client is None:
        raise FetchError(f"GET {url} -> HTTP {resp.status_code}")
    log.info("plain fetch of %s returned %s; retrying via camofox", url, resp.status_code)
    return client.page_html(url)
