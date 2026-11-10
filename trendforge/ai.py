"""Optional AI intelligence layer powered by Claude.

* Repo insights: what a repo does, the problem it solves, who it is for and
  what a student could learn from it. Cached per repo (re-analyzed monthly),
  so a daily run only pays for repos that are new to the dataset.
* Category analysis ("Build Opportunity"): why a topic is trending, what
  already exists, gaps, and concrete project ideas. One call per category/day.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Literal

from pydantic import BaseModel, Field

from .categories import BY_ID, CATEGORIES, STUDENTS_ID
from .config import CONFIG
from .history import write_json
from .sources.github import readme_excerpt

log = logging.getLogger("trendforge.ai")

CATEGORY_IDS = [c.id for c in CATEGORIES] + ["other"]
CACHE_PATH = CONFIG.cache_dir / "repo_insights.json"
CACHE_TTL = timedelta(days=30)
BATCH_SIZE = 8


# ---------------------------------------------------------------------------
# Output schemas (validated via structured outputs)
# ---------------------------------------------------------------------------

class RepoInsight(BaseModel):
    full_name: str
    summary: str = Field(description="One plain-English sentence: what this project is.")
    problem: str = Field(description="One sentence: the concrete problem it solves and for whom.")
    audience: Literal["developers", "students", "both"]
    student_angle: str = Field(description="One sentence on what a student can learn or build with it; empty if none.")
    category: str = Field(description="Best-fitting category id from the provided list.")


class RepoInsightBatch(BaseModel):
    items: list[RepoInsight]


class BuildIdea(BaseModel):
    title: str
    pitch: str = Field(description="2 sentences: what to build and who uses it.")
    why_now: str = Field(description="1 sentence tying it to evidence in the trend data.")
    difficulty: Literal["beginner", "intermediate", "advanced"]
    good_for_students: bool


class CategoryAnalysis(BaseModel):
    why_trending: str = Field(description="2-3 sentences, grounded in the repos/discussions given.")
    what_exists: str = Field(description="2 sentences summarizing the solutions that already exist.")
    gaps: list[str] = Field(description="3-5 specific unmet needs or recurring complaints.")
    ideas: list[BuildIdea] = Field(description="Exactly 3 complementary tools worth building.")


SYSTEM = (
    "You are the analyst behind TrendForge, an open-source dashboard that helps developers and "
    "students understand what is trending in software and decide what to build next. "
    "Write plainly and concretely for a smart reader new to the topic. Base every claim only on "
    "the data provided; do not invent stars, users, companies or features. If the data is thin, "
    "say less rather than guessing."
)


# ---------------------------------------------------------------------------
# Client plumbing
# ---------------------------------------------------------------------------

class _AIDisabled(Exception):
    pass


def ai_enabled() -> bool:
    if CONFIG.ai_mode in {"off", "0", "false", "no"}:
        return False
    if CONFIG.ai_mode in {"on", "1", "true", "yes"}:
        return True
    return CONFIG.has_anthropic_key  # auto


def _client():
    import anthropic
    return anthropic.Anthropic()


def _parse(client, prompt: str, schema: type[BaseModel]) -> BaseModel | None:
    import anthropic

    try:
        # Server-side fallback: if a request is declined by a safety classifier, the API
        # transparently retries it on a suitable fallback model inside the same call.
        resp = client.beta.messages.parse(
            model=CONFIG.ai_model,
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": "low"},
            system=SYSTEM,
            messages=[{"role": "user", "content": prompt}],
            output_format=schema,
        )
    except anthropic.AuthenticationError as exc:
        raise _AIDisabled(f"authentication failed: {exc}") from exc
    except anthropic.PermissionDeniedError as exc:
        raise _AIDisabled(f"permission denied: {exc}") from exc
    except anthropic.RateLimitError as exc:
        raise _AIDisabled(f"rate limited, stopping AI for this run: {exc}") from exc
    except anthropic.APIStatusError as exc:
        log.warning("Claude API error %s: %s", exc.status_code, exc.message)
        return None
    except anthropic.APIConnectionError as exc:
        log.warning("Claude API connection error: %s", exc)
        return None

    if resp.stop_reason == "refusal":
        log.warning("request declined (%s); skipping", getattr(resp.stop_details, "category", None))
        return None
    if resp.stop_reason == "max_tokens":
        log.warning("response truncated at max_tokens; skipping")
        return None
    return resp.parsed_output


# ---------------------------------------------------------------------------
# Repo insights
# ---------------------------------------------------------------------------

def _load_cache() -> dict:
    if CACHE_PATH.exists():
        try:
            return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def _fresh(entry: dict) -> bool:
    try:
        return datetime.now(timezone.utc) - datetime.fromisoformat(entry["analyzed_at"]) < CACHE_TTL
    except (KeyError, ValueError):
        return False


def apply_cached_insights(repos: list[dict]) -> dict:
    cache = _load_cache()
    for r in repos:
        if r["full_name"] in cache:
            r["ai"] = cache[r["full_name"]]
    return cache


def analyze_repos(client, repos: list[dict], cache: dict) -> int:
    todo = [r for r in repos if not _fresh(cache.get(r["full_name"], {}))][: CONFIG.ai_max_new_repos]
    cat_list = ", ".join(f"{c.id} ({c.name})" for c in CATEGORIES) + ", other"
    done = 0
    for i in range(0, len(todo), BATCH_SIZE):
        batch = todo[i: i + BATCH_SIZE]
        blocks = []
        for r in batch:
            readme = readme_excerpt(r["full_name"], limit=1800)
            blocks.append(
                f"<repo name=\"{r['full_name']}\">\n"
                f"description: {r.get('description') or '-'}\n"
                f"language: {r.get('language') or '-'} | stars: {r.get('stars')} | topics: {', '.join(r.get('topics') or []) or '-'}\n"
                f"readme_excerpt:\n{readme or '-'}\n</repo>"
            )
        prompt = (
            f"Analyze each repository below. Categories: {cat_list}.\n"
            "Return one item per repository, using its exact full_name.\n\n" + "\n\n".join(blocks)
        )
        result = _parse(client, prompt, RepoInsightBatch)
        if result is None:
            continue
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        wanted = {r["full_name"].lower(): r for r in batch}
        for item in result.items:
            repo = wanted.get(item.full_name.lower())
            if repo is None:
                continue
            data = item.model_dump(exclude={"full_name"})
            if data["category"] not in CATEGORY_IDS:
                data["category"] = repo.get("category", "other")
            data["analyzed_at"] = now
            cache[repo["full_name"]] = data
            repo["ai"] = data
            done += 1
        write_json(CACHE_PATH, cache)
    return done


# ---------------------------------------------------------------------------
# Category "Build Opportunity" analysis
# ---------------------------------------------------------------------------

def _category_prompt(cat_id: str, repos: list[dict], discussions: list[dict]) -> str:
    cat = BY_ID.get(cat_id)
    lines = []
    for r in repos[:15]:
        ai = r.get("ai") or {}
        gain = r.get("gain_1d") or r.get("gain_7d")
        lines.append(
            f"- {r['full_name']} ({r['stars']}★{f', +{gain} recently' if gain else ''}): "
            f"{ai.get('summary') or r.get('description') or '-'}"
        )
    talk = [f"- [{d['community']}, {d['points']} pts] {d['title']}" for d in discussions[:12]]
    audience = (
        "The audience is STUDENTS: favour portfolio-worthy, learnable projects that teach in-demand skills; "
        "at least two ideas must be beginner or intermediate."
        if cat_id == STUDENTS_ID else
        "The audience is developers and students looking for open-source tools worth building that "
        "complement (not clone) what exists."
    )
    return (
        f"Category: {cat.name if cat else cat_id} — {cat.description if cat else ''}\n{audience}\n\n"
        f"Trending repositories:\n" + "\n".join(lines) +
        ("\n\nRelated community discussions:\n" + "\n".join(talk) if talk else "") +
        "\n\nExplain why this area is gaining momentum, what already exists, the gaps, and three "
        "complementary tools worth building."
    )


def analyze_categories(client, ranked: list[str], repos_by_cat: dict[str, list[dict]],
                       talk_by_cat: dict[str, list[dict]]) -> dict[str, dict]:
    out = {}
    for cat_id in ranked[: CONFIG.ai_max_categories]:
        repos = repos_by_cat.get(cat_id, [])
        if len(repos) < 3:
            continue
        result = _parse(client, _category_prompt(cat_id, repos, talk_by_cat.get(cat_id, [])), CategoryAnalysis)
        if result is not None:
            out[cat_id] = result.model_dump()
    return out


def run_ai(repos: list[dict], ranked_categories: list[str], repos_by_cat: dict, talk_by_cat: dict) -> dict:
    """Returns {'enabled': bool, 'repos_analyzed': int, 'categories': {...}}."""
    cache = apply_cached_insights(repos)
    if not ai_enabled():
        log.info("AI layer off (set ANTHROPIC_API_KEY or TRENDFORGE_AI=on to enable)")
        return {"enabled": False, "repos_analyzed": 0, "categories": {}}
    client = _client()
    try:
        n = analyze_repos(client, repos, cache)
        log.info("AI: analyzed %d new repos", n)
        cats = analyze_categories(client, ranked_categories, repos_by_cat, talk_by_cat)
        log.info("AI: analyzed %d categories", len(cats))
        return {"enabled": True, "repos_analyzed": n, "categories": cats}
    except _AIDisabled as exc:
        log.warning("AI layer disabled for this run: %s", exc)
        return {"enabled": False, "repos_analyzed": 0, "categories": {}}
