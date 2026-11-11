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
| AI layer | Claude through **your Claude account** via the Claude Code CLI (`claude -p`, no API key), or an API key as fallback. Built to be token-efficient: tools/MCP/default system prompt disabled, repos batched ~25 per call, repo insights cached 60 days, all topics in one call. **Data updates daily; the AI step runs weekly** (`TRENDFORGE_AI_INTERVAL_DAYS`, `--ai-now` to force): ~3–4 calls, ~40–50k tokens per week. Cache lives in `data/cache/` and is reused on the days in between |

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
## TrendForge daily report — 2026-11-11

_785 repositories and 249 discussions analyzed from api, hackernews, reddit, search, trending-daily, trending-weekly._

### 🔥 Trending technologies

| # | Topic | Momentum | Change (7d) | Leading repos |
|---|---|---|---|---|
| 1 | **AI Agents** | 36.8k | new | [security-audit-skill](https://github.com/cloudflare/security-audit-skill), [skills](https://github.com/mattpocock/skills), [agent-desktop](https://github.com/vercel-labs/agent-desktop) |
| 2 | **LLM Apps & RAG** | 20.1k | new | [auto-ontology](https://github.com/NVIDIA/auto-ontology), [dsh-our-free-model](https://github.com/Ebony-Vinyl/dsh-our-free-model), [dsh-Go](https://github.com/ccch1mneyyy/dsh-Go) |
| 3 | **Developer Tools** | 19.2k | new | [agent-desktop](https://github.com/vercel-labs/agent-desktop), [GestaltX](https://github.com/huamidev/GestaltX), [dsh-our-free-model](https://github.com/Ebony-Vinyl/dsh-our-free-model) |
| 4 | **AI Coding Tools** | 17.3k | new | [OpenMausBot](https://github.com/milind-soni/OpenMausBot), [dsh-Go](https://github.com/ccch1mneyyy/dsh-Go), [cleanyourtv](https://github.com/Gathin23/cleanyourtv) |
| 5 | **Web & App Frameworks** | 17.1k | new | [OpenMausBot](https://github.com/milind-soni/OpenMausBot), [astryx](https://github.com/meta/astryx), [auto-ontology](https://github.com/NVIDIA/auto-ontology) |
| 6 | **Infra, Self-hosting & Security** | 14.5k | new | [security-audit-skill](https://github.com/cloudflare/security-audit-skill), [OpenMausBot](https://github.com/milind-soni/OpenMausBot), [sherlock](https://github.com/sherlock-project/sherlock) |
| 7 | **MCP Tooling** | 11.2k | new | [agent-desktop](https://github.com/vercel-labs/agent-desktop), [Scrapling](https://github.com/D4Vinci/Scrapling), [ha-mcp](https://github.com/homeassistant-ai/ha-mcp) |
| 8 | **Browser Agents** | 5.6k | new | [Scrapling](https://github.com/D4Vinci/Scrapling), [agent-browser](https://github.com/vercel-labs/agent-browser), [OpenBot](https://github.com/CopilotKit/OpenBot) |

### 🚀 Top repositories today

| Repository | Stars | Growth | What it is |
|---|---|---|---|
| [cloudflare/security-audit-skill](https://github.com/cloudflare/security-audit-skill) | 69.9k | +1.2k today | Skill that lets a coding agent run multi-phase security audits and output machine-readable findings. |
| [mattpocock/skills](https://github.com/mattpocock/skills) | 321.6k | +1.2k today | Matt Pocock's personal set of agent skills for engineering work. |
| [storytold/craft-anything](https://github.com/storytold/craft-anything) | 27.8k | +2.3k today | Rust project for understanding how software works and building your own. |
| [vercel-labs/agent-desktop](https://github.com/vercel-labs/agent-desktop) | 21.8k | +716 today | Rust CLI that lets AI agents use desktop apps through the OS accessibility tree. |
| [milind-soni/OpenMausBot](https://github.com/milind-soni/OpenMausBot) | 21.1k | +637 today | Open-source alternative to Grok Bot that gives bots a virtual machine to use. |
| [meta/astryx](https://github.com/meta/astryx) | 24.3k | +2.8k today | Open-source design system that can be fully customized and is built to work with agents. |
| [huamidev/GestaltX](https://github.com/huamidev/GestaltX) | 5.9k | +1.8k today | MobileGestalt editor for iOS 27.x with region-code tweaks, device presets and backups. |
| [NVIDIA/auto-ontology](https://github.com/NVIDIA/auto-ontology) | 11.7k | +379 today | Python framework for building graph-based semantic reasoning layers over data. |
| [D4Vinci/Scrapling](https://github.com/D4Vinci/Scrapling) | 101.5k | +558 today | Python web scraping framework that handles everything from single requests to full crawls. |
| [anthropics/skills](https://github.com/anthropics/skills) | 192.9k | +1.1k today | Anthropic's public repository of Agent Skills for Claude. |

### 🎓 For students

**Learn from these**

| Repository | Stars | Growth | What it is |
|---|---|---|---|
| [freeCodeCamp/freeCodeCamp](https://github.com/freeCodeCamp/freeCodeCamp) | 459.0k | +111 today | freeCodeCamp.org's open-source codebase and curriculum. Learn math, programming, and computer science for free. |
| [EbookFoundation/free-programming-books](https://github.com/EbookFoundation/free-programming-books) | 401.5k | +60 today | :books: Freely available programming books |
| [nilbuild/developer-roadmap](https://github.com/nilbuild/developer-roadmap) | 371.8k | +80 today | Interactive roadmaps, guides and other educational content to help developers grow in their careers. |
| [jwasham/coding-interview-university](https://github.com/jwasham/coding-interview-university) | 364.2k | +71 today | A complete computer science study plan to become a software engineer. |
| [practical-tutorials/project-based-learning](https://github.com/practical-tutorials/project-based-learning) | 289.5k | +64 today | Curated list of project-based tutorials |
| [TheAlgorithms/Python](https://github.com/TheAlgorithms/Python) | 226.0k | +30 today | All Algorithms implemented in Python |
| [getify/You-Dont-Know-JS](https://github.com/getify/You-Dont-Know-JS) | 184.8k | +1 today | A book series (2 published editions) on the JS language. |
| [krahets/hello-algo](https://github.com/krahets/hello-algo) | 132.2k | +72 today | 《Hello 算法》：动画图解、一键运行的数据结构与算法教程。支持简中、繁中、English、日本語，提供 Python, Java, C++, C, C#, JS, Go, Swift, Rust, Ruby, Kotlin, TS, Dart 等代码实现 |

**Make your first open-source contribution** (active projects with many `good first issue`s)

- [microsoft/vscode](https://github.com/microsoft/vscode/contribute) — 195.3k★ · TypeScript
- [langgenius/dify](https://github.com/langgenius/dify/contribute) — 161.0k★ · Python
- [vercel/next.js](https://github.com/vercel/next.js/contribute) — 143.5k★ · JavaScript
- [ytdl-org/youtube-dl](https://github.com/ytdl-org/youtube-dl/contribute) — 141.5k★ · Python
- [excalidraw/excalidraw](https://github.com/excalidraw/excalidraw/contribute) — 135.5k★ · TypeScript
- [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp/contribute) — 134.1k★ · C++

### 💡 Build opportunities

#### AI Agents

Growth is going to tools that give agents new abilities. vercel-labs/agent-desktop (+12120), cloudflare/security-audit-skill (+10695) and NVIDIA/auto-ontology (+10159) gained the most stars. Skill collections are also growing fast: mattpocock/skills has 319861★ (+9800), and claude-mem added +5130.

**Gaps:** No way to test or score whether a skill actually improves agent output; Skills from different repos can conflict or duplicate each other, and nothing manages that; Hard to see what agents with desktop or VM access actually did; Multi-agent setups are hard to debug once they reach dozens of agents

- **Skill Bench** _(intermediate 🎓)_ — A harness that runs the same tasks with and without a skill and reports the difference in results. Skill authors and teams choosing skills would use it.
- **Skill Lockfile** _(beginner 🎓)_ — A CLI that installs skills from several repos, pins their versions and flags overlapping or conflicting instructions. Developers mixing skill packs would use it.
- **Agent Action Replay** _(advanced)_ — A recorder that captures accessibility-tree actions from desktop and browser agents and lets users replay them step by step. Teams auditing computer-use agents would use it.

#### LLM Apps & RAG

Users want output that doesn't look AI-generated and agents that remember context. hallmark (+5987) and unslop target generic AI design, and claude-mem (+5130) handles memory. Interest in structured reasoning over data also appears in auto-ontology (+10159).

**Gaps:** No objective way to measure whether a design looks AI-generated; Memory plugins don't let users inspect or edit what was stored; Few ways to connect ontology layers to existing RAG stacks

- **Slop Score** _(intermediate 🎓)_ — A tool that screenshots a UI and scores it on common AI-generated design patterns, so users can compare results before and after applying hallmark or unslop. Designers and agent users would use it.
- **Memory Inspector** _(beginner 🎓)_ — A local UI for browsing, editing and deleting the compressed sessions stored by claude-mem-style plugins. Heavy agent users would use it.
- **Ontology-to-RAG Adapter** _(advanced)_ — A library that adds results from an auto-ontology graph to vector search retrieval. RAG builders would use it.

#### Developer Tools

Rust CLIs built for agents lead this category: agent-desktop gained +12120 and worktrunk gained +2395. Worktree management and PR review (pr-agent, +1822) point to developers running several agents in parallel. sherlock (+4267) is still drawing strong interest.

**Gaps:** No dashboard showing which agent is working in which worktree; AI-written PRs are hard to tie back to the agent session that produced them; No simple check of whether a tool's claims are legitimate (for example, dsh-our-free-model's claim of free, unlimited model access with no API key)

- **Worktree Board** _(beginner 🎓)_ — A terminal UI that shows each Git worktree with its branch, the agent running in it, its diff size and test status. Developers running parallel agents would use it.
- **PR Provenance** _(intermediate 🎓)_ — A git hook plus a GitHub Action that attaches a summary of the agent session and its prompts to each PR. Reviewers using pr-agent-style tools would use it.
- **Repo Trust Check** _(intermediate 🎓)_ — A CLI that reviews a plugin repo before installation, checking its network calls, credential use and install scripts. Developers trying trending plugins would use it.

#### AI Coding Tools

Coding agents are being extended with design skills (hallmark +5987), memory (claude-mem +5130) and workflow tools like worktrunk (+2395) and pr-agent (+1822). magpie (33214★) shows developers want to switch the model behind each agent.

**Gaps:** No cost or quality comparison when switching models behind an agent; Background agents need better escalation and approval inboxes; Skills and memory don't carry over between Claude Code, Cursor and Codex

- **Model Swap Benchmarks** _(intermediate 🎓)_ — A runner that sends the same coding task to the same agent with different backend models and compares the diffs, test results and cost. Developers using magpie-style routing would use it.
- **Agent Approval Inbox** _(beginner 🎓)_ — A mobile or web inbox that collects decision cards from background coding agents in one place. Solo developers running agent-autoloop would use it.
- **Cross-Agent Skill Sync** _(beginner 🎓)_ — A converter that keeps skills and rules files in sync across Claude Code, Cursor and Codex. Teams using more than one agent would use it.

<!-- TRENDFORGE:END -->

## License

MIT
