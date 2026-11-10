"""The daily build: collect -> merge -> score -> classify -> analyze -> publish."""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone

from . import ai, history, report
from .categories import BY_ID, CATEGORIES, STUDENTS_ID, classify
from .config import CONFIG
from .net import close_camofox
from .sources import discussions as disc
from .sources import github as gh

log = logging.getLogger("trendforge.pipeline")

MAX_REPOS_OUT = 300


def _merge(repos: dict[str, dict], item: dict, source: str) -> dict:
    key = item["full_name"].lower()
    cur = repos.get(key)
    if cur is None:
        cur = repos[key] = {**item, "sources": []}
    else:
        for k, v in item.items():
            if v not in (None, "", [], 0) and (cur.get(k) in (None, "", [], 0) or k in {"stars", "forks"}):
                cur[k] = max(cur.get(k) or 0, v) if k in {"stars", "forks"} else v
    if source not in cur["sources"]:
        cur["sources"].append(source)
    return cur


def _age_days(iso: str | None, now: datetime) -> float | None:
    if not iso:
        return None
    try:
        return max((now - datetime.fromisoformat(iso.replace("Z", "+00:00"))).total_seconds() / 86400, 0.5)
    except ValueError:
        return None


def collect(now: datetime) -> tuple[dict[str, dict], list[dict], set[str]]:
    repos: dict[str, dict] = {}

    # 1) GitHub Trending (daily + weekly + a couple of language pages)
    for item in gh.fetch_trending("daily"):
        r = _merge(repos, item, "trending-daily")
        r["gain_1d_trending"] = item["period_stars"]
        r["trending_rank"] = item["trending_rank"]
    for item in gh.fetch_trending("weekly"):
        r = _merge(repos, item, "trending-weekly")
        r["gain_7d_trending"] = item["period_stars"]
    for lang in ("python", "typescript", "rust", "jupyter-notebook"):
        for item in gh.fetch_trending("daily", lang):
            r = _merge(repos, item, "trending-daily")
            r["gain_1d_trending"] = max(r.get("gain_1d_trending") or 0, item["period_stars"])

    # 2) GitHub Search (new + per-category + student queries)
    good_first: set[str] = set()
    for label, items in gh.fetch_search_signals().items():
        for item in items:
            r = _merge(repos, item, f"search:{label}")
            if label == "good-first-issues":
                good_first.add(r["full_name"].lower())

    # 3) Community discussions
    try:
        talk = disc.fetch_hackernews() + disc.fetch_reddit()
    finally:
        close_camofox()
    mentioned: dict[str, list[dict]] = {}
    for d in talk:
        if d.get("repo"):
            mentioned.setdefault(d["repo"].lower(), []).append(d)

    # 4) Enrich: topics/created_at for trending repos, and repos only seen in discussions
    budget = 120 if CONFIG.github_token else 25
    need = [r for r in repos.values() if not r.get("created_at")]
    need += [{"full_name": name} for name in mentioned if name not in repos]
    for r in need[:budget]:
        details = gh.repo_details(r["full_name"])
        if details:
            _merge(repos, details, "api")
    for name, posts in mentioned.items():
        if name in repos:
            r = repos[name]
            r["mentions"] = [{k: p[k] for k in ("community", "title", "discussion_url", "points")} for p in posts]
            for p in posts:
                r.setdefault("sources", []).append(p["source"])
    return repos, talk, good_first


def score_and_classify(repos: dict[str, dict], now: datetime) -> list[dict]:
    today = now.date()
    snap1, _ = history.snapshot_near(today, 1)
    snap7, days7 = history.snapshot_near(today, 7)
    out = []
    for r in repos.values():
        name = r["full_name"]
        stars = r.get("stars") or 0
        g1 = r.pop("gain_1d_trending", None)
        if g1 is None and name in snap1:
            g1 = stars - snap1[name]
        g7 = r.pop("gain_7d_trending", None)
        if g7 is None and name in snap7:
            g7 = stars - snap7[name]
        age = _age_days(r.get("created_at"), now)
        velocity = stars / age if age is not None and age < 120 else 0.0
        hn = sum(m["points"] for m in r.get("mentions", []) if m["community"] == "Hacker News")
        rd = sum(m["points"] for m in r.get("mentions", []) if m["community"].startswith("r/"))
        r["gain_1d"] = g1
        r["gain_7d"] = g7
        r["velocity"] = round(velocity, 1)
        r["age_days"] = round(age) if age is not None else None
        r["score"] = round(
            (g1 or 0) + 0.25 * (g7 or 0) + 0.5 * min(velocity, 2000) + 0.3 * hn + 0.1 * rd
            + math.log10(stars + 1), 1)
        r["sources"] = sorted(set(r.get("sources", [])))
        r["url"] = f"https://github.com/{name}"
        r.update(classify(name, r.get("description"), r.get("topics")))
        out.append(r)
    out.sort(key=lambda x: -x["score"])
    return out


def build_categories(ranked: list[dict], talk: list[dict], now: datetime, trends: dict) -> tuple[list[dict], dict, dict]:
    repos_by_cat: dict[str, list[dict]] = {c.id: [] for c in CATEGORIES}
    for r in ranked:
        for tag in r["tags"]:
            repos_by_cat.setdefault(tag, []).append(r)

    talk_by_cat: dict[str, list[dict]] = {c.id: [] for c in CATEGORIES}
    for d in talk:
        cls = classify(d["title"], "", [])
        for tag in cls["tags"]:
            talk_by_cat.setdefault(tag, []).append(d)
        if d["audience"] == "students" and STUDENTS_ID not in cls["tags"]:
            talk_by_cat[STUDENTS_ID].append(d)
    for lst in talk_by_cat.values():
        lst.sort(key=lambda x: -x["points"])

    cats = []
    for c in CATEGORIES:
        members = repos_by_cat.get(c.id, [])
        momentum = sum(r["score"] for r in members[:25])
        prev = history.momentum_days_ago(trends, c.id, now.date(), 7)
        growth = round((momentum - prev) / prev * 100, 1) if prev else None
        cats.append({
            "id": c.id, "name": c.name, "description": c.description,
            "repo_count": len(members), "momentum": round(momentum, 1), "growth_pct": growth,
            "top_repos": [r["full_name"] for r in members[:5]],
            "discussion_count": len(talk_by_cat.get(c.id, [])),
        })
    cats.sort(key=lambda x: -x["momentum"])
    return cats, repos_by_cat, talk_by_cat


def _public_repo(r: dict) -> dict:
    keep = ("full_name", "url", "description", "language", "stars", "forks", "topics", "created_at",
            "license", "homepage", "gain_1d", "gain_7d", "velocity", "age_days", "score", "category",
            "tags", "for_students", "sources", "mentions", "trending_rank", "good_first_issues", "ai")
    out = {k: r.get(k) for k in keep if r.get(k) not in (None, [], "")}
    if "ai" in out:
        out["ai"] = {k: v for k, v in out["ai"].items() if k != "analyzed_at"}
    return out


def run(*, use_ai: bool = True) -> dict:
    now = datetime.now(timezone.utc)
    log.info("TrendForge build starting %s", now.isoformat(timespec="seconds"))

    repos, talk, good_first = collect(now)
    ranked = score_and_classify(repos, now)
    for r in ranked:
        if r["full_name"].lower() in good_first:
            r["good_first_issues"] = True
            r["for_students"] = True
            if STUDENTS_ID not in r["tags"]:
                r["tags"].append(STUDENTS_ID)

    trends = history.load_trends()
    categories, repos_by_cat, talk_by_cat = build_categories(ranked, talk, now, trends)

    # Pick what we publish: top by score + the best student resources
    student_repos = sorted(repos_by_cat[STUDENTS_ID], key=lambda r: (-(r.get("gain_7d") or 0), -r["stars"]))
    published = {r["full_name"]: r for r in ranked[:MAX_REPOS_OUT]}
    for r in student_repos[:80]:
        published.setdefault(r["full_name"], r)
    pub_list = sorted(published.values(), key=lambda r: -r["score"])

    ai_result = ai.run_ai(pub_list, [c["id"] for c in categories], repos_by_cat, talk_by_cat, enabled=use_ai)
    for c in categories:
        if c["id"] in ai_result["categories"]:
            c["analysis"] = ai_result["categories"][c["id"]]

    payload = {
        "generated_at": now.isoformat(timespec="seconds"),
        "ai_enabled": ai_result["enabled"] or bool(ai_result["categories"]),
        "ai": {k: ai_result[k] for k in ("backend", "repos_analyzed", "categories_analyzed", "usage")},
        "stats": {
            "repos_tracked": len(ranked),
            "repos_published": len(pub_list),
            "discussions": len(talk),
            "sources": sorted({s.split(":")[0] for r in ranked for s in r["sources"]}),
        },
        "categories": categories,
        "repos": [_public_repo(r) for r in pub_list],
        "discussions": talk[:150],
        "students": {
            "learning": [r["full_name"] for r in student_repos if not r.get("good_first_issues")][:40],
            "contribute": [r["full_name"] for r in student_repos if r.get("good_first_issues")][:30],
            "discussions": [d for d in talk_by_cat[STUDENTS_ID]][:30],
        },
    }

    # Publish
    history.write_json(CONFIG.data_dir / "latest.json", payload, compact=True)
    history.save_snapshot(now.date(), {r["full_name"]: r["stars"] for r in ranked})
    momentum = {c["id"]: c["momentum"] for c in categories}
    history.write_json(CONFIG.data_dir / "trends.json", history.update_trends(trends, now.date(), momentum), compact=True)
    report.write_reports(payload)
    log.info("done: %d repos tracked, %d published, %d discussions",
             len(ranked), len(pub_list), len(talk))
    return payload


def category_name(cid: str) -> str:
    return BY_ID[cid].name if cid in BY_ID else cid.title()
