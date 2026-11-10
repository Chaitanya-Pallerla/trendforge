"""Category definitions and rule-based classification.

Rules are deliberately simple and transparent so contributors can improve them
with a one-line PR. The AI layer (optional) refines summaries on top of this.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Category:
    id: str
    name: str
    description: str
    topics: tuple[str, ...]            # exact GitHub topic matches (strong signal)
    keywords: tuple[str, ...]          # regex fragments matched on name + description
    queries: tuple[str, ...] = ()      # extra GitHub search queries ({d30}/{d90} expanded)
    _patterns: list[re.Pattern] = field(default_factory=list, compare=False, repr=False)

    def __post_init__(self) -> None:
        for kw in self.keywords:
            self._patterns.append(re.compile(rf"(?<![a-z0-9]){kw}(?![a-z0-9])", re.I))


STUDENTS_ID = "students"

CATEGORIES: list[Category] = [
    Category(
        "browser-agents", "Browser Agents", "Tools that automate browser workflows and scrape the web",
        topics=("browser-automation", "web-scraping", "crawler", "playwright", "puppeteer", "browser-agent",
                "web-crawler", "scraping", "headless-browser"),
        keywords=(r"browser[- ]?(use|agent|automation)", r"web agents?", "playwright", "puppeteer", "headless",
                  r"scrap(er|ing|e)", r"crawl(er|ing)?", "selenium"),
        queries=("topic:browser-automation created:>{d90}", "topic:web-scraping created:>{d90}"),
    ),
    Category(
        "mcp", "MCP Tooling", "Model Context Protocol servers, clients and agent tool integrations",
        topics=("mcp", "mcp-server", "model-context-protocol", "mcp-client", "mcp-tools"),
        keywords=("mcp", "model context protocol"),
        queries=("topic:mcp created:>{d90}", "topic:mcp-server created:>{d90}"),
    ),
    Category(
        "ai-agents", "AI Agents", "Agent frameworks, multi-agent systems and autonomous workflows",
        topics=("ai-agents", "agents", "llm-agent", "agentic-ai", "multi-agent", "autonomous-agents", "agent"),
        keywords=(r"agents?", "agentic", "multi-agent", "autonomous", "swarm"),
        queries=("topic:ai-agents created:>{d90}", "topic:agentic-ai created:>{d90}"),
    ),
    Category(
        "ai-coding", "AI Coding Tools", "Coding agents, code assistants, AI code review and generation",
        topics=("coding-assistant", "ai-coding", "code-generation", "claude-code", "copilot", "vibe-coding",
                "coding-agent", "ai-code-review"),
        keywords=("coding agent", "code assistant", "copilot", "claude code", "codegen", "code review",
                  "vibe coding", "cursor", "ai pair programm\\w*"),
        queries=("topic:claude-code created:>{d90}", "topic:coding-agent created:>{d90}"),
    ),
    Category(
        "llm-apps", "LLM Apps & RAG", "Chat apps, RAG pipelines, prompt tooling and vector search",
        topics=("llm", "rag", "chatgpt", "large-language-models", "generative-ai", "vector-database",
                "openai", "claude", "anthropic", "gemini", "langchain", "prompt-engineering", "embeddings"),
        keywords=("llms?", "rag", "retrieval", "chatbot", "prompts?", "embeddings?", "vector (db|database|search)",
                  "gpt", "claude", "gemini", "chat ui"),
        queries=("topic:rag created:>{d90}", "topic:llm created:>{d30}"),
    ),
    Category(
        "local-inference", "Local Inference", "On-device and self-hosted model inference",
        topics=("local-llm", "ollama", "llama-cpp", "inference", "mlx", "vllm", "gguf", "quantization", "llamacpp",
                "on-device-ai"),
        keywords=("local llm", "ollama", "llama\\.cpp", "gguf", r"quantiz\w+", "inference", "on-device",
                  "vllm", "mlx", "offline ai"),
        queries=("topic:local-llm created:>{d90}", "topic:ollama created:>{d90}"),
    ),
    Category(
        "observability", "Agent Observability & Evals", "Tracing, evaluation, guardrails and monitoring for AI",
        topics=("llm-observability", "llmops", "evaluation", "observability", "llm-evaluation", "evals",
                "guardrails", "monitoring", "tracing"),
        keywords=("observability", "tracing", r"evals?", "evaluation", "monitoring", "benchmarks?", "guardrails?",
                  "llmops", "telemetry"),
        queries=("topic:llm-evaluation created:>{d90}", "topic:llmops created:>{d90}"),
    ),
    Category(
        "physical-ai", "Physical AI & Robotics", "Robot learning, simulation, embodied AI and drones",
        topics=("robotics", "ros", "ros2", "embodied-ai", "simulation", "humanoid", "drone", "robot-learning",
                "reinforcement-learning", "isaac-sim"),
        keywords=(r"robots?", "robotics", "embodied", "ros2?", "humanoid", r"drones?", "simulat\\w+",
                  "reinforcement learning", "manipulation", "slam"),
        queries=("topic:robotics created:>{d90}", "topic:embodied-ai created:>{d90}"),
    ),
    Category(
        "ml-research", "ML & Research Code", "Models, training, fine-tuning, vision and research implementations",
        topics=("machine-learning", "deep-learning", "pytorch", "computer-vision", "diffusion", "fine-tuning",
                "dataset", "transformers", "neural-network", "nlp", "jax", "stable-diffusion", "speech"),
        keywords=("machine learning", "deep learning", "datasets?", "training", r"fine-?tun\w+", "diffusion",
                  "computer vision", "pytorch", "transformers?", "paper", "neural", "tts", "speech", "video generation"),
        queries=("topic:deep-learning created:>{d30}",),
    ),
    Category(
        "devtools", "Developer Tools", "CLIs, terminals, editors, git tooling and productivity",
        topics=("cli", "developer-tools", "terminal", "devtools", "neovim", "vscode-extension", "git", "tui",
                "productivity", "lsp", "rust-cli"),
        keywords=("cli", "terminal", "developer tools?", "devtools?", "lsp", "editor", "git", "debugger",
                  "build tool", "bundler", "tui", "linter", "formatter"),
        queries=("topic:cli created:>{d30}",),
    ),
    Category(
        "web", "Web & App Frameworks", "Frontend, full-stack and mobile frameworks and UI kits",
        topics=("react", "nextjs", "frontend", "tailwindcss", "web-framework", "vue", "svelte", "typescript",
                "ui-components", "flutter", "react-native", "fullstack"),
        keywords=("framework", "react", "next\\.?js", "frontend", "ui (components?|kit|library)", "css", "web apps?",
                  "full-?stack", "svelte", "vue", "flutter", "design system"),
        queries=("topic:nextjs created:>{d30}",),
    ),
    Category(
        "infra-security", "Infra, Self-hosting & Security", "DevOps, databases, self-hosted apps and security tools",
        topics=("security", "kubernetes", "docker", "self-hosted", "devops", "database", "homelab", "pentesting",
                "cybersecurity", "privacy", "infrastructure"),
        keywords=("kubernetes", "docker", "security", "pentest\\w*", "vulnerabilit\\w+", "database", "self-?hosted",
                  "homelab", "devops", "privacy", "firewall", "postgres\\w*", "sqlite"),
        queries=("topic:self-hosted created:>{d30}",),
    ),
    Category(
        STUDENTS_ID, "For Students", "Learning resources, roadmaps, interview prep and beginner-friendly projects",
        topics=("education", "tutorial", "tutorials", "learning", "roadmap", "interview-preparation", "awesome-list",
                "awesome", "course", "courses", "beginner-friendly", "algorithms", "computer-science",
                "free-programming-books", "first-contributions", "good-first-issue", "interview-questions",
                "cheatsheet", "learn-to-code", "data-structures", "leetcode", "books", "study-notes"),
        keywords=("tutorials?", r"courses?", "learn (to|how|python|rust|go|ai|ml|programming)", "roadmaps?",
                  r"interviews?", "beginners?", "education\\w*", r"awesome( list)?", r"cheat ?sheets?",
                  r"exercises?", "from scratch", "build[- ]your[- ]own", "handbook", "curriculum", "study",
                  "leetcode", "dsa", "data structures", "algorithms", "free books", "students?", "university",
                  "step[- ]by[- ]step", "hands-on", "guide to", "100 days", "zero to hero", "explained"),
        queries=(
            "topic:education stars:>200 pushed:>{d30}",
            "topic:tutorial stars:>200 pushed:>{d30}",
            "topic:roadmap stars:>200 pushed:>{d30}",
            "topic:interview-preparation stars:>200 pushed:>{d30}",
            "\"from scratch\" in:name,description stars:>300 created:>{d90}",
        ),
    ),
]

BY_ID = {c.id: c for c in CATEGORIES}


def _score(cat: Category, text: str, topics: set[str]) -> int:
    score = 3 * len(topics.intersection(cat.topics))
    for pat in cat._patterns:
        if pat.search(text):
            score += 1
    return score


def classify(name: str, description: str | None, topics: list[str] | None) -> dict:
    """Return {'category': id, 'tags': [ids], 'for_students': bool}."""
    text = f"{name.replace('-', ' ').replace('_', ' ')} {description or ''}"
    topic_set = {t.lower() for t in (topics or [])}
    scores = {c.id: _score(c, text, topic_set) for c in CATEGORIES}

    student_score = scores.pop(STUDENTS_ID)
    tags = [cid for cid, s in sorted(scores.items(), key=lambda kv: -kv[1]) if s > 0]
    for_students = student_score >= 2 or bool(topic_set.intersection(BY_ID[STUDENTS_ID].topics))

    if tags:
        primary = tags[0]
    elif for_students:
        primary = STUDENTS_ID
    else:
        primary = "other"
    if for_students:
        tags.append(STUDENTS_ID)
    return {"category": primary, "tags": tags[:4], "for_students": for_students}
