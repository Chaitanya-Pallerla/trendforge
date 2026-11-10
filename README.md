# TrendForge AI

**Discover what's trending. Understand what's missing. Build what's next.**

TrendForge collects trending repositories and discussions from GitHub, Hacker News and Reddit every day,
groups them into technology topics, and (optionally) uses Claude to explain what each project solves,
why a topic is gaining momentum, what is still missing, and which tools are worth building next.

It has a dedicated **🎓 For Students** track: trending learning resources, roadmaps and interview prep,
active projects with lots of `good first issue`s for a first open-source contribution, and
portfolio-worthy project ideas.

- 🌐 **Dashboard** — [chaitanya-pallerla.github.io/trendforge](https://chaitanya-pallerla.github.io/trendforge/):
  filter by topic, audience (developers/students), language, stars, repo age, source, GitHub topic,
  "good first issues", "discussed on HN/Reddit" and more. Every filtered view has a shareable link.
- 📰 **Daily report** — [`reports/LATEST.md`](reports/LATEST.md) (plus a dated archive), and the summary below
- 🔁 **Updated daily** by GitHub Actions — free to run; no server, no database

## How it works

```
GitHub Trending ─┐
GitHub Search   ─┼─► merge & dedupe ─► score (star gains, velocity, buzz) ─► classify into topics
Hacker News     ─┤                                                              │
Reddit          ─┘   (camofox-browser fallback for blocked sites)               ▼
                                         Claude (optional): summaries, gaps, build ideas
                                                              │
                     site/data/latest.json · site/data/trends.json · reports/YYYY-MM-DD.md
```

| What | How |
|---|---|
| Star growth | `stars today/this week` from GitHub Trending, plus daily snapshots in `data/snapshots/` (committed to git, so history accumulates for free) |
| Topic momentum | Sum of trend scores of the top repos in a topic; the change is versus 7 days ago (`site/data/trends.json`) |
| Categories | Transparent keyword + GitHub-topic rules in [`trendforge/categories.py`](trendforge/categories.py) — PRs welcome |
| AI layer | Claude via the Anthropic SDK with structured outputs. Repo insights are cached for 30 days, so each daily run only analyzes new repos (≈30 repos + 8 topics per day) |

## Quick start

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                 # add GITHUB_TOKEN (recommended) and ANTHROPIC_API_KEY (optional)

python -m trendforge run             # collect + analyze + write site/data and reports/
python -m trendforge run --no-ai     # skip Claude
python -m trendforge serve           # open http://127.0.0.1:8000
pytest -q
```

### Using camofox-browser for blocked sites

Some sources (notably Reddit) block plain HTTP clients **and** datacenter IPs such as GitHub Actions
runners. TrendForge therefore runs best from a normal home connection through
[camofox-browser](https://github.com/jo-inc/camofox-browser), a real (Camoufox/Firefox) browser with a
REST API. Requests to blocked sites are made with `fetch()` *inside* a browser tab on that site, so they
carry a real browser fingerprint and cookies.

```bash
# in the camofox-browser repo
npm install && npm start           # http://localhost:9377
# in .env
CAMOFOX_URL=http://localhost:9377
```

### Automatic daily run on your PC (Windows)

[`scripts/daily.ps1`](scripts/daily.ps1) starts camofox, collects everything, stops camofox, then commits
and pushes the new data, which triggers the GitHub Pages redeploy. Schedule it once:

```powershell
.\scripts\install-schedule.ps1            # every day at 08:00 (runs later if the PC was off)
.\scripts\install-schedule.ps1 -At 07:30  # pick a time
Start-ScheduledTask -TaskName 'TrendForge Daily'   # run now
.\scripts\install-schedule.ps1 -Uninstall
```

The Camoufox browser (~1.3 GB), profiles and temp files go to `E:\camofox-data` by default
(`-CamofoxDataDir` or `CAMOFOX_DATA_DIR` to change). Logs are in `logs/`.

The GitHub Actions workflow is the **backup**: at 18:00 UTC it checks whether today's data was already
pushed. If not (PC was off), it collects without Reddit so the site still updates.

## Deploy your own (daily updates)

1. Push this folder to a new GitHub repository.
2. **Settings → Pages → Source: GitHub Actions.**
3. **Settings → Secrets and variables → Actions**: add `ANTHROPIC_API_KEY` (optional, enables AI analysis).
   `GITHUB_TOKEN` is provided automatically.
4. **Actions → Daily trend update → Run workflow** once. After that the backup job runs daily at
   18:00 UTC, and every push of new data (e.g. from `scripts/daily.ps1`) redeploys the dashboard.

## Contributing

Good first contributions: improve category rules, add a data source (`trendforge/sources/`), improve the
dashboard (`site/`), or add tests (`tests/`). See the roadmap below.

**Roadmap**
- [x] Phase 1 — trend aggregator: GitHub Trending + Search, HN, Reddit, history, dashboard, daily report
- [x] Phase 2 — AI layer: summaries, problem solved, audience, topic explanations
- [ ] Phase 3 — opportunity engine: mine issues/feature requests of top repos for recurring complaints
- [ ] More sources: Product Hunt, Hugging Face trending, arXiv, dev.to
- [ ] Weekly digest (RSS / email)

## Latest

<!-- TRENDFORGE:START -->
## TrendForge daily report — 2026-11-10

_775 repositories and 236 discussions analyzed from api, hackernews, reddit, search, trending-daily, trending-weekly._

### 🔥 Trending technologies

| # | Topic | Momentum | Change (7d) | Leading repos |
|---|---|---|---|---|
| 1 | **AI Agents** | 30.4k | new | [OpenMausBot](https://github.com/milind-soni/OpenMausBot), [astryx](https://github.com/meta/astryx), [agent-desktop](https://github.com/vercel-labs/agent-desktop) |
| 2 | **Developer Tools** | 15.9k | new | [sherlock](https://github.com/sherlock-project/sherlock), [agent-desktop](https://github.com/vercel-labs/agent-desktop), [agent-browser](https://github.com/vercel-labs/agent-browser) |
| 3 | **Web & App Frameworks** | 14.3k | new | [OpenMausBot](https://github.com/milind-soni/OpenMausBot), [astryx](https://github.com/meta/astryx), [auto-ontology](https://github.com/NVIDIA/auto-ontology) |
| 4 | **Infra, Self-hosting & Security** | 14.1k | new | [sherlock](https://github.com/sherlock-project/sherlock), [OpenMausBot](https://github.com/milind-soni/OpenMausBot), [security-audit-skill](https://github.com/cloudflare/security-audit-skill) |
| 5 | **LLM Apps & RAG** | 13.6k | new | [auto-ontology](https://github.com/NVIDIA/auto-ontology), [hallmark](https://github.com/Nutlope/hallmark), [claude-mem](https://github.com/thedotmack/claude-mem) |
| 6 | **AI Coding Tools** | 13.3k | new | [OpenMausBot](https://github.com/milind-soni/OpenMausBot), [hallmark](https://github.com/Nutlope/hallmark), [claude-mem](https://github.com/thedotmack/claude-mem) |
| 7 | **MCP Tooling** | 8.1k | new | [agent-desktop](https://github.com/vercel-labs/agent-desktop), [Scrapling](https://github.com/D4Vinci/Scrapling), [Concat](https://github.com/jub0t/Concat) |
| 8 | **Browser Agents** | 4.3k | new | [Scrapling](https://github.com/D4Vinci/Scrapling), [agent-browser](https://github.com/vercel-labs/agent-browser), [vork](https://github.com/voyager-so/vork) |

### 🚀 Top repositories today

| Repository | Stars | Growth | What it is |
|---|---|---|---|
| [sherlock-project/sherlock](https://github.com/sherlock-project/sherlock) | 107.3k | +4.3k today | Python CLI that searches social networks for accounts matching a username. |
| [milind-soni/OpenMausBot](https://github.com/milind-soni/OpenMausBot) | 19.8k | +1.6k today | Open-source alternative to Grok Bot that gives bots a virtual machine to use. |
| [pingdotgg/t3code](https://github.com/pingdotgg/t3code) | 54.3k | +13.4k this week | Control surface for coding agents, with mobile, web and desktop apps. |
| [meta/astryx](https://github.com/meta/astryx) | 20.4k | +3.3k today | Open-source design system that can be fully customized and is built to work with agents. |
| [vercel-labs/agent-desktop](https://github.com/vercel-labs/agent-desktop) | 20.6k | +12.1k this week | Rust CLI that lets AI agents use desktop apps through the OS accessibility tree. |
| [cloudflare/security-audit-skill](https://github.com/cloudflare/security-audit-skill) | 68.2k | +10.7k this week | Skill that lets a coding agent run multi-phase security audits and output machine-readable findings. |
| [NVIDIA/auto-ontology](https://github.com/NVIDIA/auto-ontology) | 11.1k | +10.2k this week | Python framework for building graph-based semantic reasoning layers over data. |
| [mattpocock/skills](https://github.com/mattpocock/skills) | 319.9k | +9.8k this week | Matt Pocock's personal set of agent skills for engineering work. |
| [D4Vinci/Scrapling](https://github.com/D4Vinci/Scrapling) | 100.6k | +8.2k this week | Python web scraping framework that handles everything from single requests to full crawls. |
| [anthropics/skills](https://github.com/anthropics/skills) | 191.1k | +1.0k today | Anthropic's public repository of Agent Skills for Claude. |

### 🎓 For students

**Learn from these**

| Repository | Stars | Growth | What it is |
|---|---|---|---|
| [freeCodeCamp/freeCodeCamp](https://github.com/freeCodeCamp/freeCodeCamp) | 458.8k |  | freeCodeCamp.org's open-source codebase and curriculum. Learn math, programming, and computer science for free. |
| [EbookFoundation/free-programming-books](https://github.com/EbookFoundation/free-programming-books) | 401.4k |  | :books: Freely available programming books |
| [nilbuild/developer-roadmap](https://github.com/nilbuild/developer-roadmap) | 371.7k |  | Interactive roadmaps, guides and other educational content to help developers grow in their careers. |
| [jwasham/coding-interview-university](https://github.com/jwasham/coding-interview-university) | 364.2k |  | A complete computer science study plan to become a software engineer. |
| [practical-tutorials/project-based-learning](https://github.com/practical-tutorials/project-based-learning) | 289.4k |  | Curated list of project-based tutorials |
| [TheAlgorithms/Python](https://github.com/TheAlgorithms/Python) | 226.0k |  | All Algorithms implemented in Python |
| [getify/You-Dont-Know-JS](https://github.com/getify/You-Dont-Know-JS) | 184.8k |  | A book series (2 published editions) on the JS language. |
| [krahets/hello-algo](https://github.com/krahets/hello-algo) | 132.1k |  | 《Hello 算法》：动画图解、一键运行的数据结构与算法教程。支持简中、繁中、English、日本語，提供 Python, Java, C++, C, C#, JS, Go, Swift, Rust, Ruby, Kotlin, TS, Dart 等代码实现 |

**Make your first open-source contribution** (active projects with many `good first issue`s)

- [microsoft/vscode](https://github.com/microsoft/vscode/contribute) — 195.2k★ · TypeScript
- [langgenius/dify](https://github.com/langgenius/dify/contribute) — 160.8k★ · Python
- [vercel/next.js](https://github.com/vercel/next.js/contribute) — 143.4k★ · JavaScript
- [ytdl-org/youtube-dl](https://github.com/ytdl-org/youtube-dl/contribute) — 141.5k★ · Python
- [excalidraw/excalidraw](https://github.com/excalidraw/excalidraw/contribute) — 135.4k★ · TypeScript
- [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp/contribute) — 133.9k★ · C++

<!-- TRENDFORGE:END -->

## License

MIT
