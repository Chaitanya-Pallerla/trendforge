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
## TrendForge daily report — 2026-11-18

_762 repositories and 120 discussions analyzed from api, hackernews, search, trending-daily, trending-weekly._

### 🔥 Trending technologies

| # | Topic | Momentum | Change (7d) | Leading repos |
|---|---|---|---|---|
| 1 | **AI Agents** | 40.6k | +10% | [dsh-our-free-model](https://github.com/Ebony-Vinyl/dsh-our-free-model), [univer](https://github.com/dream-num/univer), [astryx](https://github.com/meta/astryx) |
| 2 | **AI Coding Tools** | 34.2k | +97% | [dsh-Go](https://github.com/ccch1mneyyy/dsh-Go), [modern-web-guidance-src](https://github.com/GoogleChrome/modern-web-guidance-src), [ffmpeg-skill](https://github.com/kajisho5/ffmpeg-skill) |
| 3 | **LLM Apps & RAG** | 33.6k | +67% | [dsh-our-free-model](https://github.com/Ebony-Vinyl/dsh-our-free-model), [dsh-Go](https://github.com/ccch1mneyyy/dsh-Go), [ffmpeg-skill](https://github.com/kajisho5/ffmpeg-skill) |
| 4 | **Developer Tools** | 21.2k | +10% | [dsh-our-free-model](https://github.com/Ebony-Vinyl/dsh-our-free-model), [photocraft](https://github.com/storytold/photocraft), [elephant-goldfish-model](https://github.com/google/elephant-goldfish-model) |
| 5 | **Web & App Frameworks** | 18.6k | +8% | [dsh-Go](https://github.com/ccch1mneyyy/dsh-Go), [astryx](https://github.com/meta/astryx), [superpowers](https://github.com/obra/superpowers) |
| 6 | **Infra, Self-hosting & Security** | 14.4k | -0% | [cleanyourtv](https://github.com/Gathin23/cleanyourtv), [OpenMausBot](https://github.com/milind-soni/OpenMausBot), [Claude-BugHunter](https://github.com/elementalsouls/Claude-BugHunter) |
| 7 | **MCP Tooling** | 12.4k | +11% | [ffmpeg-skill](https://github.com/kajisho5/ffmpeg-skill), [chrome-devtools-mcp](https://github.com/ChromeDevTools/chrome-devtools-mcp), [SoduWork](https://github.com/mdiri-ai/SoduWork) |
| 8 | **Browser Agents** | 4.7k | -16% | [chrome-devtools-mcp](https://github.com/ChromeDevTools/chrome-devtools-mcp), [agent-browser](https://github.com/vercel-labs/agent-browser), [nod](https://github.com/n8n-io/nod) |

### 🚀 Top repositories today

| Repository | Stars | Growth | What it is |
|---|---|---|---|
| [Ebony-Vinyl/dsh-our-free-model](https://github.com/Ebony-Vinyl/dsh-our-free-model) | 78.5k | +1.2k today | dsh plugin that claims free, unlimited access to frontier models with no API key. |
| [storytold/craft-anything](https://github.com/storytold/craft-anything) | 35.7k | +895 today | Rust project for understanding how software works and building your own. |
| [ccch1mneyyy/dsh-Go](https://github.com/ccch1mneyyy/dsh-Go) | 26.0k | +1.2k today | An Android client for DeepSeek Harness that runs on the phone itself or remotely controls DSH on a computer. |
| [dream-num/univer](https://github.com/dream-num/univer) | 28.9k | +1.8k today | Build your own AI office with Univer Office SDK. Bring editing, calculation, collaboration, and file processing into your product for peo… |
| [meta/astryx](https://github.com/meta/astryx) | 30.1k | +520 today | Open-source design system that can be fully customized and is built to work with agents. |
| [anefzaoui/misterdownloadmanager](https://github.com/anefzaoui/misterdownloadmanager) | 12.1k | +894 today | misterdownloadmanager: The ultimate open-source, clean-room download manager written from scratch in pure Rust for Windows, Mac, and Linux |
| [GoogleChrome/modern-web-guidance-src](https://github.com/GoogleChrome/modern-web-guidance-src) | 8.4k | +437 today | Keep your coding agent up to date with the latest web best practices |
| [kajisho5/ffmpeg-skill](https://github.com/kajisho5/ffmpeg-skill) | 7.7k | +1.3k today | Local video editor for coding agents: 42 FFmpeg tools with a machine-readable contract and an MCP server, for Claude Code, Cursor and Cod… |
| [Gathin23/cleanyourtv](https://github.com/Gathin23/cleanyourtv) | 59.0k | +336 today | Tool that removes bloatware from Android or Google TV over Wi-Fi and adds an Apple TV-style home screen. |
| [obra/superpowers](https://github.com/obra/superpowers) | 319.3k | +1.9k today | An agentic skills framework & software development methodology that works. |

### 🎓 For students

**Learn from these**

| Repository | Stars | Growth | What it is |
|---|---|---|---|
| [career-ops-hq/career-ops](https://github.com/career-ops-hq/career-ops) | 83.4k | +247 today | Open-source AI job search agent and job finder: scan job boards, score each job 1-5 against your CV before you apply, tailor an ATS-frien… |
| [xiaoyang111222/cn-math-taxonomy](https://github.com/xiaoyang111222/cn-math-taxonomy) | 8.4k | +124 today | 数学（小学到高中）、英语（三年级到高中）、初中物理的知识图谱：1644 个知识点、2403 条先修边、6723 道题，对齐课标，附自适应前置诊断。 |
| [reacher-z/Awesome-REA](https://github.com/reacher-z/Awesome-REA) | 3.1k | +59 today | Curated tools, case studies and papers for reverse engineering websites, games, apps, binaries, firmware and protocols. Source-reviewed, … |
| [datawhalechina/hello-agents](https://github.com/datawhalechina/hello-agents) | 87.2k | +75 today | 📚 《从零开始构建智能体》——从零开始的智能体原理与实践教程 |
| [nilbuild/developer-roadmap](https://github.com/nilbuild/developer-roadmap) | 372.2k | +68 today | Interactive roadmaps, guides and other educational content to help developers grow in their careers. |
| [luongnv89/claude-howto](https://github.com/luongnv89/claude-howto) | 47.4k | +57 today | A visual, example-driven guide to Claude Code — from basic concepts to advanced agents, with copy-paste templates that bring immediate va… |
| [practical-tutorials/project-based-learning](https://github.com/practical-tutorials/project-based-learning) | 289.9k | +72 today | Curated list of project-based tutorials |
| [Xin-YuXiao/Awesome-AI-for-Astronomy](https://github.com/Xin-YuXiao/Awesome-AI-for-Astronomy) | 332 | +49 today | A curated list of papers for AI in Astronomy & Astrophysics. |

**Make your first open-source contribution** (active projects with many `good first issue`s)

- [Gathin23/cleanyourtv](https://github.com/Gathin23/cleanyourtv/contribute) — 59.0k★ · Python
- [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp/contribute) — 135.7k★ · C++
- [nexu-io/open-design](https://github.com/nexu-io/open-design/contribute) — 108.1k★ · TypeScript
- [rtk-ai/rtk](https://github.com/rtk-ai/rtk/contribute) — 86.9k★ · Rust
- [OpenHands/OpenHands](https://github.com/OpenHands/OpenHands/contribute) — 93.7k★ · TypeScript
- [pytorch/pytorch](https://github.com/pytorch/pytorch/contribute) — 105.8k★ · Python

### 💡 Build opportunities

#### AI Agents

Growth is going to tools that give agents new abilities. vercel-labs/agent-desktop (+12120), cloudflare/security-audit-skill (+10695) and NVIDIA/auto-ontology (+10159) gained the most stars. Skill collections are also growing fast: mattpocock/skills has 319861★ (+9800), and claude-mem added +5130.

**Gaps:** No way to test or score whether a skill actually improves agent output; Skills from different repos can conflict or duplicate each other, and nothing manages that; Hard to see what agents with desktop or VM access actually did; Multi-agent setups are hard to debug once they reach dozens of agents

- **Skill Bench** _(intermediate 🎓)_ — A harness that runs the same tasks with and without a skill and reports the difference in results. Skill authors and teams choosing skills would use it.
- **Skill Lockfile** _(beginner 🎓)_ — A CLI that installs skills from several repos, pins their versions and flags overlapping or conflicting instructions. Developers mixing skill packs would use it.
- **Agent Action Replay** _(advanced)_ — A recorder that captures accessibility-tree actions from desktop and browser agents and lets users replay them step by step. Teams auditing computer-use agents would use it.

#### AI Coding Tools

Coding agents are being extended with design skills (hallmark +5987), memory (claude-mem +5130) and workflow tools like worktrunk (+2395) and pr-agent (+1822). magpie (33214★) shows developers want to switch the model behind each agent.

**Gaps:** No cost or quality comparison when switching models behind an agent; Background agents need better escalation and approval inboxes; Skills and memory don't carry over between Claude Code, Cursor and Codex

- **Model Swap Benchmarks** _(intermediate 🎓)_ — A runner that sends the same coding task to the same agent with different backend models and compares the diffs, test results and cost. Developers using magpie-style routing would use it.
- **Agent Approval Inbox** _(beginner 🎓)_ — A mobile or web inbox that collects decision cards from background coding agents in one place. Solo developers running agent-autoloop would use it.
- **Cross-Agent Skill Sync** _(beginner 🎓)_ — A converter that keeps skills and rules files in sync across Claude Code, Cursor and Codex. Teams using more than one agent would use it.

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

<!-- TRENDFORGE:END -->

## License

MIT
