"""GitHub sources: the Trending page (HTML) and the Search API."""

from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timedelta, timezone

from bs4 import BeautifulSoup

from ..categories import CATEGORIES, STUDENTS_ID
from ..config import CONFIG
from ..net import FetchError, get, get_html_with_fallback

log = logging.getLogger("trendforge.github")

API = "https://api.github.com"


def _api_headers() -> dict:
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if CONFIG.github_token:
        headers["Authorization"] = f"Bearer {CONFIG.github_token}"
    return headers


def _int(text: str | None) -> int:
    if not text:
        return 0
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else 0


# ---------------------------------------------------------------------------
# Trending page
# ---------------------------------------------------------------------------

def parse_trending_html(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    repos = []
    for rank, row in enumerate(soup.select("article.Box-row"), start=1):
        link = row.select_one("h2 a")
        if not link or not link.get("href"):
            continue
        full_name = link["href"].strip("/")
        desc_el = row.select_one("p")
        lang_el = row.select_one('[itemprop="programmingLanguage"]')
        stars_el = row.select_one('a[href$="/stargazers"]')
        forks_el = row.select_one('a[href$="/forks"]')
        period_el = row.select_one("span.d-inline-block.float-sm-right")
        repos.append({
            "full_name": full_name,
            "description": desc_el.get_text(" ", strip=True) if desc_el else "",
            "language": lang_el.get_text(strip=True) if lang_el else None,
            "stars": _int(stars_el.get_text() if stars_el else None),
            "forks": _int(forks_el.get_text() if forks_el else None),
            "period_stars": _int(period_el.get_text() if period_el else None),
            "trending_rank": rank,
        })
    return repos


def fetch_trending(since: str = "daily", language: str = "") -> list[dict]:
    url = f"https://github.com/trending/{language}" if language else "https://github.com/trending"
    try:
        html = get_html_with_fallback(url, params={"since": since})
    except FetchError as exc:
        log.warning("trending fetch failed: %s", exc)
        return []
    repos = parse_trending_html(html)
    log.info("trending %s%s: %d repos", since, f"/{language}" if language else "", len(repos))
    return repos


# ---------------------------------------------------------------------------
# REST API
# ---------------------------------------------------------------------------

def _normalize_api_repo(item: dict) -> dict:
    return {
        "full_name": item["full_name"],
        "description": item.get("description") or "",
        "language": item.get("language"),
        "stars": item.get("stargazers_count", 0),
        "forks": item.get("forks_count", 0),
        "open_issues": item.get("open_issues_count", 0),
        "topics": item.get("topics") or [],
        "created_at": item.get("created_at"),
        "pushed_at": item.get("pushed_at"),
        "license": (item.get("license") or {}).get("spdx_id"),
        "homepage": item.get("homepage") or None,
        "owner_avatar": (item.get("owner") or {}).get("avatar_url"),
        "archived": item.get("archived", False),
    }


_last_search = 0.0


def search_repos(query: str, *, sort: str = "stars", per_page: int = 30) -> list[dict]:
    """GitHub search (30 req/min with a token, 10 without) — paced accordingly."""
    global _last_search
    min_gap = 2.2 if CONFIG.github_token else 6.5
    wait = _last_search + min_gap - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    _last_search = time.monotonic()

    resp = get(f"{API}/search/repositories", headers=_api_headers(),
               params={"q": query, "sort": sort, "order": "desc", "per_page": per_page})
    if resp.status_code != 200:
        log.warning("search %r -> HTTP %s %s", query, resp.status_code, resp.text[:120])
        return []
    return [_normalize_api_repo(i) for i in resp.json().get("items", []) if not i.get("archived")]


def repo_details(full_name: str) -> dict | None:
    resp = get(f"{API}/repos/{full_name}", headers=_api_headers())
    if resp.status_code != 200:
        return None
    return _normalize_api_repo(resp.json())


def readme_excerpt(full_name: str, limit: int = 2500) -> str:
    """First part of the README (raw.githubusercontent is not API-rate-limited)."""
    for name in ("README.md", "readme.md", "README.rst", "README"):
        try:
            resp = get(f"https://raw.githubusercontent.com/{full_name}/HEAD/{name}", timeout=15, retries=0)
        except FetchError:
            return ""
        if resp.status_code == 200:
            text = re.sub(r"<[^>]+>", " ", resp.text)          # strip html tags/badges
            text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)   # strip images
            text = re.sub(r"[ \t]+", " ", text)
            text = re.sub(r"\n{3,}", "\n\n", text)
            return text.strip()[:limit]
    return ""


def _dates() -> dict[str, str]:
    today = datetime.now(timezone.utc).date()
    return {f"d{n}": (today - timedelta(days=n)).isoformat() for n in (1, 7, 14, 30, 90)}


def fetch_search_signals() -> dict[str, list[dict]]:
    """Run all search queries. Returns {query_label: [repos]}."""
    d = _dates()
    queries: list[tuple[str, str]] = [
        ("new-this-week", f"created:>{d['d7']} stars:>50"),
        ("new-this-month", f"created:>{d['d30']} stars:>500"),
    ]
    for cat in CATEGORIES:
        for q in cat.queries:
            queries.append((cat.id, q.format(**d)))
    # beginner-friendly projects actively looking for contributors
    queries.append(("good-first-issues",
                     f"good-first-issues:>10 stars:>500 pushed:>{d['d7']}"))

    out: dict[str, list[dict]] = {}
    for label, q in queries:
        repos = search_repos(q, per_page=30)
        log.info("search [%s] %s -> %d", label, q, len(repos))
        out.setdefault(label, []).extend(repos)
    return out


def students_query_labels() -> set[str]:
    return {STUDENTS_ID, "good-first-issues"}
