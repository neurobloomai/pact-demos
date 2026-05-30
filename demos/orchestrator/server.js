/**
 * Browser demo server for the Orchestrator (fan-out) demo.
 * Usage: ANTHROPIC_API_KEY=sk-ant-... node demos/orchestrator/server.js
 */

const express = require("express");
const { spawn } = require("child_process");
const path = require("path");

const app = express();
const PORT = process.env.PORT || 4001;

app.get("/", (req, res) => res.send(HTML));

app.get("/run", (req, res) => {
  res.setHeader("Content-Type", "text/event-stream");
  res.setHeader("Cache-Control", "no-cache");
  res.setHeader("Connection", "keep-alive");
  res.flushHeaders();

  const env = { ...process.env, PYTHONUNBUFFERED: "1" };
  const child = spawn("python3", [
    path.join(__dirname, "demo.py"),
  ], { env, cwd: path.join(__dirname, "../../..") });

  const send = (data) => res.write(`data: ${JSON.stringify(data)}\n\n`);

  child.stdout.on("data", (c) => send({ type: "line", text: c.toString() }));
  child.stderr.on("data", (c) => send({ type: "err",  text: c.toString() }));
  child.on("close", (code) => { send({ type: "done", code }); res.end(); });
  req.on("close", () => child.kill());
});

app.listen(PORT, () => console.log(`\nOrchestrator Demo → http://localhost:${PORT}\n`));

const HTML = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>PACT-AX · Orchestrator Demo</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #0d1117; color: #e6edf3; font-family: "SF Mono","Fira Code",monospace;
         font-size: 13px; line-height: 1.6; padding: 32px 24px; }
  header { display: flex; align-items: center; gap: 20px; margin-bottom: 28px; flex-wrap: wrap; }
  h1 { font-size: 18px; font-weight: 600; color: #f0f6fc; }
  h1 span { color: #58a6ff; }
  h1 em { color: #d2a8ff; font-style: normal; }
  #run-btn { padding: 8px 20px; background: #238636; color: #fff; border: none;
             border-radius: 6px; font-family: inherit; font-size: 13px; cursor: pointer; }
  #run-btn:hover { background: #2ea043; }
  #run-btn:disabled { background: #21262d; color: #8b949e; cursor: not-allowed; }
  #status { font-size: 12px; color: #8b949e; }
  #status.running { color: #d29922; }
  #status.done { color: #3fb950; }
  #output { background: #161b22; border: 1px solid #30363d; border-radius: 8px;
            padding: 20px 24px; white-space: pre-wrap; max-width: 920px; min-height: 200px;
            overflow-y: auto; }
  .s-header { color: #58a6ff; font-weight: 600; }
  .s-step   { color: #d2a8ff; font-weight: 600; }
  .s-ok     { color: #3fb950; }
  .s-box    { color: #79c0ff; }
  .s-label  { color: #ffa657; }
  .s-err    { color: #f85149; }
</style>
</head>
<body>
<header>
  <h1>PACT-AX · <span>Orchestrator</span> — <em>Fan-out Demo</em></h1>
  <button id="run-btn" onclick="runDemo()">▶ Run Demo</button>
  <span id="status">ready</span>
</header>
<div id="output">Click "Run Demo" to start…</div>
<script>
const out = document.getElementById("output");
const btn = document.getElementById("run-btn");
const status = document.getElementById("status");

function colorize(text) {
  return text
    .replace(/^(═+.+═+)$/gm,  '<span class="s-header">$1</span>')
    .replace(/^(─+.+─+)$/gm,  '<span class="s-step">$1</span>')
    .replace(/(✓)/g,           '<span class="s-ok">$1</span>')
    .replace(/(↑[^\\n]+)/g,    '<span class="s-ok">$1</span>')
    .replace(/^(  [┌└│].+)$/gm,'<span class="s-box">$1</span>')
    .replace(/(  ▸ [A-Z].+)/g, '<span class="s-label">$1</span>');
}

function runDemo() {
  out.innerHTML = "";
  btn.disabled = true;
  status.textContent = "running…";
  status.className = "running";
  const es = new EventSource("/run");
  es.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    if (msg.type === "line") {
      const span = document.createElement("span");
      span.innerHTML = colorize(msg.text);
      out.appendChild(span);
      out.scrollTop = out.scrollHeight;
    } else if (msg.type === "err") {
      const span = document.createElement("span");
      span.className = "s-err";
      span.textContent = msg.text;
      out.appendChild(span);
    } else if (msg.type === "done") {
      es.close();
      btn.disabled = false;
      status.textContent = msg.code === 0 ? "done ✓" : "error (code " + msg.code + ")";
      status.className = msg.code === 0 ? "done" : "s-err";
    }
  };
  es.onerror = () => { es.close(); btn.disabled = false; status.textContent = "connection error"; };
}
</script>
</body>
</html>`;
