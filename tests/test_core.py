from datetime import date

from trendforge.categories import classify
from trendforge.history import update_trends
from trendforge.sources.discussions import repo_from_url
from trendforge.sources.github import parse_trending_html

TRENDING_HTML = """
<article class="Box-row">
  <h2 class="h3 lh-condensed"><a href="/acme/browser-pilot">acme / browser-pilot</a></h2>
  <p class="col-9 color-fg-muted my-1 pr-4">An open-source browser agent built on Playwright</p>
  <div class="f6">
    <span itemprop="programmingLanguage">Python</span>
    <a href="/acme/browser-pilot/stargazers">12,345</a>
    <a href="/acme/browser-pilot/forks">678</a>
    <span class="d-inline-block float-sm-right">1,024 stars today</span>
  </div>
</article>
<article class="Box-row">
  <h2><a href="/kim/learn-rust">kim / learn-rust</a></h2>
  <div class="f6"><a href="/kim/learn-rust/stargazers">900</a></div>
</article>
"""


def test_parse_trending_html():
    repos = parse_trending_html(TRENDING_HTML)
    assert [r["full_name"] for r in repos] == ["acme/browser-pilot", "kim/learn-rust"]
    first = repos[0]
    assert first["stars"] == 12345 and first["forks"] == 678
    assert first["period_stars"] == 1024 and first["language"] == "Python"
    assert first["trending_rank"] == 1
    assert repos[1]["description"] == "" and repos[1]["period_stars"] == 0


def test_classify_browser_agent():
    out = classify("browser-pilot", "An open-source browser agent built on Playwright", ["browser-automation"])
    assert out["category"] == "browser-agents"
    assert not out["for_students"]


def test_classify_students():
    out = classify("system-design-primer", "Learn how to design large-scale systems. Prep for the system design interview.",
                   ["interview-questions", "education"])
    assert out["for_students"]
    assert "students" in out["tags"]


def test_machine_learning_is_not_a_student_signal():
    out = classify("fast-trainer", "Deep learning training library for PyTorch", ["deep-learning"])
    assert out["category"] == "ml-research"
    assert not out["for_students"]


def test_mcp_topic():
    out = classify("github-mcp-server", "GitHub's official MCP Server", ["mcp", "mcp-server"])
    assert out["category"] == "mcp"


def test_repo_from_url():
    assert repo_from_url("https://github.com/owner/repo/tree/main") == "owner/repo"
    assert repo_from_url("https://github.com/owner/repo.git") == "owner/repo"
    assert repo_from_url("https://github.com/topics/ai") is None
    assert repo_from_url("https://example.com") is None


def test_update_trends_same_day_overwrites():
    t = update_trends({"dates": [], "categories": {}}, date(2026, 1, 1), {"a": 1})
    t = update_trends(t, date(2026, 1, 2), {"a": 2, "b": 5})
    t = update_trends(t, date(2026, 1, 2), {"a": 3, "b": 6})
    assert t["dates"] == ["2026-01-01", "2026-01-02"]
    assert t["categories"]["a"] == [1, 3]
    assert t["categories"]["b"] == [None, 6]


def test_inline_refs_has_no_refs():
    import json
    from trendforge.ai import CategoryBatch, _inline_refs
    schema = _inline_refs(CategoryBatch.model_json_schema())
    text = json.dumps(schema)
    assert "$ref" not in text and "$defs" not in text
    assert schema["additionalProperties"] is False
    idea = schema["properties"]["items"]["items"]["properties"]["analysis"]["properties"]["ideas"]["items"]
    # every required field must be defined (regression: a field named "title" was stripped)
    assert set(idea["required"]) <= set(idea["properties"])
    assert "title" in idea["properties"]


def test_ai_due_weekly():
    from datetime import datetime, timedelta, timezone
    from trendforge import ai
    object.__setattr__(ai.CONFIG, "ai_interval_days", 7)
    now = datetime.now(timezone.utc)
    assert ai._ai_due({}) is True
    assert ai._ai_due({"last_run": (now - timedelta(days=2)).isoformat()}) is False
    assert ai._ai_due({"last_run": (now - timedelta(days=7, hours=-1)).isoformat()}) is True
    object.__setattr__(ai.CONFIG, "ai_interval_days", 1)
    assert ai._ai_due({"last_run": now.isoformat()}) is True
    object.__setattr__(ai.CONFIG, "ai_interval_days", 7)
