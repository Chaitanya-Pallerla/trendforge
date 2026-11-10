"""Community signals: Hacker News (Algolia API) and Reddit."""

from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timezone

from ..config import CONFIG
from ..net import FetchError, camofox, get_json, get_json_with_fallback

log = logging.getLogger("trendforge.discussions")

GITHUB_RE = re.compile(r"github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)")

# r/<sub> -> audience tag
SUBREDDITS = {
    "MachineLearning": "developers",
    "LocalLLaMA": "developers",
    "programming": "developers",
    "webdev": "developers",
    "opensource": "developers",
    "selfhosted": "developers",
    "ClaudeAI": "developers",
    "learnprogramming": "students",
    "cscareerquestions": "students",
    "csMajors": "students",
    "learnmachinelearning": "students",
}


def repo_from_url(url: str | None) -> str | None:
    if not url:
        return None
    m = GITHUB_RE.search(url)
    if not m:
        return None
    name = m.group(1).removesuffix(".git")
    owner, _, repo = name.partition("/")
    if owner.lower() in {"orgs", "topics", "sponsors", "features", "about", "marketplace"}:
        return None
    return f"{owner}/{repo}"


def fetch_hackernews(hours: int = 48, min_points: int = 40) -> list[dict]:
    if not CONFIG.hn_enabled:
        return []
    since = int(time.time()) - hours * 3600
    try:
        data = get_json("https://hn.algolia.com/api/v1/search",
                        params={"tags": "story", "hitsPerPage": 200,
                                "numericFilters": f"created_at_i>{since},points>{min_points}"})
    except FetchError as exc:
        log.warning("HN fetch failed: %s", exc)
        return []
    items = []
    for hit in data.get("hits", []):
        url = hit.get("url")
        items.append({
            "source": "hackernews",
            "title": hit.get("title") or "",
            "url": url or f"https://news.ycombinator.com/item?id={hit['objectID']}",
            "discussion_url": f"https://news.ycombinator.com/item?id={hit['objectID']}",
            "points": hit.get("points") or 0,
            "comments": hit.get("num_comments") or 0,
            "created_at": hit.get("created_at"),
            "repo": repo_from_url(url),
            "audience": "developers",
            "community": "Hacker News",
        })
    items.sort(key=lambda x: -x["points"])
    log.info("hackernews: %d stories", len(items))
    return items


# Runs inside the Reddit page: scroll to load more posts, then read <shreddit-post> attributes.
REDDIT_DOM_JS = """(async () => {
  for (let i = 0; i < %(scrolls)d; i++) {
    window.scrollTo(0, document.body.scrollHeight);
    await new Promise(r => setTimeout(r, 1200));
  }
  return [...document.querySelectorAll('shreddit-post')].map(p => ({
    title: p.getAttribute('post-title'), score: +p.getAttribute('score') || 0,
    comments: +p.getAttribute('comment-count') || 0, permalink: p.getAttribute('permalink'),
    href: p.getAttribute('content-href'), created: p.getAttribute('created-timestamp'),
    nsfw: p.hasAttribute('nsfw'), promoted: p.hasAttribute('promoted') || p.getAttribute('post-type') === 'ad'
  }));
})()"""


def _reddit_via_browser(client, sub: str, limit: int) -> list[dict]:
    posts = client.scrape(f"https://www.reddit.com/r/{sub}/top/?t=day", REDDIT_DOM_JS % {"scrolls": 3})
    out = []
    for p in (posts or [])[:limit]:
        if not p.get("title") or p.get("nsfw") or p.get("promoted"):
            continue
        out.append({
            "title": p["title"], "url": p.get("href") or "", "permalink": p.get("permalink") or "",
            "score": p.get("score", 0), "num_comments": p.get("comments", 0),
            "created_iso": p.get("created"),
        })
    return out


def fetch_reddit(limit_per_sub: int = 15) -> list[dict]:
    if not CONFIG.reddit_enabled:
        return []
    client = camofox()
    items = []
    for sub, audience in SUBREDDITS.items():
        if client is not None:
            # Reddit's .json API now rejects logged-out clients, even real browsers;
            # the rendered page works, so read posts from the DOM.
            try:
                for p in _reddit_via_browser(client, sub, limit_per_sub):
                    link = p["url"]
                    items.append({
                        "source": "reddit", "title": p["title"],
                        "url": link if link.startswith("http") else f"https://www.reddit.com{p['permalink']}",
                        "discussion_url": f"https://www.reddit.com{p['permalink']}",
                        "points": p["score"], "comments": p["num_comments"],
                        "created_at": p["created_iso"],
                        "repo": repo_from_url(link), "audience": audience, "community": f"r/{sub}",
                    })
            except Exception as exc:
                log.warning("reddit r/%s via camofox failed: %s", sub, exc)
            continue
        url = f"https://www.reddit.com/r/{sub}/top.json"
        try:
            data = get_json_with_fallback(url, params={"t": "day", "limit": limit_per_sub, "raw_json": 1})
        except Exception as exc:  # reddit often blocks scripts/datacenter IPs; never fail the run
            log.warning("reddit r/%s failed: %s", sub, exc)
            continue
        for child in (data.get("data") or {}).get("children", []):
            p = child.get("data", {})
            if p.get("stickied") or p.get("over_18"):
                continue
            link = p.get("url_overridden_by_dest") or p.get("url")
            items.append({
                "source": "reddit",
                "title": p.get("title") or "",
                "url": link,
                "discussion_url": f"https://www.reddit.com{p.get('permalink', '')}",
                "points": p.get("score") or 0,
                "comments": p.get("num_comments") or 0,
                "created_at": datetime.fromtimestamp(p.get("created_utc", 0), timezone.utc).isoformat(),
                "repo": repo_from_url(link) or repo_from_url(p.get("selftext")),
                "audience": audience,
                "community": f"r/{sub}",
            })
        time.sleep(1.5)
    log.info("reddit: %d posts", len(items))
    return items
