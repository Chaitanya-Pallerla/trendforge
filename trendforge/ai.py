"""Optional AI intelligence layer powered by Claude — built to spend as few tokens as possible.

Backends
  cli  Your Claude account through the Claude Code CLI (`claude -p`). No API key. Each call
       replaces Claude Code's default system prompt with a short one and disables tools, MCP
       servers and slash commands, so a call costs ~1.5k tokens of overhead.
  api  Anthropic API key (ANTHROPIC_API_KEY) via the SDK — used by the cloud backup run.

Token budget per daily run (typical)
  * Repo insights: only repos never seen before (or older than 60 days), batched ~25 per call,
    with a short README excerpt only when the description is too thin to go on.
  * Topic "Build opportunity": reused until a topic's leading repos really change or the analysis
    is 7 days old; every stale topic goes into ONE call.
  => usually 1-2 calls/day. Everything is cached in data/cache/ (committed to git), so days
     without AI still show the insights.
"""

from __future__ import annotations

import glob
import json
import logging
import os
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from .categories import BY_ID, CATEGORIES, STUDENTS_ID
from .config import CONFIG
from .history import write_json
from .sources.github import readme_excerpt

log = logging.getLogger("trendforge.ai")

CATEGORY_IDS = [c.id for c in CATEGORIES] + ["other"]
REPO_CACHE = CONFIG.cache_dir / "repo_insights.json"
CAT_CACHE = CONFIG.cache_dir / "category_analysis.json"
REPO_TTL = timedelta(days=60)
CAT_TTL = timedelta(days=6)   # < the weekly AI interval, so each weekly run refreshes topics
CAT_MIN_OVERLAP = 5          # of the top 8 repos; fewer shared => topic changed, re-analyze
REPO_BATCH = 25
README_CHARS = 500
THIN_DESCRIPTION = 60        # chars; below this we add a README excerpt


# ---------------------------------------------------------------------------
# Output schemas
# ---------------------------------------------------------------------------

class RepoInsight(BaseModel):
    full_name: str
    summary: str = Field(description="One plain sentence: what it is.")
    problem: str = Field(description="One short sentence: the problem it solves, for whom.")
    audience: Literal["developers", "students", "both"]
    student_angle: str = Field(description="One short sentence on what a student learns from it, or empty string.")
    category: str = Field(description="Category id from the list.")


class RepoInsightBatch(BaseModel):
    items: list[RepoInsight]


class BuildIdea(BaseModel):
    title: str
    pitch: str = Field(description="2 sentences: what to build and who uses it.")
    why_now: str = Field(description="1 sentence tied to the trend data.")
    difficulty: Literal["beginner", "intermediate", "advanced"]
    good_for_students: bool


class CategoryAnalysis(BaseModel):
    why_trending: str = Field(description="2-3 sentences grounded in the data given.")
    what_exists: str = Field(description="2 sentences on existing solutions.")
    gaps: list[str] = Field(description="3-5 specific unmet needs.")
    ideas: list[BuildIdea] = Field(description="Exactly 3 complementary tools worth building.")


class CategoryResult(BaseModel):
    category_id: str
    analysis: CategoryAnalysis


class CategoryBatch(BaseModel):
    items: list[CategoryResult]


SYSTEM = (
    "You are the analyst behind TrendForge, an open-source dashboard helping developers and students "
    "see what is trending in software and decide what to build. Write plainly and concisely. Use only "
    "the data provided; never invent numbers, users or features. Reply only with the requested JSON."
)


# ---------------------------------------------------------------------------
# Backends
# ---------------------------------------------------------------------------

class AIDisabled(Exception):
    pass


def _inline_refs(schema: dict) -> dict:
    """Pydantic emits $defs/$ref; inline them so any JSON-schema consumer accepts it."""
    defs = schema.pop("$defs", {})

    def walk(node, is_properties_map: bool = False):
        if isinstance(node, dict):
            if is_properties_map:  # keys here are field names (a field may be called "title")
                return {k: walk(v) for k, v in node.items()}
            if "$ref" in node:
                return walk(dict(defs[node["$ref"].split("/")[-1]]))
            # drop pydantic's "title" *annotation* (a string), never a field definition
            out = {k: walk(v, is_properties_map=(k == "properties"))
                   for k, v in node.items() if not (k == "title" and isinstance(v, str))}
            if out.get("type") == "object":
                out.setdefault("additionalProperties", False)
            return out
        if isinstance(node, list):
            return [walk(v) for v in node]
        return node

    return walk(schema)


def find_claude_cli() -> str | None:
    if CONFIG.claude_cli and Path(CONFIG.claude_cli).exists():
        return CONFIG.claude_cli
    found = shutil.which("claude")
    if found:
        return found
    # Claude Code bundled with the VS Code extension (newest version first)
    home = Path.home()
    patterns = [str(home / ".vscode" / "extensions" / "anthropic.claude-code-*" / "resources" / "native-binary" / "claude*"),
                str(home / ".local" / "bin" / "claude*")]
    hits = [p for pat in patterns for p in glob.glob(pat) if p.lower().endswith(("claude.exe", "claude"))]
    hits.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return hits[0] if hits else None


class Usage:
    def __init__(self):
        self.calls = 0
        self.input_tokens = 0
        self.output_tokens = 0

    def add(self, inp: int, out: int):
        self.calls += 1
        self.input_tokens += inp
        self.output_tokens += out

    def as_dict(self) -> dict:
        return {"calls": self.calls, "input_tokens": self.input_tokens, "output_tokens": self.output_tokens}


class CliBackend:
    name = "cli"

    def __init__(self, exe: str, usage: Usage):
        self.exe = exe
        self.usage = usage
        self.cwd = CONFIG.cache_dir / "cli-workdir"   # empty dir: no CLAUDE.md / project settings picked up
        self.cwd.mkdir(parents=True, exist_ok=True)

    def ask(self, prompt: str, schema: type[BaseModel]) -> BaseModel | None:
        cmd = [self.exe, "-p", "--output-format", "json",
               "--json-schema", json.dumps(_inline_refs(schema.model_json_schema())),
               "--system-prompt", SYSTEM, "--exclude-dynamic-system-prompt-sections",
               "--tools", "", "--strict-mcp-config", "--disable-slash-commands",
               "--no-session-persistence", "--effort", CONFIG.ai_effort]
        if CONFIG.ai_model:
            cmd += ["--model", CONFIG.ai_model]
        try:
            proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding="utf-8",
                                  timeout=900, cwd=self.cwd)
        except subprocess.TimeoutExpired:
            log.warning("claude CLI timed out")
            return None
        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError:
            msg = (proc.stderr or proc.stdout)[-300:]
            if "login" in msg.lower() or "auth" in msg.lower():
                raise AIDisabled(f"Claude CLI not logged in: {msg}")
            log.warning("claude CLI returned non-JSON (rc=%s): %s", proc.returncode, msg)
            return None
        u = data.get("usage") or {}
        self.usage.add(u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
                       + u.get("cache_read_input_tokens", 0), u.get("output_tokens", 0))
        log.info("claude call: %s turns, stop=%s/%s, input=%s cache_write=%s cache_read=%s output=%s",
                 data.get("num_turns"), data.get("subtype"), data.get("terminal_reason") or data.get("stop_reason"),
                 u.get("input_tokens"), u.get("cache_creation_input_tokens"), u.get("cache_read_input_tokens"),
                 u.get("output_tokens"))
        (CONFIG.cache_dir / "last_cli_response.json").write_text(proc.stdout, encoding="utf-8")
        if data.get("is_error"):
            text = str(data.get("result", ""))[:300]
            if data.get("api_error_status") in (401, 403) or "login" in text.lower():
                raise AIDisabled(f"Claude CLI auth problem: {text}")
            if data.get("api_error_status") == 429 or "limit" in text.lower():
                raise AIDisabled(f"usage limit reached, stopping AI for this run: {text}")
            log.warning("claude CLI error: %s", text)
            return None
        payload = data.get("structured_output")
        if payload is None:
            try:
                payload = json.loads(data.get("result") or "")
            except (TypeError, json.JSONDecodeError):
                log.warning("claude CLI returned no structured output")
                return None
        try:
            return schema.model_validate(payload)
        except ValidationError as exc:
            log.warning("claude CLI output failed validation: %s", str(exc)[:300])
            return None


class ApiBackend:
    name = "api"

    def __init__(self, usage: Usage):
        import anthropic
        self.client = anthropic.Anthropic()
        self.usage = usage

    def ask(self, prompt: str, schema: type[BaseModel]) -> BaseModel | None:
        import anthropic
        try:
            resp = self.client.beta.messages.parse(
                model=CONFIG.ai_model or "claude-opus-5-5",
                max_tokens=16000,
                # Server-side fallback: a request declined by a safety classifier is retried
                # on a suitable fallback model inside the same call.
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
                output_config={"effort": CONFIG.ai_effort},
                system=SYSTEM,
                messages=[{"role": "user", "content": prompt}],
                output_format=schema,
            )
        except (anthropic.AuthenticationError, anthropic.PermissionDeniedError) as exc:
            raise AIDisabled(f"API auth failed: {exc}") from exc
        except anthropic.RateLimitError as exc:
            raise AIDisabled(f"rate limited: {exc}") from exc
        except anthropic.APIStatusError as exc:
            log.warning("Claude API error %s: %s", exc.status_code, exc.message)
            return None
        except anthropic.APIConnectionError as exc:
            log.warning("Claude API connection error: %s", exc)
            return None
        self.usage.add(resp.usage.input_tokens, resp.usage.output_tokens)
        if resp.stop_reason in ("refusal", "max_tokens"):
            log.warning("request ended with %s; skipping", resp.stop_reason)
            return None
        return resp.parsed_output


def make_backend(usage: Usage):
    if CONFIG.ai_mode in {"off", "0", "false", "no"}:
        return None
    want = CONFIG.ai_backend
    if want in {"auto", "cli"}:
        exe = find_claude_cli()
        if exe:
            log.info("AI backend: Claude account via Claude Code CLI (%s)", exe)
            return CliBackend(exe, usage)
        if want == "cli":
            log.warning("TRENDFORGE_AI_BACKEND=cli but no Claude Code CLI found (set CLAUDE_CLI)")
            return None
    if want in {"auto", "api"} and (CONFIG.has_anthropic_key or CONFIG.ai_mode in {"on", "1", "true", "yes"}):
        log.info("AI backend: Anthropic API")
        return ApiBackend(usage)
    return None


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def _load(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def _age_ok(entry: dict, ttl: timedelta) -> bool:
    try:
        return datetime.now(timezone.utc) - datetime.fromisoformat(entry["analyzed_at"]) < ttl
    except (KeyError, ValueError, TypeError):
        return False


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Repo insights
# ---------------------------------------------------------------------------

def _repo_line(r: dict) -> str:
    desc = (r.get("description") or "").strip()
    topics = ",".join((r.get("topics") or [])[:6])
    line = f"- {r['full_name']} | {r.get('language') or '-'} | {desc or '-'}" + (f" | topics: {topics}" if topics else "")
    if len(desc) < THIN_DESCRIPTION:
        readme = readme_excerpt(r["full_name"], limit=README_CHARS).replace("\n", " ")
        if readme:
            line += f"\n  readme: {readme}"
    return line


def analyze_repos(backend, repos: list[dict], cache: dict) -> int:
    todo = [r for r in repos if not _age_ok(cache.get(r["full_name"], {}), REPO_TTL)][: CONFIG.ai_max_new_repos]
    if not todo:
        return 0
    cats = ", ".join(c.id for c in CATEGORIES) + ", other"
    done = 0
    for i in range(0, len(todo), REPO_BATCH):
        batch = todo[i: i + REPO_BATCH]
        prompt = (f"Category ids: {cats}\nFor each repository return one item (exact full_name).\n\n"
                  + "\n".join(_repo_line(r) for r in batch))
        result = backend.ask(prompt, RepoInsightBatch)
        if result is None:
            continue
        wanted = {r["full_name"].lower(): r for r in batch}
        for item in result.items:
            repo = wanted.get(item.full_name.lower())
            if repo is None:
                continue
            data = item.model_dump(exclude={"full_name"})
            if data["category"] not in CATEGORY_IDS:
                data["category"] = repo.get("category", "other")
            data["analyzed_at"] = _now()
            cache[repo["full_name"]] = data
            repo["ai"] = data
            done += 1
        write_json(REPO_CACHE, cache)
    return done


# ---------------------------------------------------------------------------
# Topic "Build opportunity" analysis
# ---------------------------------------------------------------------------

def _top_names(repos: list[dict], n: int = 8) -> list[str]:
    return [r["full_name"] for r in repos[:n]]


def _cat_block(cat_id: str, repos: list[dict], talk: list[dict]) -> str:
    cat = BY_ID.get(cat_id)
    lines = [f"## {cat_id} — {cat.name if cat else cat_id}: {cat.description if cat else ''}"]
    if cat_id == STUDENTS_ID:
        lines.append("(Audience: students. Ideas = portfolio-worthy, learnable projects; >=2 beginner/intermediate.)")
    for r in repos[:10]:
        summary = (r.get("ai") or {}).get("summary") or r.get("description") or "-"
        gain = r.get("gain_1d") or r.get("gain_7d")
        lines.append(f"- {r['full_name']} ({r['stars']}★{f', +{gain}' if gain else ''}): {summary[:160]}")
    for d in talk[:6]:
        lines.append(f"- talk [{d['community']}, {d['points']}pts]: {d['title'][:140]}")
    return "\n".join(lines)


def analyze_categories(backend, ranked: list[str], repos_by_cat: dict, talk_by_cat: dict, cache: dict) -> int:
    stale = []
    for cat_id in ranked[: CONFIG.ai_max_categories]:
        repos = repos_by_cat.get(cat_id, [])
        if len(repos) < 3:
            continue
        entry = cache.get(cat_id, {})
        overlap = len(set(entry.get("repos", [])) & set(_top_names(repos)))
        if _age_ok(entry, CAT_TTL) and overlap >= CAT_MIN_OVERLAP:
            continue
        stale.append(cat_id)
    if not stale:
        return 0
    prompt = ("For each topic below, explain why it is gaining momentum, what already exists, the gaps, "
              "and three complementary tools worth building (not clones). Return one item per topic "
              "with its exact category_id.\n\n"
              + "\n\n".join(_cat_block(c, repos_by_cat[c], talk_by_cat.get(c, [])) for c in stale))
    result = backend.ask(prompt, CategoryBatch)
    if result is None:
        return 0
    n = 0
    for item in result.items:
        if item.category_id in stale:
            cache[item.category_id] = {"analysis": item.analysis.model_dump(),
                                       "repos": _top_names(repos_by_cat[item.category_id]),
                                       "analyzed_at": _now()}
            n += 1
    write_json(CAT_CACHE, cache)
    return n


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

STATE = CONFIG.cache_dir / "ai_state.json"


def _ai_due(state: dict) -> bool:
    if CONFIG.ai_interval_days <= 1:
        return True
    try:
        last = datetime.fromisoformat(state["last_run"])
    except (KeyError, ValueError, TypeError):
        return True
    # small slack so a run at 08:05 still counts as "7 days" after one at 08:10
    return datetime.now(timezone.utc) - last >= timedelta(days=CONFIG.ai_interval_days, hours=-3)


def run_ai(repos: list[dict], ranked_categories: list[str], repos_by_cat: dict, talk_by_cat: dict,
           *, enabled: bool = True, force: bool = False) -> dict:
    """Apply cached insights; if enabled, fill gaps with as few Claude calls as possible."""
    repo_cache, cat_cache = _load(REPO_CACHE), _load(CAT_CACHE)
    usage = Usage()
    state = _load(STATE)
    due = force or _ai_due(state)
    if enabled and not due:
        log.info("AI step skipped (runs every %d days; last run %s). Use --ai-now to force.",
                 CONFIG.ai_interval_days, state.get("last_run", "never"))
    backend = make_backend(usage) if (enabled and due) else None
    status = {"enabled": False, "backend": None, "repos_analyzed": 0, "categories_analyzed": 0,
              "last_run": state.get("last_run"), "interval_days": CONFIG.ai_interval_days}
    if backend is None:
        if enabled:
            log.info("AI layer off: no Claude Code CLI login or API key found")
    else:
        status.update(enabled=True, backend=backend.name)
        try:
            # Apply cache first so category prompts can reuse cached summaries.
            for r in repos:
                if r["full_name"] in repo_cache:
                    r["ai"] = repo_cache[r["full_name"]]
            status["repos_analyzed"] = analyze_repos(backend, repos, repo_cache)
            status["categories_analyzed"] = analyze_categories(backend, ranked_categories, repos_by_cat,
                                                               talk_by_cat, cat_cache)
        except AIDisabled as exc:
            log.warning("AI stopped for this run: %s", exc)
        if usage.calls:
            state["last_run"] = _now()
            write_json(STATE, state)
            status["last_run"] = state["last_run"]
        log.info("AI: %d new repo insights, %d topic analyses, %d calls, %d input + %d output tokens",
                 status["repos_analyzed"], status["categories_analyzed"], usage.calls,
                 usage.input_tokens, usage.output_tokens)
    status["usage"] = usage.as_dict()

    for r in repos:
        if r["full_name"] in repo_cache:
            r["ai"] = repo_cache[r["full_name"]]
    status["categories"] = {cid: e["analysis"] for cid, e in cat_cache.items() if "analysis" in e}
    return status
