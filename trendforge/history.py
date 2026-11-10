"""Daily star snapshots + category momentum time series.

Snapshots are tiny ({repo: stars}) and committed to git by the daily workflow,
which gives us historical star growth for free without a database.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from .config import CONFIG


def _read(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return default
    return default


def write_json(path: Path, data, *, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":")) if compact \
        else json.dumps(data, ensure_ascii=False, indent=2)
    path.write_text(text + "\n", encoding="utf-8")


def save_snapshot(day: date, stars: dict[str, int]) -> None:
    write_json(CONFIG.snapshot_dir / f"{day.isoformat()}.json", dict(sorted(stars.items())), compact=True)
    cutoff = day - timedelta(days=CONFIG.snapshot_retention_days)
    for f in CONFIG.snapshot_dir.glob("*.json"):
        try:
            if date.fromisoformat(f.stem) < cutoff:
                f.unlink()
        except ValueError:
            continue


def snapshot_near(day: date, days_back: int, tolerance: int = 2) -> tuple[dict[str, int], int | None]:
    """Snapshot from `days_back` days ago (± tolerance, preferring older). Returns (data, actual_days)."""
    for delta in [0] + [d for t in range(1, tolerance + 1) for d in (t, -t)]:
        n = days_back + delta
        if n < 1:
            continue
        path = CONFIG.snapshot_dir / f"{(day - timedelta(days=n)).isoformat()}.json"
        if path.exists():
            return _read(path, {}), n
    return {}, None


# ---------------------------------------------------------------------------
# Category momentum series (served to the dashboard for charts)
# ---------------------------------------------------------------------------

TRENDS_PATH = lambda: CONFIG.data_dir / "trends.json"  # noqa: E731


def load_trends() -> dict:
    return _read(TRENDS_PATH(), {"dates": [], "categories": {}})


def momentum_days_ago(trends: dict, cat_id: str, today: date, days: int) -> float | None:
    target = (today - timedelta(days=days)).isoformat()
    series = trends.get("categories", {}).get(cat_id, [])
    best = None
    for d, v in zip(trends.get("dates", []), series):
        if v is not None and d <= target:
            best = v
    return best


def update_trends(trends: dict, today: date, momentum: dict[str, float], keep: int = 90) -> dict:
    day = today.isoformat()
    dates: list[str] = trends.get("dates", [])
    cats: dict[str, list] = trends.get("categories", {})
    if dates and dates[-1] == day:      # re-run on the same day: overwrite
        dates.pop()
        for series in cats.values():
            if len(series) > len(dates):
                series.pop()
    dates.append(day)
    for cid in set(cats) | set(momentum):
        series = cats.setdefault(cid, [])
        series.extend([None] * (len(dates) - 1 - len(series)))
        series.append(round(momentum.get(cid, 0.0), 1))
    if len(dates) > keep:
        drop = len(dates) - keep
        dates = dates[drop:]
        cats = {k: v[drop:] for k, v in cats.items()}
    return {"dates": dates, "categories": cats}
