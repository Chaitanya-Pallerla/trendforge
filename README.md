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
## TrendForge daily report — 2026-11-20

_757 repositories and 116 discussions analyzed from api, hackernews, search, trending-daily, trending-weekly._

### 🔥 Trending technologies

| # | Topic | Momentum | Change (7d) | Leading repos |
|---|---|---|---|---|
| 1 | **AI Agents** | 34.9k | -19% | [dsh-our-free-model](https://github.com/Ebony-Vinyl/dsh-our-free-model), [univer](https://github.com/dream-num/univer), [SoduWork](https://github.com/mdiri-ai/SoduWork) |
| 2 | **AI Coding Tools** | 30.7k | +18% | [dsh-Go](https://github.com/ccch1mneyyy/dsh-Go), [rust-anything](https://github.com/erkamyaman/rust-anything), [SoduWork](https://github.com/mdiri-ai/SoduWork) |
| 3 | **LLM Apps & RAG** | 28.2k | +5% | [dsh-our-free-model](https://github.com/Ebony-Vinyl/dsh-our-free-model), [dsh-Go](https://github.com/ccch1mneyyy/dsh-Go), [last30days-skill](https://github.com/mvanhorn/last30days-skill) |
| 4 | **Web & App Frameworks** | 17.0k | +30% | [dsh-Go](https://github.com/ccch1mneyyy/dsh-Go), [rust-anything](https://github.com/erkamyaman/rust-anything), [superpowers](https://github.com/obra/superpowers) |
| 5 | **Developer Tools** | 16.7k | -40% | [dsh-our-free-model](https://github.com/Ebony-Vinyl/dsh-our-free-model), [rust-anything](https://github.com/erkamyaman/rust-anything), [photocraft](https://github.com/storytold/photocraft) |
| 6 | **MCP Tooling** | 14.9k | +29% | [rust-anything](https://github.com/erkamyaman/rust-anything), [SoduWork](https://github.com/mdiri-ai/SoduWork), [ffmpeg-skill](https://github.com/kajisho5/ffmpeg-skill) |
| 7 | **Infra, Self-hosting & Security** | 11.9k | -40% | [SoduWork](https://github.com/mdiri-ai/SoduWork), [cleanyourtv](https://github.com/Gathin23/cleanyourtv), [Claude-BugHunter](https://github.com/elementalsouls/Claude-BugHunter) |
| 8 | **Local Inference** | 5.8k | -2% | [linger](https://github.com/simplexai-labs/linger), [yogurt](https://github.com/FrigadeHQ/yogurt), [blender-ai-mcp-addon](https://github.com/bookwjitchieni1986/blender-ai-mcp-addon) |

### 🚀 Top repositories today

| Repository | Stars | Growth | What it is |
|---|---|---|---|
| [storytold/craft-anything](https://github.com/storytold/craft-anything) | 38.5k | +1.5k today | Rust project for understanding how software works and building your own. |
| [Ebony-Vinyl/dsh-our-free-model](https://github.com/Ebony-Vinyl/dsh-our-free-model) | 81.0k | +1.2k today | dsh plugin that claims free, unlimited access to frontier models with no API key. |
| [ccch1mneyyy/dsh-Go](https://github.com/ccch1mneyyy/dsh-Go) | 28.2k | +1.0k today | An Android client for DeepSeek Harness that runs on the phone itself or remotely controls DSH on a computer. |
| [erkamyaman/rust-anything](https://github.com/erkamyaman/rust-anything) | 5.2k | +1.8k today | Rewrite your whole app in Rust, one piece at a time, checked against the original's recorded behavior at every step. CLIs, HTTP servers a… |
| [dream-num/univer](https://github.com/dream-num/univer) | 30.4k | +557 today | Build your own AI office with Univer Office SDK. Bring editing, calculation, collaboration, and file processing into your product for peo… |
| [mdiri-ai/SoduWork](https://github.com/mdiri-ai/SoduWork) | 4.2k | +1.3k today | The AI-native engine for teams and their agents. Multi-harness, multi-agent, self-hosted. |
| [anefzaoui/misterdownloadmanager](https://github.com/anefzaoui/misterdownloadmanager) | 13.7k | +736 today | misterdownloadmanager: The ultimate open-source, clean-room download manager written from scratch in pure Rust for Windows, Mac, and Linux |
| [obra/superpowers](https://github.com/obra/superpowers) | 322.1k | +2.0k today | An agentic skills framework & software development methodology that works. |
| [GoogleChrome/modern-web-guidance-src](https://github.com/GoogleChrome/modern-web-guidance-src) | 9.1k | +285 today | Keep your coding agent up to date with the latest web best practices |
| [mvanhorn/last30days-skill](https://github.com/mvanhorn/last30days-skill) | 70.8k | +954 today | AI agent skill that researches any topic across Reddit, X, YouTube, HN, Polymarket, and the web - then synthesizes a grounded summary |

### 🎓 For students

**Learn from these**

| Repository | Stars | Growth | What it is |
|---|---|---|---|
| [career-ops-hq/career-ops](https://github.com/career-ops-hq/career-ops) | 83.8k | +240 today | Open-source AI job search agent and job finder: scan job boards, score each job 1-5 against your CV before you apply, tailor an ATS-frien… |
| [xiaoyang111222/cn-math-taxonomy](https://github.com/xiaoyang111222/cn-math-taxonomy) | 8.7k | +142 today | 数学（小学到高中）、英语（三年级到高中）、初中物理的知识图谱：1644 个知识点、2403 条先修边、6723 道题，对齐课标，附自适应前置诊断。 |
| [datawhalechina/hello-agents](https://github.com/datawhalechina/hello-agents) | 87.4k | +95 today | 📚 《从零开始构建智能体》——从零开始的智能体原理与实践教程 |
| [reacher-z/Awesome-REA](https://github.com/reacher-z/Awesome-REA) | 3.2k | +50 today | Curated tools, case studies and papers for reverse engineering websites, games, apps, binaries, firmware and protocols. Source-reviewed, … |
| [nilbuild/developer-roadmap](https://github.com/nilbuild/developer-roadmap) | 372.4k | +74 today | Interactive roadmaps, guides and other educational content to help developers grow in their careers. |
| [practical-tutorials/project-based-learning](https://github.com/practical-tutorials/project-based-learning) | 290.1k | +67 today | Curated list of project-based tutorials |
| [EbookFoundation/free-programming-books](https://github.com/EbookFoundation/free-programming-books) | 401.9k | +61 today | :books: Freely available programming books |
| [luongnv89/claude-howto](https://github.com/luongnv89/claude-howto) | 47.4k | +29 today | A visual, example-driven guide to Claude Code — from basic concepts to advanced agents, with copy-paste templates that bring immediate va… |

**Make your first open-source contribution** (active projects with many `good first issue`s)

- [Gathin23/cleanyourtv](https://github.com/Gathin23/cleanyourtv/contribute) — 59.6k★ · Python
- [nexu-io/open-design](https://github.com/nexu-io/open-design/contribute) — 108.5k★ · TypeScript
- [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp/contribute) — 135.8k★ · C++
- [rtk-ai/rtk](https://github.com/rtk-ai/rtk/contribute) — 87.2k★ · Rust
- [OpenHands/OpenHands](https://github.com/OpenHands/OpenHands/contribute) — 93.9k★ · TypeScript
- [vllm-project/vllm](https://github.com/vllm-project/vllm/contribute) — 97.2k★ · Python

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

#### Web & App Frameworks

Web frameworks are being redesigned with agents as users. meta/astryx (+3278) is a design system built for agents, and Scrapling (+8226) is a scraping framework. Open alternatives to Grok Bot are also rising, such as OpenMausBot (+1587) and rakazo (+143).

**Gaps:** No way to check whether agent-generated UI actually follows a design system; Few templates for web front ends that let people supervise sandboxed bots; Few mobile-first interfaces for controlling agents

- **Design System Linter for Agents** _(intermediate 🎓)_ — A CI check that flags components and tokens in agent-written UI that don't come from astryx or another chosen design system. Frontend teams using coding agents would use it.
- **Sandbox Bot Console Kit** _(intermediate 🎓)_ — A React starter app that streams the screen, logs and approval prompts from a bot's VM or sandbox. Builders of OpenMausBot or rakazo deployments would use it.
- **Source-to-Digest Starter** _(beginner 🎓)_ — A small template that uses Scrapling to pull from configured sources and publishes a static daily digest site. Niche communities and students would use it.

<!-- TRENDFORGE:END -->

## License

MIT
