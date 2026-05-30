/**
 * Seam Observer — live visual dashboard for PACT-AX agent handoffs.
 *
 * Connects to pact-ax /seam/events SSE stream and renders:
 *   - Agent graph (nodes + edges + trust scores)
 *   - Animated packets flying between agents
 *   - Scrolling event timeline with colour-coded event types
 *
 * Usage:
 *   ANTHROPIC_API_KEY=sk-ant-... node demos/seam_observer/server.js
 *   open http://localhost:4002
 */

const express = require("express");
const { spawn } = require("child_process");
const path = require("path");

const app = express();
const PORT = process.env.PORT || 4002;
const PACT_AX_PORT = process.env.PACT_AX_PORT || 8765;

app.get("/", (req, res) => res.send(HTML));

// Proxy /seam/events from the running pact-ax server to the browser
app.get("/seam/events", (req, res) => {
  const http = require("http");
  const options = { hostname: "127.0.0.1", port: PACT_AX_PORT, path: "/seam/events" };
  http.get(options, (upstream) => {
    res.setHeader("Content-Type", "text/event-stream");
    res.setHeader("Cache-Control", "no-cache");
    res.setHeader("Connection", "keep-alive");
    upstream.pipe(res);
    req.on("close", () => upstream.destroy());
  }).on("error", () => {
    res.status(503).end();
  });
});

// Proxy /seam/reset and /seam/snapshot to pact-ax
function proxyPost(path, req, res) {
  const http = require("http");
  const opts = { hostname: "127.0.0.1", port: PACT_AX_PORT, path, method: "POST",
                 headers: { "Content-Type": "application/json", "Content-Length": 0 } };
  const up = http.request(opts, (r) => {
    let body = "";
    r.on("data", d => body += d);
    r.on("end", () => res.json(JSON.parse(body || "{}")));
  });
  up.on("error", () => res.status(503).end());
  up.end();
}

app.post("/seam/reset",    (req, res) => proxyPost("/seam/reset",    req, res));
app.get("/seam/snapshot",  (req, res) => {
  const http = require("http");
  const opts = { hostname: "127.0.0.1", port: PACT_AX_PORT, path: "/seam/snapshot" };
  http.get(opts, (r) => { let b = ""; r.on("data", d => b += d); r.on("end", () => res.json(JSON.parse(b || "{}"))); })
      .on("error", () => res.status(503).end());
});

// Run a demo and stream its stdout back
app.get("/run/:demo", (req, res) => {
  const demos = {
    orchestrator:        path.join(__dirname, "../orchestrator/demo.py"),
    orchestrator_v2:     path.join(__dirname, "../orchestrator_v2/demo.py"),
    four_primitive:      path.join(__dirname, "../four_primitive/demo.py"),
    capability_routing:  path.join(__dirname, "../capability_routing/demo.py"),
    orchestrate_rest:    path.join(__dirname, "../orchestrate_rest/demo.py"),
  };
  const script = demos[req.params.demo];
  if (!script) return res.status(404).end();

  res.setHeader("Content-Type", "text/event-stream");
  res.setHeader("Cache-Control", "no-cache");
  res.setHeader("Connection", "keep-alive");
  res.flushHeaders();

  const env = { ...process.env, PYTHONUNBUFFERED: "1" };
  const child = spawn(
    "/Users/akanuganti/.pyenv/versions/3.9.13/bin/python",
    [script],
    { env, cwd: path.join(__dirname, "../../..") }
  );

  const send = (d) => res.write(`data: ${JSON.stringify(d)}\n\n`);
  child.stdout.on("data", (c) => send({ type: "line", text: c.toString() }));
  child.stderr.on("data", (c) => send({ type: "err",  text: c.toString() }));
  child.on("close", (code) => { send({ type: "done", code }); res.end(); });
  req.on("close", () => child.kill());
});

// Start pact-ax server in background (in-process via uvicorn subprocess)
function startPactAx() {
  const child = spawn(
    "/Users/akanuganti/.pyenv/versions/3.9.13/bin/python",
    ["-m", "uvicorn", "pact_ax.api.server:app",
     "--host", "127.0.0.1", "--port", String(PACT_AX_PORT), "--log-level", "warning"],
    {
      env: { ...process.env, PACT_ENFORCE_AUTH: "0" },
      cwd: path.join(__dirname, "../../.."),
    }
  );
  child.stderr.on("data", (d) => {
    const msg = d.toString();
    if (msg.includes("Application startup complete")) {
      console.log(`  pact-ax API → http://127.0.0.1:${PACT_AX_PORT}`);
    }
  });
  child.on("close", (code) => {
    if (code !== null) console.error(`pact-ax exited with code ${code}`);
  });
  return child;
}

const pactAx = startPactAx();
process.on("exit",    () => pactAx.kill());
process.on("SIGINT",  () => { pactAx.kill(); process.exit(); });
process.on("SIGTERM", () => { pactAx.kill(); process.exit(); });

app.listen(PORT, () => {
  console.log(`\nPACT-AX Seam Observer → http://localhost:${PORT}`);
  console.log(`  Waiting for pact-ax to start on port ${PACT_AX_PORT}...\n`);
});

// ── HTML ──────────────────────────────────────────────────────────────────────

const HTML = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>PACT-AX · Seam Observer</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg:      #0d1117;
  --surface: #161b22;
  --border:  #30363d;
  --muted:   #8b949e;
  --text:    #e6edf3;
  --blue:    #58a6ff;
  --green:   #3fb950;
  --yellow:  #d29922;
  --purple:  #d2a8ff;
  --orange:  #ffa657;
  --red:     #f85149;
  --font:    "SF Mono","Fira Code","Cascadia Code",monospace;
}

body {
  background: var(--bg);
  color: var(--text);
  font-family: var(--font);
  font-size: 12px;
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* ── Header ── */
header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 20px;
  border-bottom: 1px solid var(--border);
  background: var(--surface);
  flex-shrink: 0;
}

header h1 { font-size: 14px; font-weight: 600; color: var(--text); }
header h1 span { color: var(--blue); }
header h1 em { color: var(--purple); font-style: normal; }

.pill {
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid;
  background: transparent;
  font-family: var(--font);
}
.pill-green  { color: var(--green);  border-color: var(--green);  }
.pill-blue   { color: var(--blue);   border-color: var(--blue);   }
.pill-green:hover { background: rgba(63,185,80,0.12); }
.pill-blue:hover  { background: rgba(88,166,255,0.12); }
.pill:disabled    { opacity: 0.4; cursor: not-allowed; }

#live-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  background: var(--muted);
  transition: background 0.3s;
}
#live-dot.live { background: var(--green); animation: pulse 1.5s infinite; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }

#status-text { color: var(--muted); font-size: 11px; }

.spacer { flex: 1; }

/* ── Main layout ── */
.main {
  display: grid;
  grid-template-columns: 1fr 360px;
  flex: 1;
  min-height: 0;
}

/* ── Graph panel ── */
.graph-panel {
  position: relative;
  background: var(--bg);
  overflow: hidden;
}

#graph-svg {
  width: 100%;
  height: 100%;
}

.node-circle {
  fill: var(--surface);
  stroke: var(--border);
  stroke-width: 2;
  transition: stroke 0.3s, stroke-width 0.3s;
}
.node-circle.active { stroke: var(--blue); stroke-width: 2.5; }

.node-label {
  fill: var(--text);
  font-family: var(--font);
  font-size: 11px;
  font-weight: 600;
  text-anchor: middle;
  dominant-baseline: middle;
}
.node-role {
  fill: var(--muted);
  font-family: var(--font);
  font-size: 9px;
  text-anchor: middle;
}

.edge-line {
  stroke: var(--border);
  stroke-width: 1.5;
  fill: none;
  marker-end: url(#arrowhead);
}
.edge-line.trusted { stroke: var(--green); }
.edge-line.caution { stroke: var(--yellow); }
.edge-line.return  { stroke: var(--purple); stroke-dasharray: 4 3; }

.edge-label {
  fill: var(--muted);
  font-family: var(--font);
  font-size: 9px;
  text-anchor: middle;
}
.edge-label.trusted { fill: var(--green); }
.edge-label.caution { fill: var(--yellow); }

.packet-dot {
  fill: var(--blue);
  pointer-events: none;
}
.packet-dot.return { fill: var(--purple); }

/* empty-state */
.empty-state {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--muted);
  pointer-events: none;
}
.empty-state .icon { font-size: 40px; opacity: 0.3; }
.empty-state p { font-size: 12px; }

/* ── Timeline panel ── */
.timeline-panel {
  border-left: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: var(--surface);
}

.panel-header {
  padding: 10px 14px;
  border-bottom: 1px solid var(--border);
  font-size: 11px;
  font-weight: 600;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}

#stats-row {
  display: flex;
  gap: 16px;
  padding: 8px 14px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.stat { display: flex; flex-direction: column; gap: 1px; }
.stat-val { font-size: 16px; font-weight: 600; color: var(--text); }
.stat-lbl { font-size: 9px; color: var(--muted); text-transform: uppercase; }

#timeline {
  flex: 1;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--border) transparent;
}

.evt {
  padding: 7px 14px;
  border-bottom: 1px solid rgba(48,54,61,0.5);
  display: grid;
  grid-template-columns: 55px 1fr;
  gap: 8px;
  align-items: start;
  border-left: 3px solid transparent;
}
.evt:hover { background: rgba(255,255,255,0.02); }

.evt.packet_prepared, .evt.packet_sent, .evt.packet_received {
  border-left-color: var(--blue);
}
.evt.trust_updated, .evt.trust_read { border-left-color: var(--green); }
.evt.policy_agreed, .evt.policy_gated { border-left-color: var(--purple); }
.evt.agent_registered { border-left-color: var(--orange); }

.evt-time { color: var(--muted); font-size: 10px; padding-top: 1px; }
.evt-body { display: flex; flex-direction: column; gap: 2px; }
.evt-type {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}
.evt-type.packet_prepared,.evt-type.packet_sent,.evt-type.packet_received { color: var(--blue); }
.evt-type.trust_updated,.evt-type.trust_read { color: var(--green); }
.evt-type.policy_agreed,.evt-type.policy_gated { color: var(--purple); }
.evt-type.agent_registered { color: var(--orange); }
.evt-detail { color: var(--muted); font-size: 10px; line-height: 1.4; }

/* ── Log panel (bottom, collapsible) ── */
.log-panel {
  height: 120px;
  border-top: 1px solid var(--border);
  background: var(--bg);
  overflow-y: auto;
  padding: 6px 14px;
  font-size: 11px;
  color: var(--muted);
  scrollbar-width: thin;
  flex-shrink: 0;
}
.log-line { padding: 1px 0; }
.log-line.err { color: var(--red); }
.log-line.done { color: var(--green); }
</style>
</head>
<body>

<header>
  <div id="live-dot"></div>
  <h1>PACT-AX · <span>Seam</span> <em>Observer</em></h1>

  <button class="pill pill-green" id="btn-orch"
          onclick="runDemo('orchestrator')">▶ Orchestrator</button>
  <button class="pill" style="color:#d2a8ff;border-color:#d2a8ff" id="btn-v2"
          onclick="runDemo('orchestrator_v2')">▶ v2 · Async</button>
  <button class="pill pill-blue" id="btn-four"
          onclick="runDemo('four_primitive')">▶ Four-Primitive</button>
  <button class="pill" style="color:#f0883e;border-color:#f0883e" id="btn-cap"
          onclick="runDemo('capability_routing')">▶ Capability Router</button>
  <button class="pill" style="color:#3fb950;border-color:#3fb950" id="btn-orch-rest"
          onclick="runDemo('orchestrate_rest')">▶ Orchestrate REST</button>
  <button class="pill" style="color:var(--muted);border-color:var(--border)"
          onclick="clearAll()">↺ Clear</button>

  <span class="spacer"></span>
  <span id="status-text">connecting…</span>
</header>

<div class="main">

  <!-- Graph panel -->
  <div class="graph-panel" id="graph-panel">
    <div class="empty-state" id="empty-state">
      <div class="icon">⬡</div>
      <p>Run a demo to watch the agent graph appear</p>
    </div>

    <svg id="graph-svg">
      <defs>
        <marker id="arrowhead" markerWidth="8" markerHeight="6"
                refX="7" refY="3" orient="auto">
          <polygon points="0 0, 8 3, 0 6" fill="#30363d" id="arrow-poly"/>
        </marker>
        <marker id="arrowhead-trusted" markerWidth="8" markerHeight="6"
                refX="7" refY="3" orient="auto">
          <polygon points="0 0, 8 3, 0 6" fill="#3fb950"/>
        </marker>
        <marker id="arrowhead-caution" markerWidth="8" markerHeight="6"
                refX="7" refY="3" orient="auto">
          <polygon points="0 0, 8 3, 0 6" fill="#d29922"/>
        </marker>
        <marker id="arrowhead-return" markerWidth="8" markerHeight="6"
                refX="7" refY="3" orient="auto">
          <polygon points="0 0, 8 3, 0 6" fill="#d2a8ff"/>
        </marker>
      </defs>
      <g id="edges-layer"></g>
      <g id="packets-layer"></g>
      <g id="nodes-layer"></g>
    </svg>
  </div>

  <!-- Right panel: stats + timeline -->
  <div class="timeline-panel">
    <div class="panel-header">
      <span>Event Timeline</span>
      <span id="evt-count" style="color:var(--blue)">0</span>
    </div>

    <div id="stats-row">
      <div class="stat">
        <div class="stat-val" id="stat-agents">0</div>
        <div class="stat-lbl">agents</div>
      </div>
      <div class="stat">
        <div class="stat-val" id="stat-packets">0</div>
        <div class="stat-lbl">packets</div>
      </div>
      <div class="stat">
        <div class="stat-val" id="stat-trust">—</div>
        <div class="stat-lbl">avg trust</div>
      </div>
      <div class="stat">
        <div class="stat-val" id="stat-policies">0</div>
        <div class="stat-lbl">agreements</div>
      </div>
    </div>

    <div id="timeline"></div>
  </div>

</div>

<!-- Log panel -->
<div class="log-panel" id="log-panel"></div>

<script>
// ── State ────────────────────────────────────────────────────────────────────

const agents   = {};    // id → { x, y, role }
const edges    = {};    // "a→b" → { trust, packets, el, labelEl }
let   evtCount = 0;
let   pktCount = 0;
let   policyCount = 0;
const trustScores  = {};  // "a→b" → score

// ── Layout ───────────────────────────────────────────────────────────────────

const SVG_W  = () => document.getElementById("graph-panel").clientWidth  || 600;
const SVG_H  = () => document.getElementById("graph-panel").clientHeight || 400;
const RADIUS = 34;

function agentPositions(ids) {
  const n = ids.length;
  if (n === 0) return {};
  const cx = SVG_W() / 2, cy = SVG_H() / 2;
  const r  = Math.min(SVG_W(), SVG_H()) * 0.28;
  const out = {};
  ids.forEach((id, i) => {
    const angle = (2 * Math.PI * i / n) - Math.PI / 2;
    out[id] = { x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle) };
  });
  return out;
}

function reLayout() {
  const ids = Object.keys(agents);
  if (ids.length === 0) return;
  const pos = agentPositions(ids);
  ids.forEach(id => {
    Object.assign(agents[id], pos[id]);
    const g = document.getElementById("node-" + id);
    if (g) {
      g.setAttribute("transform", \`translate(\${agents[id].x},\${agents[id].y})\`);
    }
  });
  Object.keys(edges).forEach(key => redrawEdge(key));
}

// ── SVG helpers ──────────────────────────────────────────────────────────────

const svg       = document.getElementById("graph-svg");
const edgesL    = document.getElementById("edges-layer");
const packetsL  = document.getElementById("packets-layer");
const nodesL    = document.getElementById("nodes-layer");

function ensureAgent(id, role) {
  if (agents[id]) return;
  agents[id] = { role: role || id, x: SVG_W() / 2, y: SVG_H() / 2 };
  const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
  g.id = "node-" + id;
  g.setAttribute("transform", \`translate(\${agents[id].x},\${agents[id].y})\`);

  const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
  circle.setAttribute("r", RADIUS);
  circle.setAttribute("class", "node-circle");
  g.appendChild(circle);

  const shortId = id.split("-").slice(0, 2).join("-");
  const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
  label.setAttribute("class", "node-label");
  label.setAttribute("y", "-6");
  label.textContent = shortId;
  g.appendChild(label);

  const roleLabel = document.createElementNS("http://www.w3.org/2000/svg", "text");
  roleLabel.setAttribute("class", "node-role");
  roleLabel.setAttribute("y", "10");
  roleLabel.textContent = role || "";
  g.appendChild(roleLabel);

  nodesL.appendChild(g);
  reLayout();
  document.getElementById("empty-state").style.display = "none";
}

function edgeClass(trust) {
  if (trust === undefined) return "";
  return trust >= 0.6 ? "trusted" : "caution";
}

function markerFor(trust, isReturn) {
  if (isReturn) return "url(#arrowhead-return)";
  if (trust === undefined) return "url(#arrowhead)";
  return trust >= 0.6 ? "url(#arrowhead-trusted)" : "url(#arrowhead-caution)";
}

function edgePath(ax, ay, bx, by, offset) {
  // offset fan edges to avoid overlap on same node pair
  if (offset) {
    const mx = (ax + bx) / 2, my = (ay + by) / 2;
    const dx = bx - ax, dy = by - ay, len = Math.sqrt(dx*dx+dy*dy) || 1;
    const cx = mx - dy / len * offset * 30;
    const cy = my + dx / len * offset * 30;
    return \`M \${ax} \${ay} Q \${cx} \${cy} \${bx} \${by}\`;
  }
  return \`M \${ax} \${ay} L \${bx} \${by}\`;
}

function nodeEdgePoint(ax, ay, bx, by, r) {
  const dx = bx - ax, dy = by - ay;
  const len = Math.sqrt(dx * dx + dy * dy) || 1;
  return [ax + dx / len * r, ay + dy / len * r];
}

function redrawEdge(key) {
  const e    = edges[key];
  const a    = agents[e.from];
  const b    = agents[e.to];
  if (!a || !b) return;

  const [x1, y1] = nodeEdgePoint(a.x, a.y, b.x, b.y, RADIUS + 2);
  const [x2, y2] = nodeEdgePoint(b.x, b.y, a.x, a.y, RADIUS + 8);

  const isReturn = key.endsWith("_ret");
  const trust    = trustScores[key] || trustScores[e.from + "→" + e.to];
  const cls      = "edge-line " + edgeClass(trust) + (isReturn ? " return" : "");

  if (!e.el) {
    e.el = document.createElementNS("http://www.w3.org/2000/svg", "path");
    e.labelEl = document.createElementNS("http://www.w3.org/2000/svg", "text");
    e.labelEl.setAttribute("class", "edge-label");
    edgesL.appendChild(e.el);
    edgesL.appendChild(e.labelEl);
  }

  const path = edgePath(x1, y1, x2, y2, isReturn ? 1 : 0);
  e.el.setAttribute("d", path);
  e.el.setAttribute("class", cls);
  e.el.setAttribute("marker-end", markerFor(trust, isReturn));

  const mx = (x1 + x2) / 2, my = (y1 + y2) / 2;
  e.labelEl.setAttribute("x", mx);
  e.labelEl.setAttribute("y", my - 6);
  e.labelEl.setAttribute("class", "edge-label " + edgeClass(trust));
  e.labelEl.textContent = trust !== undefined ? trust.toFixed(2) : "";
}

function ensureEdge(from, to, isReturn) {
  const key = from + "→" + to + (isReturn ? "_ret" : "");
  if (!edges[key]) {
    edges[key] = { from, to };
  }
  return key;
}

// packet animation
function animatePacket(from, to, isReturn) {
  const a = agents[from], b = agents[to];
  if (!a || !b) return;

  const [x1, y1] = nodeEdgePoint(a.x, a.y, b.x, b.y, RADIUS + 2);
  const [x2, y2] = nodeEdgePoint(b.x, b.y, a.x, a.y, RADIUS + 8);

  const dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
  dot.setAttribute("r", 5);
  dot.setAttribute("class", "packet-dot" + (isReturn ? " return" : ""));
  packetsL.appendChild(dot);

  const dur = 700;
  const start = performance.now();

  function step(now) {
    const t = Math.min((now - start) / dur, 1);
    const ease = t < 0.5 ? 2*t*t : -1+(4-2*t)*t;
    const x = x1 + (x2 - x1) * ease;
    const y = y1 + (y2 - y1) * ease;
    dot.setAttribute("cx", x);
    dot.setAttribute("cy", y);
    dot.setAttribute("opacity", t < 0.9 ? 1 : (1 - t) / 0.1);
    if (t < 1) requestAnimationFrame(step);
    else dot.remove();
  }
  requestAnimationFrame(step);

  // pulse destination node
  setTimeout(() => {
    const g = document.getElementById("node-" + to);
    if (g) {
      const c = g.querySelector(".node-circle");
      if (c) {
        c.classList.add("active");
        setTimeout(() => c.classList.remove("active"), 600);
      }
    }
  }, dur);
}

// ── Timeline ─────────────────────────────────────────────────────────────────

const TYPE_LABELS = {
  packet_prepared:  "packet →",
  packet_sent:      "packet ✈",
  packet_received:  "packet ✓",
  trust_updated:    "trust ↑",
  trust_read:       "trust",
  policy_agreed:    "policy ✓",
  policy_gated:     "gate",
  agent_registered: "registered",
};

function detail(et, d) {
  switch(et) {
    case "agent_registered":  return \`\${d.agent_id} · \${d.role}\`;
    case "packet_prepared":   return \`\${d.from_agent} → \${d.to_agent} · \${d.packet_id?.slice(0,14)}\`;
    case "packet_sent":       return \`\${d.from_agent} → \${d.to_agent}\`;
    case "packet_received":   return \`\${d.from_agent} → \${d.to_agent} · \${d.success ? "✓" : "✗"}\`;
    case "trust_updated":     return \`\${d.from_agent} → \${d.to_agent} · \${d.new_score?.toFixed(3)}\`;
    case "trust_read":        return \`\${d.from_agent} → \${d.to_agent} · \${d.score?.toFixed(3)}\`;
    case "policy_agreed":     return \`\${d.from_agent} → \${d.to_agent} · \${d.agreement_id?.slice(0,16)}\`;
    case "policy_gated":      return \`\${d.from_agent} → \${d.to_agent} · \${d.allowed ? "allowed" : "blocked"}\`;
    default: return JSON.stringify(d).slice(0, 60);
  }
}

function pushEvent(et, data, ts) {
  const tl = document.getElementById("timeline");
  const now = ts ? new Date(ts * 1000) : new Date();
  const time = now.toTimeString().slice(0, 8);

  const row = document.createElement("div");
  row.className = "evt " + et;
  row.innerHTML = \`
    <div class="evt-time">\${time}</div>
    <div class="evt-body">
      <div class="evt-type \${et}">\${TYPE_LABELS[et] || et}</div>
      <div class="evt-detail">\${detail(et, data)}</div>
    </div>\`;
  tl.appendChild(row);
  tl.scrollTop = tl.scrollHeight;

  evtCount++;
  document.getElementById("evt-count").textContent = evtCount;
}

// ── Stats ─────────────────────────────────────────────────────────────────────

function updateStats() {
  document.getElementById("stat-agents").textContent  = Object.keys(agents).length;
  document.getElementById("stat-packets").textContent = pktCount;
  document.getElementById("stat-policies").textContent = policyCount;
  const scores = Object.values(trustScores);
  if (scores.length) {
    const avg = scores.reduce((a, b) => a + b, 0) / scores.length;
    document.getElementById("stat-trust").textContent = avg.toFixed(2);
  }
}

// ── Event handling ────────────────────────────────────────────────────────────

function handleEvent(et, data) {
  if (et === "agent_registered") {
    ensureAgent(data.agent_id, data.role);
    updateStats();
  }

  if (et === "packet_prepared") {
    ensureAgent(data.from_agent);
    ensureAgent(data.to_agent);
    const key = ensureEdge(data.from_agent, data.to_agent, false);
    redrawEdge(key);
  }

  if (et === "packet_sent") {
    animatePacket(data.from_agent, data.to_agent, false);
  }

  if (et === "packet_received" && data.success) {
    pktCount++;
    // if to_agent is orchestrator (already registered as from), this is a return
    const isReturn = data.to_agent in agents && !(data.from_agent + "→" + data.to_agent in edges);
    if (isReturn) {
      const key = ensureEdge(data.from_agent, data.to_agent, true);
      redrawEdge(key);
    }
    updateStats();
  }

  if (et === "trust_updated" || et === "trust_read") {
    const key   = data.from_agent + "→" + data.to_agent;
    const score = data.new_score ?? data.score;
    if (score !== undefined) {
      trustScores[key] = score;
      const edgeKey = key in edges ? key : null;
      if (edgeKey) redrawEdge(edgeKey);
      updateStats();
    }
  }

  if (et === "policy_agreed") {
    policyCount++;
    updateStats();
  }

  pushEvent(et, data);
}

function applySnapshot(snapshot) {
  Object.entries(snapshot.agents || {}).forEach(([id, info]) => {
    ensureAgent(id, info.role);
  });
  Object.entries(snapshot.edges || {}).forEach(([key, e]) => {
    if (e.trust !== undefined) trustScores[key] = e.trust;
    const edgeKey = ensureEdge(e.from, e.to, false);
    redrawEdge(edgeKey);
  });
  updateStats();
}

// ── SSE connection ────────────────────────────────────────────────────────────

let es = null;

function connectSSE() {
  if (es) es.close();
  es = new EventSource("/seam/events");
  const dot  = document.getElementById("live-dot");
  const text = document.getElementById("status-text");

  es.onopen = () => {
    dot.className  = "live";
    text.textContent = "live";
  };
  es.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    if (msg.type === "snapshot") {
      applySnapshot(msg.payload);
    } else if (msg.type === "event") {
      handleEvent(msg.payload.event_type, msg.payload.data);
    }
  };
  es.onerror = () => {
    dot.className  = "";
    text.textContent = "reconnecting…";
    setTimeout(connectSSE, 2000);
  };
}

// ── Demo runner ───────────────────────────────────────────────────────────────

function runDemo(name) {
  const btnMap = { orchestrator: "btn-orch", orchestrator_v2: "btn-v2", four_primitive: "btn-four", capability_routing: "btn-cap", orchestrate_rest: "btn-orch-rest" };
  const btn = document.getElementById(btnMap[name] || "btn-orch");
  btn.disabled = true;
  document.getElementById("status-text").textContent = "running " + name + "…";

  // reset the bus first
  fetch("/seam/reset", { method: "POST" });

  const log = document.getElementById("log-panel");
  log.innerHTML = "";

  const ev = new EventSource("/run/" + name);
  ev.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    if (msg.type === "line" || msg.type === "err") {
      const d = document.createElement("div");
      d.className = "log-line" + (msg.type === "err" ? " err" : "");
      d.textContent = msg.text.replace(/\\n$/, "");
      log.appendChild(d);
      log.scrollTop = log.scrollHeight;
    } else if (msg.type === "done") {
      ev.close();
      btn.disabled = false;
      const d = document.createElement("div");
      d.className = "log-line done";
      d.textContent = "── done (exit " + msg.code + ") ──";
      log.appendChild(d);
      document.getElementById("status-text").textContent = "done ✓";
    }
  };
  ev.onerror = () => {
    ev.close();
    btn.disabled = false;
  };
}

function clearAll() {
  // Clear graph
  nodesL.innerHTML = "";
  edgesL.innerHTML = "";
  packetsL.innerHTML = "";
  Object.keys(agents).forEach(k => delete agents[k]);
  Object.keys(edges).forEach(k => delete edges[k]);
  Object.keys(trustScores).forEach(k => delete trustScores[k]);
  evtCount = 0; pktCount = 0; policyCount = 0;
  document.getElementById("timeline").innerHTML = "";
  document.getElementById("log-panel").innerHTML = "";
  document.getElementById("evt-count").textContent = "0";
  document.getElementById("empty-state").style.display = "";
  updateStats();
  fetch("/seam/reset", { method: "POST" });
}

// ── Resize handler ────────────────────────────────────────────────────────────

window.addEventListener("resize", () => reLayout());

// Also need to proxy /seam/reset to pact-ax
// Done via the /run endpoint — let's add a reset proxy

// ── Boot ──────────────────────────────────────────────────────────────────────

connectSSE();
</script>
</body>
</html>`;
