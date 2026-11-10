"""Daily Markdown reports (reports/YYYY-MM-DD.md, reports/LATEST.md, README section)."""

from __future__ import annotations

import re

from .categories import BY_ID, STUDENTS_ID
from .config import CONFIG, ROOT

README_START = "<!-- TRENDFORGE:START -->"
README_END = "<!-- TRENDFORGE:END -->"


def _fmt(n: int | float | None) -> str:
    if n is None:
        return "–"
    n = int(n)
    return f"{n / 1000:.1f}k" if abs(n) >= 1000 else str(n)


def _gain(r: dict) -> str:
    if r.get("gain_1d"):
        return f"+{_fmt(r['gain_1d'])} today"
    if r.get("gain_7d"):
        return f"+{_fmt(r['gain_7d'])} this week"
    return "new" if (r.get("age_days") or 999) < 30 else ""


def _line(r: dict) -> str:
    desc = (r.get("ai") or {}).get("summary") or r.get("description") or ""
    desc = desc.replace("|", "\\|").replace("\n", " ")
    if len(desc) > 140:
        desc = desc[:137] + "…"
    return f"| [{r['full_name']}]({r['url']}) | {_fmt(r['stars'])} | {_gain(r)} | {desc} |"


def render(payload: dict, *, compact: bool = False) -> str:
    day = payload["generated_at"][:10]
    repos = {r["full_name"]: r for r in payload["repos"]}
    out = [f"## TrendForge daily report — {day}", ""]
    out.append(f"_{payload['stats']['repos_tracked']} repositories and {payload['stats']['discussions']} "
               f"discussions analyzed from {', '.join(payload['stats']['sources'])}._")
    out.append("")

    out += ["### 🔥 Trending technologies", "", "| # | Topic | Momentum | Change (7d) | Leading repos |",
            "|---|---|---|---|---|"]
    cats = [c for c in payload["categories"] if c["id"] != STUDENTS_ID]
    for i, c in enumerate(cats[:8], 1):
        growth = f"{c['growth_pct']:+.0f}%" if c.get("growth_pct") is not None else "new"
        tops = ", ".join(f"[{n.split('/')[1]}](https://github.com/{n})" for n in c["top_repos"][:3])
        out.append(f"| {i} | **{c['name']}** | {_fmt(c['momentum'])} | {growth} | {tops} |")
    out.append("")

    out += ["### 🚀 Top repositories today", "", "| Repository | Stars | Growth | What it is |", "|---|---|---|---|"]
    out += [_line(r) for r in payload["repos"][: 10 if compact else 25]]
    out.append("")

    out += ["### 🎓 For students", ""]
    learning = [repos[n] for n in payload["students"]["learning"][: 8 if compact else 15] if n in repos]
    if learning:
        out += ["**Learn from these**", "", "| Repository | Stars | Growth | What it is |", "|---|---|---|---|"]
        out += [_line(r) for r in learning]
        out.append("")
    contribute = [repos[n] for n in payload["students"]["contribute"][: 6 if compact else 12] if n in repos]
    if contribute:
        out += ["**Make your first open-source contribution** (active projects with many `good first issue`s)", ""]
        out += [f"- [{r['full_name']}]({r['url']}/contribute) — {_fmt(r['stars'])}★ · {r.get('language') or ''}"
                for r in contribute]
        out.append("")

    analyses = [c for c in payload["categories"] if c.get("analysis")]
    if analyses:
        out += ["### 💡 Build opportunities", ""]
        for c in analyses[: 4 if compact else 10]:
            a = c["analysis"]
            out += [f"#### {c['name']}", "", a["why_trending"], ""]
            if a.get("gaps"):
                out += ["**Gaps:** " + "; ".join(a["gaps"]), ""]
            for idea in a.get("ideas", []):
                tag = " 🎓" if idea.get("good_for_students") else ""
                out.append(f"- **{idea['title']}** _({idea['difficulty']}{tag})_ — {idea['pitch']}")
            out.append("")

    if not compact:
        out += ["### 💬 Most-discussed", ""]
        for d in payload["discussions"][:15]:
            out.append(f"- [{d['title']}]({d['discussion_url']}) — {d['community']}, {d['points']} points")
        out.append("")
    return "\n".join(out)


def write_reports(payload: dict) -> None:
    CONFIG.reports_dir.mkdir(parents=True, exist_ok=True)
    day = payload["generated_at"][:10]
    full = "# " + render(payload).lstrip("# ")
    (CONFIG.reports_dir / f"{day}.md").write_text(full + "\n", encoding="utf-8")
    (CONFIG.reports_dir / "LATEST.md").write_text(full + "\n", encoding="utf-8")

    readme = ROOT / "README.md"
    if readme.exists():
        text = readme.read_text(encoding="utf-8")
        if README_START in text and README_END in text:
            block = f"{README_START}\n{render(payload, compact=True)}\n{README_END}"
            text = re.sub(re.escape(README_START) + r".*?" + re.escape(README_END), lambda _: block, text, flags=re.S)
            readme.write_text(text, encoding="utf-8")


__all__ = ["render", "write_reports", "BY_ID"]
