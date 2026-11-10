/* TrendForge dashboard — reads data/latest.json + data/trends.json (generated daily). */
(() => {
  "use strict";

  const REPO = "Chaitanya-Pallerla/trendforge";
  const REPO_URL = `https://github.com/${REPO}`;
  const PAGE = 30;
  const STUDENTS = "students";

  const $ = (sel) => document.querySelector(sel);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const fmt = (n) => (n == null ? "–" : Math.abs(n) >= 1000 ? (n / 1000).toFixed(Math.abs(n) >= 10000 ? 0 : 1) + "k" : String(Math.round(n)));
  const ext = (href, text, cls = "") => `<a class="${cls}" href="${esc(href)}" target="_blank" rel="noopener">${text}</a>`;

  const LANG_COLORS = {
    Python: "#3572A5", TypeScript: "#3178c6", JavaScript: "#f1e05a", Rust: "#dea584", Go: "#00ADD8", Java: "#b07219",
    "C++": "#f34b7d", C: "#555555", "C#": "#178600", Swift: "#F05138", Kotlin: "#A97BFF", Ruby: "#701516",
    PHP: "#4F5D95", Shell: "#89e051", "Jupyter Notebook": "#DA5B0B", HTML: "#e34c26", CSS: "#563d7c", Dart: "#00B4AB",
    Zig: "#ec915c", Lua: "#000080", Vue: "#41b883", Svelte: "#ff3e00", MDX: "#fcb32c", Elixir: "#6e4a7e",
  };

  // ---------- state (mirrored in the URL so any view can be shared) ----------
  const DEFAULTS = { cat: "all", q: "", sort: "score", aud: "", lang: "", stars: "0", age: "", src: "", topic: "",
    gfi: false, buzz: false, hasai: false, rising: false };
  const state = { ...DEFAULTS, shown: PAGE, talkSrc: "", data: null, trends: null };
  const FILTER_KEYS = Object.keys(DEFAULTS);

  function readUrl() {
    const p = new URLSearchParams(location.search);
    for (const k of FILTER_KEYS) {
      if (!p.has(k)) continue;
      state[k] = typeof DEFAULTS[k] === "boolean" ? p.get(k) === "1" : p.get(k);
    }
    const hash = location.hash.slice(1);       // legacy #students / #mcp links
    if (hash && !p.has("cat")) state.cat = hash;
  }

  function writeUrl() {
    const p = new URLSearchParams();
    for (const k of FILTER_KEYS) {
      const v = state[k];
      if (v === DEFAULTS[k]) continue;
      p.set(k, typeof v === "boolean" ? "1" : v);
    }
    const qs = p.toString();
    history.replaceState(null, "", qs ? `?${qs}` : location.pathname);
    const active = FILTER_KEYS.filter((k) => k !== "cat" && k !== "sort" && state[k] !== DEFAULTS[k]).length;
    const pill = $("#active-count");
    pill.hidden = active === 0;
    pill.textContent = `${active} active`;
  }

  function syncControls() {
    for (const k of ["q", "sort", "aud", "lang", "stars", "age", "src", "topic"]) $("#" + k).value = state[k];
    for (const k of ["gfi", "buzz", "hasai", "rising"]) $("#" + k).checked = state[k];
  }

  // ---------- theme ----------
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch { /* storage unavailable */ } },
  };
  const savedTheme = store.get("tf-theme");
  if (savedTheme) document.documentElement.dataset.theme = savedTheme;
  $("#theme").addEventListener("click", () => {
    const cur = document.documentElement.dataset.theme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    const next = cur === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    store.set("tf-theme", next);
  });

  function toast(msg) {
    const t = $("#toast");
    t.textContent = msg;
    t.classList.add("show");
    clearTimeout(toast.timer);
    toast.timer = setTimeout(() => t.classList.remove("show"), 1800);
  }

  // ---------- helpers ----------
  function delta(pct) {
    if (pct == null) return `<span class="delta new" title="Not enough history yet">new</span>`;
    const cls = pct >= 0 ? "up" : "down";
    return `<span class="delta ${cls}">${pct >= 0 ? "▲" : "▼"} ${Math.abs(pct).toFixed(0)}%</span>`;
  }

  function spark(catId) {
    const series = (state.trends?.categories?.[catId] || []).filter((v) => v != null).slice(-30);
    if (series.length < 2) return "";
    const w = 64, h = 18, max = Math.max(...series), min = Math.min(...series), span = max - min || 1;
    const pts = series.map((v, i) => `${((i / (series.length - 1)) * w).toFixed(1)},${(h - 2 - ((v - min) / span) * (h - 4)).toFixed(1)}`);
    return `<svg class="spark" viewBox="0 0 ${w} ${h}" aria-hidden="true"><path d="M${pts.join(" L")}"/></svg>`;
  }

  function ago(days) {
    if (days == null) return "";
    if (days < 1) return "today";
    if (days < 30) return `${days}d ago`;
    if (days < 365) return `${Math.round(days / 30)}mo ago`;
    return `${(days / 365).toFixed(days < 3650 ? 1 : 0)}y ago`;
  }

  const catName = (id) => state.data.categories.find((c) => c.id === id)?.name || (id === "other" ? "Other" : id);
  const buzzOf = (r) => (r.mentions || []).reduce((s, m) => s + (m.points || 0), 0);
  const srcGroup = (s) => s.startsWith("trending") ? "trending" : s.startsWith("search") ? "search" : s;

  function growthLine(r) {
    if (r.gain_1d) return `<span class="gain" title="Stars gained today">▲ ${fmt(r.gain_1d)} today</span>`;
    if (r.gain_7d) return `<span class="gain" title="Stars gained this week">▲ ${fmt(r.gain_7d)} this week</span>`;
    if (r.age_days != null && r.age_days < 60 && r.velocity) return `<span class="gain" title="Average stars per day since creation">~${fmt(r.velocity)}/day</span>`;
    return "";
  }

  // ---------- repo card ----------
  function repoCard(r) {
    const [owner, name] = r.full_name.split("/");
    const ai = r.ai || {};
    const color = LANG_COLORS[r.language] || "var(--muted)";
    const beginnerIssues = `${r.url}/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22`;
    const links = [
      ext(r.url, "GitHub", "lnk"),
      r.homepage && /^https?:\/\//.test(r.homepage) ? ext(r.homepage, "Website", "lnk") : "",
      r.good_first_issues ? ext(beginnerIssues, "Beginner issues", "lnk stu") : "",
      ext(`https://star-history.com/#${r.full_name}&Date`, "Star history", "lnk"),
      ...(r.mentions || []).slice(0, 3).map((m) => ext(m.discussion_url, `💬 ${esc(m.community)} · ${fmt(m.points)}`, "lnk talk-lnk")),
    ].filter(Boolean).join("");
    const topics = (r.topics || []).slice(0, 6).map((t) =>
      `<button class="tag topic ${state.topic === t ? "on" : ""}" data-topic="${esc(t)}" title="Filter by topic">#${esc(t)}</button>`).join("");

    return `<article class="repo">
      <div class="repo-head">
        <img class="avatar" src="https://github.com/${esc(owner)}.png?size=64" alt="" loading="lazy" width="32" height="32">
        <div class="repo-title">
          ${ext(r.url, `<span class="owner">${esc(owner)}/</span>${esc(name)}`, "repo-name")}
          <div class="repo-nums">
            <span title="Stars">★ ${fmt(r.stars)}</span>${growthLine(r)}
            ${r.forks ? `<span title="Forks">⑂ ${fmt(r.forks)}</span>` : ""}
            ${r.language ? `<span><i class="dot" style="background:${color}"></i>${esc(r.language)}</span>` : ""}
            ${r.license && r.license !== "NOASSERTION" ? `<span>${esc(r.license)}</span>` : ""}
            ${r.age_days != null ? `<span title="Created">created ${ago(r.age_days)}</span>` : ""}
          </div>
        </div>
        ${r.trending_rank ? `<span class="rank-badge" title="Position on GitHub Trending today">#${r.trending_rank} trending</span>` : ""}
      </div>
      <p class="desc">${esc(ai.summary || r.description || "No description provided.")}</p>
      ${ai.problem ? `<p class="problem"><b>Solves:</b> ${esc(ai.problem)}</p>` : ""}
      ${ai.student_angle && r.for_students ? `<div class="student-note">🎓 ${esc(ai.student_angle)}</div>` : ""}
      <div class="tags">
        <button class="tag cat" data-cat="${esc(r.category)}">${esc(catName(r.category))}</button>
        ${r.for_students ? `<button class="tag stu" data-cat="${STUDENTS}">For students</button>` : ""}
        ${topics}
      </div>
      <div class="links">${links}</div>
    </article>`;
  }

  // ---------- renderers ----------
  function renderStats() {
    const d = state.data;
    const updated = new Date(d.generated_at);
    $("#updated").innerHTML = `Updated ${esc(updated.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }))}
      · refreshed daily · ${d.stats.sources.map(esc).join(", ")}`;
    const top = d.categories.filter((c) => c.id !== STUDENTS)[0];
    const newWeek = d.repos.filter((r) => r.age_days != null && r.age_days <= 7).length;
    $("#stats").innerHTML = [
      [fmt(d.stats.repos_tracked), "repositories tracked", ""],
      [String(newWeek), "new this week", "age=7&sort=velocity"],
      [esc(top?.name || "–"), "hottest topic", top ? `cat=${top.id}` : ""],
      [String(d.students.learning.length + d.students.contribute.length), "picks for students", `cat=${STUDENTS}`],
    ].map(([b, s, q]) => q
      ? `<a class="stat" href="?${q}" data-q="${q}"><b>${b}</b><span>${s} →</span></a>`
      : `<div class="stat"><b>${b}</b><span>${s}</span></div>`).join("");
  }

  function renderChips() {
    const cats = state.data.categories;
    const chip = (id, label, n, extra = "") =>
      `<button class="chip ${extra}" data-cat="${id}" aria-pressed="${state.cat === id}">${esc(label)}${n != null ? `<span class="n">${n}</span>` : ""}</button>`;
    const stu = cats.find((c) => c.id === STUDENTS);
    $("#chips").innerHTML =
      chip("all", "All topics", null) +
      chip(STUDENTS, "🎓 For Students", stu?.repo_count, "student") +
      cats.filter((c) => c.id !== STUDENTS && c.repo_count > 0).map((c) => chip(c.id, c.name, c.repo_count)).join("");
  }

  function renderTopics() {
    const cats = state.data.categories.filter((c) => c.id !== STUDENTS).slice(0, 12);
    $("#topics").innerHTML = cats.map((c, i) => `
      <li data-cat="${c.id}" class="${state.cat === c.id ? "active" : ""}" tabindex="0">
        <span class="rank">${i + 1}</span>
        <span class="name">${esc(c.name)}<span class="desc">${esc(c.description)}</span></span>
        <span class="right">${delta(c.growth_pct)}${spark(c.id)}</span>
      </li>`).join("");
  }

  function renderTalk() {
    let items = state.cat === STUDENTS ? state.data.students.discussions : state.data.discussions;
    if (state.talkSrc) items = items.filter((d) => d.source === state.talkSrc);
    document.querySelectorAll("#talk-tabs button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.src === state.talkSrc)));
    $("#talk").innerHTML = items.slice(0, 15).map((d) => {
      const article = d.url && d.url !== d.discussion_url ? ext(d.url, "article ↗", "meta-lnk") : "";
      const repo = d.repo ? ext(`https://github.com/${d.repo}`, "repo ↗", "meta-lnk") : "";
      return `<li>${ext(d.discussion_url, esc(d.title))}
        <span class="meta">${esc(d.community)} · ${fmt(d.points)} pts · ${fmt(d.comments)} comments ${article} ${repo}</span></li>`;
    }).join("") || `<li class="muted">No ${state.talkSrc === "reddit" ? "Reddit " : ""}discussions captured today.</li>`;
  }

  function ideasHtml(a) {
    return `<div class="ideas">${(a.ideas || []).map((i) => `
      <div class="idea"><b>${esc(i.title)}</b>
        <div class="badges"><span class="badge">${esc(i.difficulty)}</span>${i.good_for_students ? `<span class="badge stu">student-friendly</span>` : ""}</div>
        <div>${esc(i.pitch)}</div><div class="why">${esc(i.why_now)}</div></div>`).join("")}</div>`;
  }

  function leaders(names) {
    return names.map((n) => ext(`https://github.com/${n}`, esc(n), "leader")).join("");
  }

  function renderOpportunity() {
    const el = $("#opportunity");
    if (state.cat === "all" || state.cat === STUDENTS) { el.innerHTML = ""; return; }
    const c = state.data.categories.find((x) => x.id === state.cat);
    if (!c) { el.innerHTML = ""; return; }
    const a = c.analysis;
    el.innerHTML = `<section class="opp">
      <div class="opp-head"><h3>💡 Build opportunity: ${esc(c.name)}</h3>
        <span>${delta(c.growth_pct)} <span class="muted small">momentum ${fmt(c.momentum)} · ${c.repo_count} repos</span></span></div>
      <p class="muted">${esc(c.description)}</p>
      <div class="label">Leading repositories</div><div class="leaders">${leaders(c.top_repos)}</div>
      ${a ? `
        <div class="label">Why it's trending</div><p>${esc(a.why_trending)}</p>
        <div class="label">What already exists</div><p>${esc(a.what_exists)}</p>
        <div class="label">Gaps & unmet needs</div><ul>${a.gaps.map((g) => `<li>${esc(g)}</li>`).join("")}</ul>
        <div class="label">Tools worth building</div>${ideasHtml(a)}`
      : `<p class="muted small">AI analysis of gaps and build ideas appears here when the Claude layer is enabled.
          ${ext(`${REPO_URL}#deploy-your-own-daily-updates`, "How to enable it")}</p>`}
    </section>`;
  }

  function renderStudents() {
    const el = $("#students");
    if (state.cat !== STUDENTS) { el.innerHTML = ""; return; }
    const byName = Object.fromEntries(state.data.repos.map((r) => [r.full_name, r]));
    const c = state.data.categories.find((x) => x.id === STUDENTS);
    const list = (names, contribute) => names.map((n) => byName[n]).filter(Boolean).slice(0, 8).map((r) => {
      const href = contribute ? `${r.url}/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22` : r.url;
      return `<li>${ext(href, esc(r.full_name))}
        <span class="muted small"> · ★ ${fmt(r.stars)}${r.language ? " · " + esc(r.language) : ""}</span>
        ${r.description ? `<span class="mini-desc">${esc(r.description.slice(0, 110))}</span>` : ""}</li>`;
    }).join("") || `<li class="muted">Nothing today.</li>`;
    el.innerHTML = `<section class="opp stu">
      <div class="opp-head"><h3>🎓 For students</h3><span class="muted small">Learning resources, first contributions and portfolio ideas</span></div>
      <div class="cols">
        <div><div class="label">Learn from these</div><ul class="mini">${list(state.data.students.learning, false)}</ul></div>
        <div><div class="label">Make your first open-source contribution</div><ul class="mini">${list(state.data.students.contribute, true)}</ul>
          <p class="small muted">New to open source? Start with ${ext("https://github.com/firstcontributions/first-contributions", "first-contributions")}
          and ${ext("https://docs.github.com/en/get-started/exploring-projects-on-github/contributing-to-a-project", "GitHub's guide")}.</p></div>
      </div>
      ${c?.analysis ? `<div class="label">Portfolio project ideas</div>${ideasHtml(c.analysis)}` : ""}
    </section>`;
  }

  function filtered() {
    const q = state.q.trim().toLowerCase();
    const minStars = Number(state.stars) || 0;
    const maxAge = state.age ? Number(state.age) : null;
    const topic = state.topic.trim().toLowerCase().replace(/^#/, "");
    const rows = state.data.repos.filter((r) => {
      if (state.cat === STUDENTS && !r.for_students) return false;
      if (state.cat !== "all" && state.cat !== STUDENTS && !(r.tags || []).includes(state.cat)) return false;
      if (state.aud === "stu" && !r.for_students) return false;
      if (state.aud === "dev" && r.category === STUDENTS) return false;
      if (state.lang && r.language !== state.lang) return false;
      if (r.stars < minStars) return false;
      if (maxAge != null && (r.age_days == null || r.age_days > maxAge)) return false;
      if (state.src && !(r.sources || []).some((s) => srcGroup(s) === state.src)) return false;
      if (topic && !(r.topics || []).some((t) => t.toLowerCase() === topic)) return false;
      if (state.gfi && !r.good_first_issues) return false;
      if (state.buzz && !(r.mentions || []).length) return false;
      if (state.hasai && !r.ai) return false;
      if (state.rising && !(r.gain_1d || r.gain_7d)) return false;
      if (!q) return true;
      return [r.full_name, r.description, r.language, (r.topics || []).join(" "), r.ai?.summary, r.ai?.problem]
        .join(" ").toLowerCase().includes(q);
    });
    const key = state.sort;
    const val = (r) => key === "new" ? -(r.age_days ?? 1e9) : key === "buzz" ? buzzOf(r) : (r[key] ?? -1);
    rows.sort((a, b) => val(b) - val(a));
    return rows;
  }

  function renderRepos() {
    const rows = filtered();
    const scope = state.cat === "all" ? "" : ` in ${esc(state.cat === STUDENTS ? "For Students" : catName(state.cat))}`;
    $("#count").innerHTML = `${rows.length} repositories${scope}`;
    $("#repos").innerHTML = rows.slice(0, state.shown).map(repoCard).join("")
      || `<div class="empty">No repositories match these filters. <button class="btn small-btn" data-reset>Reset filters</button></div>`;
    $("#more").hidden = rows.length <= state.shown;
    $("#more").textContent = `Show more (${rows.length - state.shown} left)`;
  }

  function renderAll() {
    writeUrl();
    renderChips(); renderTopics(); renderTalk(); renderOpportunity(); renderStudents(); renderRepos();
  }

  function setCat(cat) {
    state.cat = state.cat === cat && cat !== "all" ? "all" : cat;
    state.shown = PAGE;
    renderAll();
    if (state.cat !== "all") document.querySelector(".main").scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function setFilter(key, value) {
    state[key] = value;
    state.shown = PAGE;
    writeUrl();
    renderRepos();
  }

  // ---------- events ----------
  document.addEventListener("click", (e) => {
    const stat = e.target.closest("a.stat[data-q]");
    if (stat) {
      e.preventDefault();
      Object.assign(state, DEFAULTS);
      const p = new URLSearchParams(stat.dataset.q);
      for (const [k, v] of p) state[k] = v;
      syncControls(); state.shown = PAGE; renderAll();
      return;
    }
    const topicBtn = e.target.closest("[data-topic]");
    if (topicBtn) {
      const t = topicBtn.dataset.topic;
      $("#topic").value = state.topic === t ? "" : t;
      setFilter("topic", $("#topic").value);
      return;
    }
    const cat = e.target.closest("[data-cat]");
    if (cat) { setCat(cat.dataset.cat); return; }
    if (e.target.closest("[data-reset]")) $("#reset").click();
  });
  document.addEventListener("keydown", (e) => {
    const li = e.target.closest?.("#topics li[data-cat]");
    if (li && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); setCat(li.dataset.cat); }
    if (e.key === "/" && document.activeElement?.tagName !== "INPUT") { e.preventDefault(); $("#q").focus(); }
  });

  let qTimer;
  $("#q").addEventListener("input", (e) => { clearTimeout(qTimer); qTimer = setTimeout(() => setFilter("q", e.target.value), 120); });
  $("#topic").addEventListener("change", (e) => setFilter("topic", e.target.value.trim().replace(/^#/, "")));
  for (const k of ["sort", "aud", "lang", "stars", "age", "src"]) $("#" + k).addEventListener("change", (e) => setFilter(k, e.target.value));
  for (const k of ["gfi", "buzz", "hasai", "rising"]) $("#" + k).addEventListener("change", (e) => setFilter(k, e.target.checked));
  $("#more").addEventListener("click", () => { state.shown += PAGE; renderRepos(); });
  $("#reset").addEventListener("click", () => {
    const cat = state.cat;
    Object.assign(state, DEFAULTS, { cat, shown: PAGE });
    syncControls(); renderAll(); toast("Filters reset");
  });
  $("#share").addEventListener("click", async () => {
    try { await navigator.clipboard.writeText(location.href); toast("Link copied"); }
    catch { toast("Copy the address bar to share this view"); }
  });
  $("#talk-tabs").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-src]");
    if (b) { state.talkSrc = b.dataset.src; renderTalk(); }
  });

  // ---------- static links ----------
  $("#gh-link").href = REPO_URL;
  $("#report-link").href = `${REPO_URL}/blob/main/reports/LATEST.md`;
  $("#foot-repo").href = REPO_URL;
  $("#foot-issues").href = `${REPO_URL}/issues/new`;
  $("#foot-reports").href = `${REPO_URL}/tree/main/reports`;
  if (matchMedia("(max-width: 700px)").matches) $("#filters").open = false;

  // ---------- boot ----------
  readUrl();
  Promise.all([
    fetch("data/latest.json", { cache: "no-cache" }).then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); }),
    fetch("data/trends.json", { cache: "no-cache" }).then((r) => (r.ok ? r.json() : null)).catch(() => null),
  ]).then(([data, trends]) => {
    state.data = data; state.trends = trends;
    if (state.cat !== "all" && state.cat !== STUDENTS && !data.categories.some((c) => c.id === state.cat)) state.cat = "all";
    const langs = [...new Set(data.repos.map((r) => r.language).filter(Boolean))].sort();
    $("#lang").insertAdjacentHTML("beforeend", langs.map((l) => `<option>${esc(l)}</option>`).join(""));
    const topicCounts = {};
    data.repos.forEach((r) => (r.topics || []).forEach((t) => { topicCounts[t] = (topicCounts[t] || 0) + 1; }));
    $("#topic-list").innerHTML = Object.entries(topicCounts).sort((a, b) => b[1] - a[1]).slice(0, 200)
      .map(([t, n]) => `<option value="${esc(t)}">${n} repos</option>`).join("");
    syncControls(); renderStats(); renderAll();
  }).catch((err) => {
    $("#repos").innerHTML = `<div class="empty">No data yet. Run <code>python -m trendforge run</code> to generate it. (${esc(err.message)})</div>`;
  });
})();
