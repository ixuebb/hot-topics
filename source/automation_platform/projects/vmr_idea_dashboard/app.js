const DATA = {
  ideas: "./data/idea_opportunities_finegrained.json",
  microProblems: "./data/micro_problem_clusters.json",
  adjacentMicroProblems: "./data/adjacent_micro_problem_clusters.json",
  microMethods: "./data/micro_method_clusters.json",
  paperCards: "./data/paper_micro_cards_index.json",
  paperIndex: "./data/paper_index.json",
  status: "./data/library_status.json",
  quality: "./data/finegrained_quality_report.json",
};

const FEATURED_IDEA_ID = "FI001";
const SVG_W = 1600;
const SVG_H = 900;

const state = {
  rawIdeas: [],
  ideas: [],
  microProblems: {},
  adjacentMicroProblems: {},
  microMethods: {},
  paperCards: new Map(),
  paperIndex: { summary: null, papers: {} },
  status: null,
  quality: null,
  mode: "forest",
  selectedIdeaId: FEATURED_IDEA_ID,
  rootFilter: "all",
  focusNodeId: null,
  selectedPaperId: null,
  hoverId: null,
  forestTransform: { x: 0, y: 0, k: 1 },
  rootTransform: defaultRootTransform(),
  forestGraph: null,
  rootGraph: null,
};

async function loadJson(path, fallback = null) {
  const response = await fetch(path);
  if (!response.ok) {
    if (fallback !== null) return fallback;
    throw new Error(`Failed to load ${path}`);
  }
  return response.json();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function defaultRootTransform() {
  return { x: 128, y: 145, k: 0.84 };
}

function uniq(values) {
  return [...new Set(values.filter(Boolean))];
}

function cleanText(value) {
  return String(value || "")
    .replace(/^#+\s*/g, "")
    .replace(/\s+/g, " ")
    .replace(/\s+([,.;:!?])/g, "$1")
    .trim();
}

function shortText(value, max = 120) {
  const text = cleanText(value);
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

function titleWords(value, max = 56) {
  const text = cleanText(value)
    .replace(/Mechanisms?:/gi, "")
    .replace(/Sparse Evidence Discovery in Long Videos/gi, "长视频稀疏证据发现")
    .replace(/Temporal Context Robustness/gi, "时间上下文鲁棒性")
    .replace(/Invalid Query and Open-Set Temporal Retrieval/gi, "开放集无效查询")
    .replace(/Weak Supervision and Annotation Reliability/gi, "弱监督与标注可靠性")
    .replace(/Compositional and Explicit Temporal Reasoning/gi, "组合式显式时间推理");
  return shortText(text, max);
}

function firstSentence(value, max = 180) {
  const text = cleanText(value);
  const pieces = text.split(/(?<=[.!?。！？])\s+/);
  return shortText(pieces[0] || text, max);
}

function paperById(id) {
  if (!id) return null;
  const card = state.paperCards.get(id) || {};
  const indexed = state.paperIndex.papers?.[id] || {};
  if (!card.paper_id && !indexed.paper_id) return null;
  return {
    ...indexed,
    ...card,
    figures: indexed.figures || [],
    tables: indexed.tables || [],
    abstract: indexed.abstract || "",
    introduction: indexed.introduction || "",
    venue_or_source: card.venue_or_source || indexed.venue || indexed.source || "",
  };
}

function allPapers() {
  const merged = new Map();
  for (const [id, card] of state.paperCards.entries()) merged.set(id, paperById(id));
  for (const id of Object.keys(state.paperIndex.papers || {})) {
    if (!merged.has(id)) merged.set(id, paperById(id));
  }
  return [...merged.values()].filter(Boolean);
}

function findPaperByKeyword(...keywords) {
  const lowered = keywords.map((item) => String(item).toLowerCase());
  return allPapers().find((paper) => {
    const blob = `${paper.title || ""} ${paper.abstract || ""} ${paper.introduction || ""}`.toLowerCase();
    return lowered.every((keyword) => blob.includes(keyword));
  });
}

function collectEvidenceFromCard(card, limit = 4) {
  const snippets = [];
  const add = (ev, role = "") => {
    if (!ev?.quote) return;
    const quote = shortText(ev.quote, 220);
    if (!quote || snippets.some((item) => item.quote === quote)) return;
    snippets.push({
      quote,
      section: ev.section || "",
      role: role || ev.role || "",
      page: ev.page || null,
    });
  };
  const addGroup = (items = [], role = "") => {
    for (const item of items || []) {
      for (const ev of item.evidence || []) add(ev, role || item.role);
    }
  };
  addGroup(card?.intro_motivation_chain?.prior_work_limitation, "limitation");
  addGroup(card?.intro_motivation_chain?.core_problem_transition, "problem");
  addGroup(card?.intro_motivation_chain?.method_transition, "method");
  addGroup(card?.problem_units, "problem");
  addGroup(card?.method_units, "method");
  return snippets.slice(0, limit);
}

function evidenceForIdeaPaper(idea, paperId) {
  const rows = [...(idea.source_papers || []), ...(idea.target_papers || [])].filter((paper) => paper.paper_id === paperId);
  const snippets = [];
  for (const paper of rows) {
    for (const ev of paper.evidence || []) {
      if (!ev.quote) continue;
      snippets.push({
        quote: shortText(ev.quote, 220),
        section: ev.section || "",
        role: ev.role || "",
      });
    }
  }
  return snippets;
}

function evidenceStrength(idea) {
  const papers = [...(idea.source_papers || []), ...(idea.target_papers || [])];
  const evidenceCount = papers.reduce((sum, paper) => sum + (paper.evidence || []).length, 0);
  const hasExperiment = /charades|qvhighlights|activitynet|tacos|didemo|ego4d|vidstg/i.test(idea.minimum_verification_experiment || "");
  return clamp(38 + papers.length * 6 + evidenceCount * 3 + (hasExperiment ? 8 : 0), 0, 100);
}

function noveltyScore(idea) {
  const underuse = /0 direct|underused|currently underused/i.test(idea.why_currently_underused || "");
  const crossTask = idea.is_cross_task_transfer ? 10 : 0;
  const recentYears = [...(idea.source_papers || []), ...(idea.target_papers || [])].filter((paper) => Number(paper.year) >= 2025).length;
  return clamp(58 + crossTask + recentYears * 4 + (underuse ? 14 : 4), 0, 100);
}

function verifiabilityScore(idea) {
  const text = `${idea.minimum_verification_experiment || ""} ${idea.target_papers?.map((p) => p.title).join(" ") || ""}`;
  const datasets = (text.match(/Charades|QVHighlights|ActivityNet|TACoS|DiDeMo|Ego4D|VidSTG|HC-STVG/gi) || []).length;
  const riskPenalty = /high/i.test(idea.risk_level || "") ? 14 : /medium/i.test(idea.risk_level || "") ? 6 : 0;
  return clamp(55 + datasets * 7 + (idea.minimum_verification_experiment ? 12 : 0) - riskPenalty, 0, 100);
}

function recommendedDatasets(idea) {
  const text = `${idea.minimum_verification_experiment || ""} ${idea.technical_sketch || ""}`;
  const names = ["Charades-STA", "QVHighlights", "ActivityNet Captions", "TACoS", "DiDeMo", "Ego4D-NLQ", "VidSTG", "HC-STVG"];
  const found = names.filter((name) => text.toLowerCase().includes(name.toLowerCase().replace("-nlq", "")));
  return uniq(found).slice(0, 4).join(" / ") || "Charades-STA / QVHighlights / ActivityNet Captions";
}

function normalizeIdea(raw, index) {
  const target = state.microProblems[raw.target_micro_problem_id] || state.adjacentMicroProblems[raw.target_micro_problem_id] || {};
  const method = state.microMethods[raw.source_micro_method_id] || {};
  const featured = raw.idea_id === FEATURED_IDEA_ID;
  const title = featured
    ? "面向长视频稀疏证据发现的结构化证据链世界模型"
    : `${titleWords(raw.source_micro_method || method.name, 34)} → ${titleWords(raw.target_micro_problem || target.name, 38)}`;
  const summary = featured
    ? "通过结构化证据链与显式记忆机制，提升长视频时序定位中对低频关键证据的发现能力。"
    : firstSentence(raw.technical_sketch || raw.candidate_idea || raw.transferable_mechanism, 150);
  return {
    id: raw.idea_id,
    raw,
    index,
    title,
    summary,
    trunk: summary,
    score: Number(raw.score || 0),
    evidence: evidenceStrength(raw),
    novelty: noveltyScore(raw),
    verifiability: verifiabilityScore(raw),
    risk: raw.risk_level || "medium",
    targetId: raw.target_micro_problem_id,
    methodId: raw.source_micro_method_id,
    target,
    method,
    datasets: featured ? "QVHighlights / Charades-STA / ActivityNet Captions / Ego4D-NLQ" : recommendedDatasets(raw),
    featured,
  };
}

function prepareIdeas() {
  state.ideas = state.rawIdeas
    .map((raw, index) => normalizeIdea(raw, index))
    .sort((a, b) => (b.featured - a.featured) || b.score - a.score);
  if (!state.ideas.some((idea) => idea.id === state.selectedIdeaId)) {
    state.selectedIdeaId = state.ideas[0]?.id || null;
  }
}

function selectedIdea() {
  return state.ideas.find((idea) => idea.id === state.selectedIdeaId) || state.ideas[0] || null;
}

function renderApp() {
  if (state.mode === "root") renderRootView();
  else renderForestView();
}

function renderMetric(value, label) {
  return `<div class="hud-metric"><strong>${escapeHtml(value)}</strong><span>${escapeHtml(label)}</span></div>`;
}

function summaryMetrics() {
  const cards = [...state.paperCards.values()];
  return [
    [state.paperIndex.summary?.paper_count ?? state.status?.paper_dirs ?? cards.length, "文献目录"],
    [cards.filter((paper) => paper.task_scope?.is_core_video_moment_retrieval).length, "核心论文"],
    [state.ideas.length, "候选 Idea"],
    [Object.keys(state.microProblems).length, "微问题"],
    [Object.keys(state.microMethods).length, "微方法"],
  ];
}

function renderForestView() {
  const graph = computeForestGraph();
  state.forestGraph = graph;
  const app = document.querySelector("#app");
  app.className = "app-shell forest-mode";
  app.innerHTML = `
    <header class="forest-hud">
      <div class="brand-block">
        <span class="eyebrow">Video Moment Retrieval · Idea Forest</span>
        <h1>先看 Idea，再向下挖根</h1>
        <p>节点大小代表潜力分，亮度代表证据强度；相互靠近或相连的 Idea 共享问题、方法或失败模式。</p>
      </div>
      <div class="hud-metrics">${summaryMetrics().map(([value, label]) => renderMetric(value, label)).join("")}</div>
    </header>

    <main class="graph-stage">
      <svg id="forestSvg" viewBox="0 0 ${SVG_W} ${SVG_H}" role="img" aria-label="Idea 森林星图">
        ${svgDefs()}
        <g id="forestViewport" transform="${transformString(state.forestTransform)}">
          ${renderForestLinks(graph.links)}
          ${graph.nodes.map(renderForestNode).join("")}
        </g>
      </svg>
      <div class="stage-toolbar">
        <button class="ghost-button" type="button" data-reset-forest>重置视图</button>
        <button class="primary-button" type="button" data-open-featured>打开默认 Idea</button>
      </div>
      <div class="legend-panel">
        <span><i class="legend-dot idea-dot"></i>Idea</span>
        <span><i class="legend-line strong"></i>共享问题</span>
        <span><i class="legend-line weak"></i>共享方法</span>
        <span>滚轮缩放 · 拖拽移动 · 点击挖根</span>
      </div>
      <div id="hoverCard" class="hover-card hidden"></div>
    </main>
  `;
  bindGraphPanZoom("forestSvg", "forestViewport", "forestTransform");
  bindForestHover();
}

function computeForestGraph() {
  const ideas = state.ideas;
  const minScore = Math.min(...ideas.map((idea) => idea.score));
  const maxScore = Math.max(...ideas.map((idea) => idea.score));
  const groups = new Map();
  for (const idea of ideas) {
    const groupId = idea.targetId || "unknown";
    if (!groups.has(groupId)) groups.set(groupId, []);
    groups.get(groupId).push(idea);
  }
  const sortedGroups = [...groups.entries()].sort((a, b) => b[1].length - a[1].length);
  const clusterRadius = 390;
  const center = { x: SVG_W / 2, y: SVG_H / 2 + 42 };
  const nodes = [];
  sortedGroups.forEach(([groupId, groupIdeas], groupIndex) => {
    const angle = (Math.PI * 2 * groupIndex) / Math.max(1, sortedGroups.length);
    const groupCenter = {
      x: center.x + Math.cos(angle) * clusterRadius,
      y: center.y + Math.sin(angle) * clusterRadius * 0.58,
    };
    groupIdeas
      .sort((a, b) => b.score - a.score)
      .forEach((idea, itemIndex) => {
        const localAngle = itemIndex * 2.399963 + groupIndex * 0.31;
        const localRadius = 28 + Math.sqrt(itemIndex) * 94 + itemIndex * 2.5;
        const scoreT = (idea.score - minScore) / Math.max(0.01, maxScore - minScore);
        const radius = 27 + scoreT * 16 + (idea.featured ? 24 : 0);
        const featuredOffset = idea.featured ? { x: -40, y: -40 } : { x: 0, y: 0 };
        nodes.push({
          ...idea,
          groupId,
          r: radius,
          x: idea.featured ? center.x + featuredOffset.x : clamp(groupCenter.x + Math.cos(localAngle) * localRadius, 90, SVG_W - 90),
          y: idea.featured ? center.y + featuredOffset.y : clamp(groupCenter.y + Math.sin(localAngle) * localRadius * 0.56, 150, SVG_H - 95),
        });
      });
  });

  const nodeById = new Map(nodes.map((node) => [node.id, node]));
  const links = [];
  const addGroupLinks = (key, type, strength) => {
    const buckets = new Map();
    for (const node of nodes) {
      const value = node[key];
      if (!value) continue;
      if (!buckets.has(value)) buckets.set(value, []);
      buckets.get(value).push(node);
    }
    for (const members of buckets.values()) {
      const sorted = members.sort((a, b) => b.score - a.score).slice(0, 8);
      for (let i = 0; i < sorted.length - 1; i += 1) {
        links.push({
          id: `${type}-${sorted[i].id}-${sorted[i + 1].id}`,
          source: sorted[i].id,
          target: sorted[i + 1].id,
          type,
          strength,
        });
      }
      const featured = sorted.find((node) => node.featured);
      if (featured) {
        for (const node of sorted.filter((item) => item.id !== featured.id).slice(0, 5)) {
          links.push({
            id: `${type}-${featured.id}-${node.id}`,
            source: featured.id,
            target: node.id,
            type,
            strength: strength + 0.15,
          });
        }
      }
    }
  };
  addGroupLinks("targetId", "shared-problem", 0.82);
  addGroupLinks("methodId", "shared-method", 0.58);
  return {
    nodes,
    nodeById,
    links: links
      .filter((link, index, arr) => arr.findIndex((item) => item.id === link.id) === index)
      .filter((link) => nodeById.has(link.source) && nodeById.has(link.target))
      .slice(0, 180),
  };
}

function svgDefs() {
  return `
    <defs>
      <radialGradient id="ideaGlow" cx="45%" cy="35%" r="72%">
        <stop offset="0%" stop-color="#fff9cc" stop-opacity="0.98" />
        <stop offset="42%" stop-color="#5ce8ff" stop-opacity="0.88" />
        <stop offset="100%" stop-color="#2f6bff" stop-opacity="0.72" />
      </radialGradient>
      <radialGradient id="featuredGlow" cx="42%" cy="34%" r="75%">
        <stop offset="0%" stop-color="#fff8d2" stop-opacity="1" />
        <stop offset="40%" stop-color="#ffc84b" stop-opacity="0.95" />
        <stop offset="100%" stop-color="#0a85ff" stop-opacity="0.78" />
      </radialGradient>
      <filter id="softGlow" x="-80%" y="-80%" width="260%" height="260%">
        <feGaussianBlur stdDeviation="6" result="coloredBlur" />
        <feMerge>
          <feMergeNode in="coloredBlur" />
          <feMergeNode in="SourceGraphic" />
        </feMerge>
      </filter>
      <filter id="wideGlow" x="-140%" y="-140%" width="380%" height="380%">
        <feGaussianBlur stdDeviation="13" result="coloredBlur" />
        <feMerge>
          <feMergeNode in="coloredBlur" />
          <feMergeNode in="SourceGraphic" />
        </feMerge>
      </filter>
      <linearGradient id="rootLine" x1="0%" x2="0%" y1="0%" y2="100%">
        <stop offset="0%" stop-color="#ffc857" stop-opacity="0.9" />
        <stop offset="35%" stop-color="#3ea2ff" stop-opacity="0.74" />
        <stop offset="70%" stop-color="#8b5cf6" stop-opacity="0.72" />
        <stop offset="100%" stop-color="#b7c7db" stop-opacity="0.62" />
      </linearGradient>
    </defs>
  `;
}

function renderForestLinks(links) {
  return `
    <g class="forest-links">
      ${links.map((link) => {
        const source = state.forestGraph?.nodeById?.get(link.source);
        const target = state.forestGraph?.nodeById?.get(link.target);
        if (!source || !target) return "";
        const opacity = link.type === "shared-problem" ? 0.34 : 0.2;
        const width = link.type === "shared-problem" ? 2.2 : 1.2;
        return `<path class="forest-link ${link.type}" data-source="${link.source}" data-target="${link.target}" d="${curve(source, target, 0.18)}" stroke-width="${width}" opacity="${opacity}" />`;
      }).join("")}
    </g>
  `;
}

function renderForestNode(node) {
  const lines = wrapText(node.title, node.featured ? 13 : 11, 3);
  const glowOpacity = 0.22 + node.evidence / 145;
  const pulseDelay = (node.index % 9) * 0.25;
  return `
    <g class="idea-node ${node.featured ? "featured" : ""}" data-idea="${node.id}" transform="translate(${node.x.toFixed(1)},${node.y.toFixed(1)})" style="--r:${node.r.toFixed(1)}px; --glow:${glowOpacity.toFixed(2)}; --delay:${pulseDelay}s">
      <circle class="idea-halo" r="${(node.r * 1.34).toFixed(1)}"></circle>
      <circle class="idea-core" r="${node.r.toFixed(1)}" fill="${node.featured ? "url(#featuredGlow)" : "url(#ideaGlow)"}"></circle>
      <text class="idea-score" y="${(-node.r + 23).toFixed(1)}">潜力 ${node.score.toFixed(1)}</text>
      <text class="idea-title" y="-7">
        ${lines.map((line, index) => `<tspan x="0" dy="${index === 0 ? 0 : 15}">${escapeHtml(line)}</tspan>`).join("")}
      </text>
      <text class="idea-mini" y="${(node.r - 20).toFixed(1)}">证 ${node.evidence} · 新 ${node.novelty} · 验 ${node.verifiability}</text>
    </g>
  `;
}

function curve(source, target, bend = 0.24) {
  const dx = target.x - source.x;
  const dy = target.y - source.y;
  const cx1 = source.x + dx * 0.5 - dy * bend;
  const cy1 = source.y + dy * 0.5 + dx * bend;
  const cx2 = source.x + dx * 0.5 + dy * bend;
  const cy2 = source.y + dy * 0.5 - dx * bend;
  return `M ${source.x.toFixed(1)} ${source.y.toFixed(1)} C ${cx1.toFixed(1)} ${cy1.toFixed(1)}, ${cx2.toFixed(1)} ${cy2.toFixed(1)}, ${target.x.toFixed(1)} ${target.y.toFixed(1)}`;
}

function verticalCurve(source, target) {
  const midY = (source.y + target.y) / 2;
  return `M ${source.x.toFixed(1)} ${source.y.toFixed(1)} C ${source.x.toFixed(1)} ${midY.toFixed(1)}, ${target.x.toFixed(1)} ${midY.toFixed(1)}, ${target.x.toFixed(1)} ${target.y.toFixed(1)}`;
}

function wrapText(text, maxChars, maxLines = 2) {
  const clean = cleanText(text);
  const lines = [];
  let cursor = 0;
  while (cursor < clean.length && lines.length < maxLines) {
    lines.push(clean.slice(cursor, cursor + maxChars));
    cursor += maxChars;
  }
  if (cursor < clean.length && lines.length) lines[lines.length - 1] = `${lines[lines.length - 1].slice(0, Math.max(2, maxChars - 1))}…`;
  return lines.length ? lines : ["Untitled"];
}

function transformString(transform) {
  return `translate(${transform.x.toFixed(2)} ${transform.y.toFixed(2)}) scale(${transform.k.toFixed(3)})`;
}

function bindGraphPanZoom(svgId, viewportId, transformKey) {
  const svg = document.querySelector(`#${svgId}`);
  const viewport = document.querySelector(`#${viewportId}`);
  if (!svg || !viewport) return;
  let dragging = false;
  let last = null;

  const point = (event) => {
    const rect = svg.getBoundingClientRect();
    return {
      x: ((event.clientX - rect.left) / rect.width) * SVG_W,
      y: ((event.clientY - rect.top) / rect.height) * SVG_H,
    };
  };
  const apply = () => viewport.setAttribute("transform", transformString(state[transformKey]));

  svg.addEventListener("wheel", (event) => {
    event.preventDefault();
    const transform = state[transformKey];
    const before = point(event);
    const scale = event.deltaY < 0 ? 1.09 : 0.92;
    const nextK = clamp(transform.k * scale, 0.45, 2.8);
    const ratio = nextK / transform.k;
    transform.x = before.x - (before.x - transform.x) * ratio;
    transform.y = before.y - (before.y - transform.y) * ratio;
    transform.k = nextK;
    apply();
  }, { passive: false });

  svg.addEventListener("pointerdown", (event) => {
    if (event.target.closest(".idea-node, .root-node")) return;
    dragging = true;
    last = point(event);
    svg.setPointerCapture(event.pointerId);
  });
  svg.addEventListener("pointermove", (event) => {
    if (!dragging || !last) return;
    const now = point(event);
    const transform = state[transformKey];
    transform.x += now.x - last.x;
    transform.y += now.y - last.y;
    last = now;
    apply();
  });
  svg.addEventListener("pointerup", () => {
    dragging = false;
    last = null;
  });
}

function bindForestHover() {
  const svg = document.querySelector("#forestSvg");
  const hoverCard = document.querySelector("#hoverCard");
  if (!svg || !hoverCard) return;
  svg.addEventListener("mousemove", (event) => {
    const node = event.target.closest(".idea-node");
    if (!node) {
      clearForestHighlight();
      return;
    }
    const idea = state.ideas.find((item) => item.id === node.dataset.idea);
    if (!idea) return;
    setForestHighlight(idea.id);
    hoverCard.classList.remove("hidden");
    hoverCard.style.left = `${event.clientX + 18}px`;
    hoverCard.style.top = `${event.clientY + 18}px`;
    hoverCard.innerHTML = `
      <strong>${escapeHtml(idea.title)}</strong>
      <p>${escapeHtml(idea.summary)}</p>
      <div class="mini-bars">
        ${miniBar("潜力", idea.score * 9.3)}
        ${miniBar("证据", idea.evidence)}
        ${miniBar("新颖", idea.novelty)}
        ${miniBar("可验", idea.verifiability)}
      </div>
      <small>点击进入树根探索视图</small>
    `;
  });
  svg.addEventListener("mouseleave", clearForestHighlight);
}

function setForestHighlight(ideaId) {
  document.querySelectorAll(".idea-node").forEach((node) => {
    node.classList.toggle("dimmed", node.dataset.idea !== ideaId);
    node.classList.toggle("active", node.dataset.idea === ideaId);
  });
  document.querySelectorAll(".forest-link").forEach((link) => {
    const active = link.dataset.source === ideaId || link.dataset.target === ideaId;
    link.classList.toggle("active", active);
    link.classList.toggle("dimmed", !active);
  });
}

function clearForestHighlight() {
  const hoverCard = document.querySelector("#hoverCard");
  if (hoverCard) hoverCard.classList.add("hidden");
  document.querySelectorAll(".idea-node, .forest-link").forEach((item) => {
    item.classList.remove("dimmed", "active");
  });
}

function miniBar(label, value) {
  const width = clamp(Math.round(value), 0, 100);
  return `<span><b>${escapeHtml(label)}</b><i><em style="width:${width}%"></em></i>${width}</span>`;
}

function renderRootView() {
  const idea = selectedIdea();
  const graph = buildRootGraph(idea);
  const visible = filterRootGraph(graph);
  state.rootGraph = graph;
  const app = document.querySelector("#app");
  app.className = "app-shell root-mode";
  app.innerHTML = `
    <header class="root-hud">
      <button class="back-button" type="button" data-back-forest>返回 Idea 森林</button>
      <div class="root-title-block">
        <span class="eyebrow">Root Exploration View</span>
        <h1>${escapeHtml(idea.title)}</h1>
        <p>${escapeHtml(idea.summary)}</p>
      </div>
      <div class="root-score-strip">
        ${renderMetric(idea.score.toFixed(1), "潜力")}
        ${renderMetric(idea.novelty, "新颖度")}
        ${renderMetric(idea.evidence, "证据")}
        ${renderMetric(idea.verifiability, "可验证")}
      </div>
    </header>

    <main class="root-stage">
      <svg id="rootSvg" viewBox="0 0 ${SVG_W} ${SVG_H}" role="img" aria-label="Idea 树根探索图谱">
        ${svgDefs()}
        <g id="rootViewport" transform="${transformString(state.rootTransform)}">
          <g class="root-links">${visible.edges.map(renderRootEdge).join("")}</g>
          <g class="root-nodes">${visible.nodes.map(renderRootNode).join("")}</g>
        </g>
      </svg>
      <div class="root-controls">
        <button class="root-filter ${state.rootFilter === "all" ? "active" : ""}" type="button" data-root-filter="all">展开全部</button>
        <button class="root-filter ${state.rootFilter === "main" ? "active" : ""}" type="button" data-root-filter="main">只看主路径</button>
        <button class="root-filter ${state.rootFilter === "strong" ? "active" : ""}" type="button" data-root-filter="strong">高置信度根系</button>
        ${state.focusNodeId ? `<button class="root-filter active" type="button" data-root-filter="branch">当前分支</button>` : ""}
        <button class="ghost-button" type="button" data-reset-root>重置视图</button>
      </div>
      <aside class="idea-claim-panel">
        <span>主干</span>
        <p>${escapeHtml(idea.trunk)}</p>
        <small>推荐验证：${escapeHtml(idea.datasets)} · 风险：${escapeHtml(idea.risk)}</small>
      </aside>
      <div class="root-legend">
        <span><i class="legend-dot problem-dot"></i>研究缺口</span>
        <span><i class="legend-dot failure-dot"></i>失败模式 / 根因</span>
        <span><i class="legend-dot method-dot"></i>已有方法 / 迁移机制</span>
        <span><i class="legend-dot paper-dot"></i>论文证据</span>
        <span><i class="legend-line weak"></i>共享证据或机制</span>
      </div>
      ${state.selectedPaperId ? renderPaperDrawer(state.selectedPaperId) : ""}
      <div id="rootHoverCard" class="hover-card hidden"></div>
    </main>
  `;
  bindGraphPanZoom("rootSvg", "rootViewport", "rootTransform");
  bindRootHover();
}

function buildRootGraph(idea) {
  if (!idea) return { nodes: [], edges: [], nodeById: new Map(), edgeById: new Map(), ancestors: new Map(), descendants: new Map() };
  const graph = idea.featured ? buildFeaturedRootGraph(idea) : buildGenericRootGraph(idea);
  graph.nodeById = new Map(graph.nodes.map((node) => [node.id, node]));
  graph.edgeById = new Map(graph.edges.map((edge) => [edge.id, edge]));
  graph.ancestors = computeAncestors(graph.nodes, graph.edges);
  graph.descendants = computeDescendants(graph.nodes, graph.edges);
  return graph;
}

function node(id, type, label, detail, x, y, options = {}) {
  return {
    id,
    type,
    label: cleanText(label),
    detail: cleanText(detail),
    x,
    y,
    confidence: options.confidence ?? 75,
    paperId: options.paperId || "",
    evidence: options.evidence || [],
    meta: options.meta || "",
    size: options.size || 1,
  };
}

function edge(source, target, type = "support", strength = 0.72, label = "") {
  return {
    id: `${source}->${target}`,
    source,
    target,
    type,
    strength,
    label,
  };
}

function buildFeaturedRootGraph(idea) {
  const raw = idea.raw;
  const smore = findPaperByKeyword("see more", "store less") || raw.source_papers?.find((paper) => /smore|see more/i.test(paper.title));
  const diffusion = findPaperByKeyword("diffusion", "video grounding");
  const omtg = findPaperByKeyword("one-to-many", "temporal grounding");
  const structured = findPaperByKeyword("bridging time and space");
  const evidenceChain = findPaperByKeyword("evidence chain");
  const locformer = findPaperByKeyword("locformer", "long untrimmed");
  const targetPaper = raw.target_papers?.[0] ? paperById(raw.target_papers[0].paper_id) || raw.target_papers[0] : null;
  const papers = uniq([smore?.paper_id, diffusion?.paper_id, omtg?.paper_id, structured?.paper_id, evidenceChain?.paper_id, locformer?.paper_id, targetPaper?.paper_id])
    .map((id) => paperById(id) || [...(raw.source_papers || []), ...(raw.target_papers || [])].find((paper) => paper.paper_id === id))
    .filter(Boolean);

  const nodes = [
    node("idea", "idea", idea.title, "一个从长视频稀疏证据问题中长出的候选研究主张。", 800, 172, { confidence: 96, size: 1.28 }),
    node("trunk", "trunk", "结构化证据链 + 显式记忆机制", idea.trunk, 800, 292, { confidence: 92, size: 1.1 }),
    node("p_sparse", "problem", "长视频中的稀疏证据发现困难", "关键证据在长视频中低频、短暂且容易被平均池化或稀疏采样漏掉。", 430, 425, { confidence: 92 }),
    node("p_reason", "problem", "显式时间推理不足", "模型常把定位看成片段打分，而不是维护可解释的时间证据链。", 800, 425, { confidence: 86 }),
    node("p_memory", "problem", "跨片段长程记忆不稳定", "长上下文下关键线索被冗余 token 和相邻片段干扰，证据链难以持续保持。", 1170, 425, { confidence: 84 }),
    node("f_salient", "failure", "偏向显著片段，忽略低频关键证据", "视觉上显著或高频出现的片段获得更高注意力，真正决定答案的低频证据被淹没。", 250, 565, { confidence: 88 }),
    node("f_redundant", "failure", "冗余 token 淹没关键信号", "密集帧 token 带来高显存和噪声，稀疏关键 token 的相对权重下降。", 560, 565, { confidence: 94 }),
    node("f_alignment", "failure", "query 与局部证据对齐过弱", "查询语义无法稳定指向关键局部片段，尤其在开放描述或多事件组合中更明显。", 870, 565, { confidence: 80 }),
    node("f_chain", "failure", "跨片段证据链无法持续保持", "模型难以把早期线索、后续状态和最终边界连成可验证的推理链。", 1180, 565, { confidence: 87 }),
    node("m_smore", "method", "SMORE", "用查询感知的重要性调制和信息分辨率控制，减少冗余视觉 token 并保留关键帧线索。", 205, 705, { confidence: 92 }),
    node("m_diffusion", "method", "DiffusionVG", "通过迭代式边界细化，把一次性预测改为逐步修正的时间定位过程。", 430, 730, { confidence: 80 }),
    node("m_omtg", "method", "OMTG", "从一对一定位扩展到一对多时刻，适合将证据链拆成多个相关 temporal anchors。", 675, 705, { confidence: 82 }),
    node("m_reasoning", "method", "structured reasoning", "把时间定位转换为可组合、可追踪的推理步骤，让证据选择不只是黑箱打分。", 930, 730, { confidence: 84 }),
    node("m_memory", "method", "memory compression", "用记忆压缩保存跨片段低频线索，降低全量帧 token 对关键证据的遮蔽。", 1180, 705, { confidence: 86 }),
    node("m_chain", "method", "evidence chain construction", "显式维护证据分配、证据延续和边界验证，使根因能够被实验诊断。", 1390, 730, { confidence: 90 }),
  ];

  papers.slice(0, 7).forEach((paper, index) => {
    const x = 170 + index * 205;
    const evidence = evidenceForIdeaPaper(raw, paper.paper_id).concat(collectEvidenceFromCard(paper, 2)).slice(0, 3);
    nodes.push(node(`paper_${index}`, "paper", paper.title || "Untitled paper", `${paper.year || ""} · ${paper.venue_or_source || paper.venue || ""}`, x, 840, {
      confidence: 68 + Math.min(22, evidence.length * 7),
      paperId: paper.paper_id,
      evidence,
      meta: `${paper.year || ""} · ${paper.venue_or_source || paper.venue || ""}`,
    }));
  });

  const edges = [
    edge("idea", "trunk", "claim", 1, "核心主张"),
    edge("trunk", "p_sparse", "root", 0.92, "直接缺口"),
    edge("trunk", "p_reason", "root", 0.86, "直接缺口"),
    edge("trunk", "p_memory", "root", 0.84, "直接缺口"),
    edge("p_sparse", "f_salient", "cause", 0.88, "稀疏证据被显著片段覆盖"),
    edge("p_sparse", "f_redundant", "cause", 0.94, "冗余 token 稀释证据"),
    edge("p_reason", "f_alignment", "cause", 0.8, "局部证据对齐不足"),
    edge("p_reason", "f_chain", "cross-cause", 0.74, "需要跨片段推理"),
    edge("p_memory", "f_redundant", "cross-cause", 0.78, "记忆受 token 噪声影响"),
    edge("p_memory", "f_chain", "cause", 0.87, "证据延续失败"),
    edge("f_redundant", "m_smore", "transfer", 0.93, "信息分辨率 / 冗余压缩"),
    edge("f_alignment", "m_diffusion", "transfer", 0.76, "迭代修正局部对齐"),
    edge("f_chain", "m_omtg", "transfer", 0.78, "多时刻锚点"),
    edge("f_alignment", "m_reasoning", "transfer", 0.82, "显式推理步骤"),
    edge("f_redundant", "m_memory", "transfer", 0.88, "记忆压缩"),
    edge("f_chain", "m_chain", "transfer", 0.92, "证据链构造"),
    edge("m_reasoning", "m_chain", "shared-mechanism", 0.62, "共享结构化推理"),
    edge("m_smore", "m_memory", "shared-mechanism", 0.66, "共享 token 压缩"),
    edge("m_omtg", "m_chain", "shared-mechanism", 0.6, "共享多证据锚点"),
  ];
  const methodPaper = [
    ["m_smore", smore],
    ["m_diffusion", diffusion],
    ["m_omtg", omtg],
    ["m_reasoning", structured],
    ["m_chain", evidenceChain],
    ["m_memory", locformer || smore],
    ["p_sparse", targetPaper],
  ];
  methodPaper.forEach(([methodId, paper]) => {
    if (!paper?.paper_id) return;
    const paperNode = nodes.find((item) => item.paperId === paper.paper_id);
    if (paperNode) edges.push(edge(methodId, paperNode.id, "evidence", 0.72, "论文证据"));
  });
  return { nodes, edges };
}

function buildGenericRootGraph(idea) {
  const raw = idea.raw;
  const problem = idea.target || {};
  const method = idea.method || {};
  const nodes = [
    node("idea", "idea", idea.title, "候选迁移式研究 Idea。", 800, 172, { confidence: 88, size: 1.22 }),
    node("trunk", "trunk", "把可迁移机制接到目标失败模式上", idea.trunk, 800, 292, { confidence: 84 }),
    node("p_target", "problem", titleWords(problem.name || raw.target_micro_problem, 46), problem.canonical_question || raw.target_micro_problem, 470, 425, { confidence: 82 }),
    node("p_gap", "problem", "当前解决方案仍未充分覆盖", raw.why_currently_underused || "已有方法和目标问题之间存在低直接连接度。", 800, 425, { confidence: 76 }),
    node("p_transfer", "problem", "跨问题迁移窗口", raw.shared_failure_mode || "两个问题共享相近失败机制或证据组织需求。", 1130, 425, { confidence: raw.is_cross_task_transfer ? 82 : 68 }),
    node("f_mode", "failure", titleWords(problem.failure_mode || raw.shared_failure_mode || "失败模式", 42), problem.root_cause || raw.shared_failure_mode || "", 480, 565, { confidence: 80 }),
    node("f_root", "failure", titleWords(problem.root_cause || "根因解释", 42), raw.shared_failure_mode || problem.canonical_question || "", 800, 565, { confidence: 76 }),
    node("f_underuse", "failure", "已有机制尚未被直接使用", raw.why_currently_underused || "", 1120, 565, { confidence: 78 }),
    node("m_source", "method", titleWords(method.name || raw.source_micro_method, 42), method.core_mechanism || raw.transferable_mechanism || "", 520, 715, { confidence: 82 }),
    node("m_transfer", "method", "可迁移机制", raw.transferable_mechanism || raw.technical_sketch || "", 820, 715, { confidence: 84 }),
    node("m_components", "method", titleWords((method.components || []).slice(0, 4).join(" / ") || "方法组件", 42), (method.capability_facets || []).join(" / "), 1120, 715, { confidence: 74 }),
  ];
  const paperPool = [...(raw.target_papers || []), ...(raw.source_papers || [])]
    .filter((paper, index, arr) => arr.findIndex((item) => item.paper_id === paper.paper_id) === index)
    .slice(0, 7);
  paperPool.forEach((paper, index) => {
    const fullPaper = paperById(paper.paper_id) || paper;
    const evidence = evidenceForIdeaPaper(raw, paper.paper_id).concat(collectEvidenceFromCard(fullPaper, 2)).slice(0, 3);
    nodes.push(node(`paper_${index}`, "paper", paper.title, `${paper.year || ""} · ${paper.venue_or_source || ""}`, 180 + index * 205, 840, {
      confidence: 62 + Math.min(26, evidence.length * 8),
      paperId: paper.paper_id,
      evidence,
      meta: `${paper.year || ""} · ${paper.venue_or_source || ""}`,
    }));
  });
  const edges = [
    edge("idea", "trunk", "claim", 0.95, "核心主张"),
    edge("trunk", "p_target", "root", 0.84, "目标缺口"),
    edge("trunk", "p_gap", "root", 0.76, "未被覆盖"),
    edge("trunk", "p_transfer", "root", raw.is_cross_task_transfer ? 0.84 : 0.66, "迁移窗口"),
    edge("p_target", "f_mode", "cause", 0.8, "具体失败"),
    edge("p_gap", "f_underuse", "cause", 0.78, "直接连接少"),
    edge("p_transfer", "f_root", "cross-cause", 0.74, "共享机制"),
    edge("f_mode", "m_source", "transfer", 0.78, "来源方法"),
    edge("f_root", "m_transfer", "transfer", 0.84, "机制迁移"),
    edge("f_underuse", "m_components", "transfer", 0.72, "组件补位"),
    edge("m_source", "m_transfer", "shared-mechanism", 0.62, "共享机制"),
    edge("m_transfer", "m_components", "shared-mechanism", 0.58, "组件化"),
  ];
  paperPool.forEach((paper, index) => {
    const targetNode = index < 2 ? "p_target" : index < 5 ? "m_source" : "m_transfer";
    edges.push(edge(targetNode, `paper_${index}`, "evidence", 0.62 + Math.min(0.24, (paper.evidence || []).length * 0.07), "论文证据"));
  });
  return { nodes, edges };
}

function computeAncestors(nodes, edges) {
  const result = new Map(nodes.map((item) => [item.id, new Set()]));
  const incoming = new Map(nodes.map((item) => [item.id, []]));
  edges.forEach((item) => incoming.get(item.target)?.push(item.source));
  const visit = (id, seen = new Set()) => {
    for (const parent of incoming.get(id) || []) {
      if (seen.has(parent)) continue;
      seen.add(parent);
      result.get(id)?.add(parent);
      visit(parent, seen);
    }
  };
  nodes.forEach((item) => visit(item.id));
  return result;
}

function computeDescendants(nodes, edges) {
  const result = new Map(nodes.map((item) => [item.id, new Set()]));
  const outgoing = new Map(nodes.map((item) => [item.id, []]));
  edges.forEach((item) => outgoing.get(item.source)?.push(item.target));
  const visit = (id, seen = new Set()) => {
    for (const child of outgoing.get(id) || []) {
      if (seen.has(child)) continue;
      seen.add(child);
      result.get(id)?.add(child);
      visit(child, seen);
    }
  };
  nodes.forEach((item) => visit(item.id));
  return result;
}

function filterRootGraph(graph) {
  let nodes = [...graph.nodes];
  if (state.rootFilter === "main") {
    const keepIds = new Set(["idea", "trunk"]);
    for (const type of ["problem", "failure", "method", "paper"]) {
      nodes.filter((node) => node.type === type).sort((a, b) => b.confidence - a.confidence).slice(0, type === "paper" ? 4 : 2).forEach((node) => keepIds.add(node.id));
    }
    nodes = nodes.filter((node) => keepIds.has(node.id));
  } else if (state.rootFilter === "strong") {
    nodes = nodes.filter((node) => ["idea", "trunk"].includes(node.type) || node.confidence >= 78);
  } else if (state.rootFilter === "branch" && state.focusNodeId) {
    const keep = new Set(["idea", "trunk", state.focusNodeId]);
    for (const id of graph.ancestors.get(state.focusNodeId) || []) keep.add(id);
    for (const id of graph.descendants.get(state.focusNodeId) || []) keep.add(id);
    nodes = nodes.filter((node) => keep.has(node.id));
  }
  const visibleIds = new Set(nodes.map((node) => node.id));
  const edges = graph.edges.filter((item) => visibleIds.has(item.source) && visibleIds.has(item.target));
  return { nodes, edges };
}

function renderRootEdge(item) {
  const source = state.rootGraph.nodeById.get(item.source);
  const target = state.rootGraph.nodeById.get(item.target);
  if (!source || !target) return "";
  const width = 1.2 + item.strength * 4.2;
  const dashed = ["shared-mechanism", "cross-cause"].includes(item.type) ? "dashed" : "";
  return `<path class="root-edge ${item.type} ${dashed}" data-source="${item.source}" data-target="${item.target}" data-label="${escapeHtml(item.label)}" d="${verticalCurve(source, target)}" stroke-width="${width.toFixed(1)}" opacity="${clamp(item.strength, 0.25, 0.95).toFixed(2)}" />`;
}

function renderRootNode(item) {
  const lines = wrapText(item.label, item.type === "paper" ? 24 : 18, item.type === "paper" ? 2 : 3);
  const meta = item.type === "paper" ? shortText(item.meta, 40) : item.confidence >= 86 ? "高置信" : "可探索";
  const evidenceMark = item.evidence?.length ? `<text class="node-evidence" y="${nodeRadius(item) + 18}">${item.evidence.length} 条证据</text>` : "";
  return `
    <g class="root-node ${item.type}" data-node="${item.id}" transform="translate(${item.x},${item.y})">
      <circle class="root-node-halo" r="${nodeRadius(item) + 15}"></circle>
      <circle class="root-node-core" r="${nodeRadius(item)}"></circle>
      <text class="root-node-label" y="${lines.length > 1 ? -8 * lines.length : 4}">
        ${lines.map((line, index) => `<tspan x="0" dy="${index === 0 ? 0 : 15}">${escapeHtml(line)}</tspan>`).join("")}
      </text>
      <text class="root-node-meta" y="${nodeRadius(item) - 12}">${escapeHtml(meta)}</text>
      ${evidenceMark}
    </g>
  `;
}

function nodeRadius(item) {
  const base = {
    idea: 62,
    trunk: 50,
    problem: 47,
    failure: 43,
    method: 45,
    paper: 38,
  }[item.type] || 40;
  return base * (item.size || 1);
}

function bindRootHover() {
  const svg = document.querySelector("#rootSvg");
  const card = document.querySelector("#rootHoverCard");
  if (!svg || !card) return;
  svg.addEventListener("mousemove", (event) => {
    const nodeEl = event.target.closest(".root-node");
    const edgeEl = event.target.closest(".root-edge");
    if (!nodeEl && !edgeEl) {
      clearRootHighlight();
      return;
    }
    if (nodeEl) {
      const nodeData = state.rootGraph.nodeById.get(nodeEl.dataset.node);
      setRootHighlight(nodeData.id);
      card.classList.remove("hidden");
      card.style.left = `${event.clientX + 18}px`;
      card.style.top = `${event.clientY + 18}px`;
      card.innerHTML = `
        <strong>${escapeHtml(nodeData.label)}</strong>
        <p>${escapeHtml(nodeData.detail || nodeData.meta || "")}</p>
        <small>${nodeTypeName(nodeData.type)} · 置信 ${nodeData.confidence}</small>
      `;
    } else if (edgeEl) {
      card.classList.remove("hidden");
      card.style.left = `${event.clientX + 18}px`;
      card.style.top = `${event.clientY + 18}px`;
      card.innerHTML = `<strong>连接原因</strong><p>${escapeHtml(edgeEl.dataset.label || "共享问题、机制或证据。")}</p>`;
    }
  });
  svg.addEventListener("mouseleave", clearRootHighlight);
}

function nodeTypeName(type) {
  return {
    idea: "Idea",
    trunk: "主干",
    problem: "研究缺口",
    failure: "失败模式 / 根因",
    method: "方法 / 迁移机制",
    paper: "论文证据",
  }[type] || type;
}

function setRootHighlight(nodeId) {
  const graph = state.rootGraph;
  const related = new Set([nodeId]);
  for (const id of graph.ancestors.get(nodeId) || []) related.add(id);
  for (const id of graph.descendants.get(nodeId) || []) related.add(id);
  graph.edges.forEach((item) => {
    if (item.source === nodeId || item.target === nodeId) {
      related.add(item.source);
      related.add(item.target);
    }
  });
  document.querySelectorAll(".root-node").forEach((nodeEl) => {
    const active = related.has(nodeEl.dataset.node);
    nodeEl.classList.toggle("active", active);
    nodeEl.classList.toggle("dimmed", !active);
  });
  document.querySelectorAll(".root-edge").forEach((edgeEl) => {
    const active = related.has(edgeEl.dataset.source) && related.has(edgeEl.dataset.target);
    edgeEl.classList.toggle("active", active);
    edgeEl.classList.toggle("dimmed", !active);
  });
}

function clearRootHighlight() {
  const card = document.querySelector("#rootHoverCard");
  if (card) card.classList.add("hidden");
  document.querySelectorAll(".root-node, .root-edge").forEach((item) => {
    item.classList.remove("active", "dimmed");
  });
}

function renderPaperDrawer(paperId) {
  const paper = paperById(paperId);
  if (!paper) return "";
  const graphPaper = state.rootGraph?.nodes?.find((nodeItem) => nodeItem.paperId === paperId);
  const evidence = graphPaper?.evidence?.length ? graphPaper.evidence : collectEvidenceFromCard(paper, 5);
  return `
    <aside class="paper-drawer">
      <button class="drawer-close" type="button" data-close-drawer>关闭</button>
      <span class="eyebrow">论文证据</span>
      <h2>${escapeHtml(paper.title || "Untitled paper")}</h2>
      <p class="paper-meta">${escapeHtml(paper.year || "")} · ${escapeHtml(paper.venue_or_source || paper.venue || "")}</p>
      <section>
        <h3>摘要核心句</h3>
        <p>${escapeHtml(firstSentence(paper.abstract || paper.introduction, 260) || "暂无摘要文本。")}</p>
      </section>
      <section>
        <h3>与当前 Idea 的关联证据</h3>
        ${(evidence || []).slice(0, 4).map((ev) => `
          <blockquote>
            ${escapeHtml(ev.quote)}
            <small>${escapeHtml(ev.section || ev.role || "")}</small>
          </blockquote>
        `).join("") || `<p class="muted">暂无可展示证据句。</p>`}
      </section>
      <section>
        <h3>方法图 / 结果表</h3>
        <div class="asset-grid">
          ${(paper.figures || []).slice(0, 3).map((fig) => renderAsset(fig, "figure")).join("")}
          ${(paper.tables || []).slice(0, 2).map((tab) => renderAsset(tab, "table")).join("")}
          ${!(paper.figures || []).length && !(paper.tables || []).length ? `<p class="muted">这篇论文本地还没有 clean figure/table 资产。</p>` : ""}
        </div>
      </section>
    </aside>
  `;
}

function renderAsset(asset, kind) {
  const src = asset.src || asset.path || asset.url || "";
  if (!src) return "";
  return `
    <figure class="asset-thumb">
      <img src="${escapeHtml(src)}" alt="${escapeHtml(asset.caption || asset.name || kind)}" loading="lazy" />
      <figcaption>${escapeHtml(shortText(asset.caption || asset.name || kind, 120))}</figcaption>
    </figure>
  `;
}

function bindGlobalEvents() {
  document.body.addEventListener("click", (event) => {
    const idea = event.target.closest("[data-idea]")?.dataset.idea;
    const back = event.target.closest("[data-back-forest]");
    const filter = event.target.closest("[data-root-filter]")?.dataset.rootFilter;
    const nodeEl = event.target.closest("[data-node]");
    const resetForest = event.target.closest("[data-reset-forest]");
    const resetRoot = event.target.closest("[data-reset-root]");
    const openFeatured = event.target.closest("[data-open-featured]");
    const closeDrawer = event.target.closest("[data-close-drawer]");
    if (idea) {
      state.selectedIdeaId = idea;
      state.mode = "root";
      state.rootFilter = "all";
      state.focusNodeId = null;
      state.selectedPaperId = null;
      state.rootTransform = defaultRootTransform();
      window.history.replaceState({}, "", `?idea=${encodeURIComponent(idea)}`);
      renderApp();
    } else if (back) {
      state.mode = "forest";
      state.selectedPaperId = null;
      window.history.replaceState({}, "", "./");
      renderApp();
    } else if (filter) {
      if (filter !== "branch") {
        state.rootFilter = filter;
        state.focusNodeId = null;
      }
      renderApp();
    } else if (nodeEl) {
      const nodeId = nodeEl.dataset.node;
      const item = state.rootGraph?.nodeById?.get(nodeId);
      if (!item) return;
      if (item.type === "paper") {
        state.selectedPaperId = item.paperId;
      } else if (item.type !== "idea") {
        state.focusNodeId = nodeId;
        state.rootFilter = "branch";
      }
      renderApp();
    } else if (resetForest) {
      state.forestTransform = { x: 0, y: 0, k: 1 };
      renderApp();
    } else if (resetRoot) {
      state.rootTransform = defaultRootTransform();
      state.rootFilter = "all";
      state.focusNodeId = null;
      renderApp();
    } else if (openFeatured) {
      state.selectedIdeaId = FEATURED_IDEA_ID;
      state.mode = "root";
      state.rootFilter = "all";
      state.focusNodeId = null;
      state.selectedPaperId = null;
      renderApp();
    } else if (closeDrawer) {
      state.selectedPaperId = null;
      renderApp();
    }
  });

  window.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      if (state.selectedPaperId) {
        state.selectedPaperId = null;
        renderApp();
      } else if (state.mode === "root") {
        state.mode = "forest";
        renderApp();
      }
    }
  });
}

async function init() {
  const [
    rawIdeas,
    microProblems,
    adjacentMicroProblems,
    microMethods,
    paperCards,
    paperIndex,
    status,
    quality,
  ] = await Promise.all([
    loadJson(DATA.ideas),
    loadJson(DATA.microProblems),
    loadJson(DATA.adjacentMicroProblems, {}),
    loadJson(DATA.microMethods),
    loadJson(DATA.paperCards),
    loadJson(DATA.paperIndex, { summary: null, papers: {} }),
    loadJson(DATA.status, null),
    loadJson(DATA.quality, null),
  ]);
  state.rawIdeas = rawIdeas;
  state.microProblems = microProblems;
  state.adjacentMicroProblems = adjacentMicroProblems;
  state.microMethods = microMethods;
  state.paperCards = new Map(paperCards.map((paper) => [paper.paper_id, paper]));
  state.paperIndex = paperIndex;
  state.status = status;
  state.quality = quality;
  prepareIdeas();
  const params = new URLSearchParams(window.location.search);
  const requestedIdea = params.get("idea");
  if (requestedIdea && state.ideas.some((idea) => idea.id === requestedIdea)) {
    state.selectedIdeaId = requestedIdea;
    state.mode = "root";
  }
  bindGlobalEvents();
  renderApp();
}

init().catch((error) => {
  document.querySelector("#app").innerHTML = `
    <div class="error-screen">
      <h1>数据加载失败</h1>
      <p>${escapeHtml(error.message)}</p>
    </div>
  `;
  console.error(error);
});
