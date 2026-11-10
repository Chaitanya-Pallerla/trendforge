"""Central configuration. All environment variable reads live here."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    """Minimal .env loader (no dependency). Never overrides real env vars."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(ROOT / ".env")


def _bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Config:
    # Data sources
    github_token: str = field(default_factory=lambda: os.environ.get("GITHUB_TOKEN", ""))
    reddit_enabled: bool = field(default_factory=lambda: _bool("TRENDFORGE_REDDIT", True))
    hn_enabled: bool = field(default_factory=lambda: _bool("TRENDFORGE_HN", True))

    # camofox-browser fallback (optional) for pages that block plain HTTP clients
    camofox_url: str = field(default_factory=lambda: os.environ.get("CAMOFOX_URL", "").rstrip("/"))
    camofox_api_key: str = field(default_factory=lambda: os.environ.get("CAMOFOX_API_KEY", ""))

    # AI layer (Claude).
    #   TRENDFORGE_AI       auto | on | off   (auto = on when a backend is available)
    #   TRENDFORGE_AI_BACKEND  auto | cli | api
    #     cli = your Claude account via the Claude Code CLI (`claude -p`), no API key needed
    #     api = Anthropic API key (ANTHROPIC_API_KEY), e.g. for the GitHub Actions backup run
    ai_mode: str = field(default_factory=lambda: os.environ.get("TRENDFORGE_AI", "auto").lower())
    ai_backend: str = field(default_factory=lambda: os.environ.get("TRENDFORGE_AI_BACKEND", "auto").lower())
    claude_cli: str = field(default_factory=lambda: os.environ.get("CLAUDE_CLI", ""))
    # Empty = the CLI's default model (API backend falls back to claude-opus-5-5).
    ai_model: str = field(default_factory=lambda: os.environ.get("TRENDFORGE_AI_MODEL", ""))
    ai_effort: str = field(default_factory=lambda: os.environ.get("TRENDFORGE_AI_EFFORT", "low"))
    # Run the AI step at most every N days (data collection stays daily). 1 = every run.
    ai_interval_days: int = field(default_factory=lambda: int(os.environ.get("TRENDFORGE_AI_INTERVAL_DAYS", "7")))
    ai_max_new_repos: int = field(default_factory=lambda: int(os.environ.get("TRENDFORGE_AI_MAX_REPOS", "50")))
    ai_max_categories: int = field(default_factory=lambda: int(os.environ.get("TRENDFORGE_AI_MAX_CATEGORIES", "8")))
    has_anthropic_key: bool = field(
        default_factory=lambda: bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))
    )

    # Paths
    site_dir: Path = ROOT / "site"
    data_dir: Path = ROOT / "site" / "data"
    snapshot_dir: Path = ROOT / "data" / "snapshots"
    cache_dir: Path = ROOT / "data" / "cache"
    reports_dir: Path = ROOT / "reports"
    snapshot_retention_days: int = 90


CONFIG = Config()
