"""
Capability Routing Demo
────────────────────────
Shows trust-weighted capability discovery:

  1. Register agents with skills
  2. Build trust history between them
  3. Route a task — same skill, different trust scores → best agent wins
  4. Fuzzy search across capabilities
  5. Raise trust for agent-b — routing decision flips

Run with pact-ax server on http://localhost:8765 (PACT_ENFORCE_AUTH=0).
"""

import json
import sys
import time
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8765"

# ── helpers ────────────────────────────────────────────────────────────────────

def post(path, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        BASE + path, data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def get(path):
    with urllib.request.urlopen(BASE + path) as resp:
        return json.loads(resp.read())


def banner(text):
    print(f"\n{'─' * 60}")
    print(f"  {text}")
    print('─' * 60)


def show(label, data):
    print(f"\n{label}")
    print(json.dumps(data, indent=2))


# ── wait for server ────────────────────────────────────────────────────────────

for _ in range(20):
    try:
        get("/health")
        break
    except Exception:
        time.sleep(0.5)

# ── Step 1: Register capabilities ─────────────────────────────────────────────

banner("Step 1 — Register agent capabilities")

for agent, skill, desc, tags in [
    ("agent-alpha", "contract_review",  "Expert NDA and IP review",              ["legal", "contracts"]),
    ("agent-beta",  "contract_review",  "Specialises in service agreements",      ["legal"]),
    ("agent-gamma", "contract_review",  "General contract analysis",              ["legal"]),
    ("agent-beta",  "tax_analysis",     "Federal + state tax implications",       ["legal", "finance"]),
    ("agent-delta", "tax_analysis",     "International tax jurisdiction expert",  ["finance", "global"]),
    ("agent-alpha", "ip_licensing",     "Patent and copyright licensing",         ["legal", "ip"]),
]:
    r = post("/capabilities/register", {
        "agent_id": agent, "skill": skill,
        "description": desc, "tags": tags
    })
    print(f"  ✓ {agent} → {skill}")

skills = get("/capabilities/skills")
print(f"\n  Registered skills: {skills['skills']}")

# ── Step 2: Build trust history ────────────────────────────────────────────────

banner("Step 2 — Build trust between orchestrator → agents")

trust_updates = [
    ("orchestrator", "agent-alpha", "positive", 0.9),
    ("orchestrator", "agent-alpha", "positive", 1.0),
    ("orchestrator", "agent-beta",  "positive", 0.7),
    ("orchestrator", "agent-gamma", "negative", 0.8),
]

for from_a, target, outcome, impact in trust_updates:
    post("/trust/{}/update".format(from_a), {
        "target_id": target, "outcome": outcome,
        "context_type": "task_knowledge", "impact": impact
    })
    print(f"  {from_a} → {target}: {outcome} (impact={impact})")

# Show trust scores
for target in ["agent-alpha", "agent-beta", "agent-gamma"]:
    t = get(f"/trust/orchestrator/{target}")
    print(f"  Trust[orchestrator→{target}] = {t['trust_score']:.3f}")

# ── Step 3: Route a task — trust-weighted ─────────────────────────────────────

banner("Step 3 — Route contract_review task (trust-weighted)")

decision = post("/route", {
    "from_agent": "orchestrator",
    "skill": "contract_review",
    "min_trust": 0.4,
    "top_k": 3
})
show("Route decision:", {
    "best_agent":    decision["best_agent"],
    "strategy":      decision["strategy_used"],
    "total_capable": decision["total_capable"],
    "candidates": [
        {"agent": c["agent_id"], "trust": c["trust_score"]}
        for c in decision["candidates"]
    ]
})

# ── Step 4: Fuzzy search ────────────────────────────────────────────────────────

banner("Step 4 — Fuzzy search: 'finance'")

search = post("/capabilities/search", {"query": "finance"})
print(f"\n  Results for 'finance':")
for r in search["results"]:
    print(f"    {r['agent_id']} → {r['skill']} ({', '.join(r['tags'])})")

# ── Step 5: Fuzzy route ────────────────────────────────────────────────────────

banner("Step 5 — Fuzzy route: 'tax implications' (finds tax_analysis skill)")

any_route = post("/route/any", {
    "from_agent": "orchestrator",
    "query": "tax implications",
    "min_trust": 0.0,
    "top_k": 3
})
show("Fuzzy route:", {
    "best_agent":  any_route["best_agent"],
    "strategy":    any_route["strategy_used"],
    "candidates": [
        {"agent": c["agent_id"], "skill": c["skill"], "trust": c["trust_score"]}
        for c in any_route["candidates"]
    ]
})

# ── Step 6: Raise trust for agent-beta — routing should flip ───────────────────

banner("Step 6 — Boost agent-beta trust × 2 → routing decision flips")

for _ in range(3):
    post("/trust/orchestrator/update", {
        "target_id": "agent-beta", "outcome": "positive",
        "context_type": "task_knowledge", "impact": 1.0
    })

decision2 = post("/route", {
    "from_agent": "orchestrator",
    "skill": "contract_review",
    "min_trust": 0.4,
    "top_k": 3
})
print(f"\n  New best agent: {decision2['best_agent']}")
print(f"  Updated candidates:")
for c in decision2["candidates"]:
    marker = " ◀ winner" if c["agent_id"] == decision2["best_agent"] else ""
    print(f"    {c['agent_id']}: trust={c['trust_score']:.3f}{marker}")

banner("Done — capability routing complete")
print("  Trust-weighted routing directs tasks to the most trusted capable agent.")
print("  As agents earn (or lose) trust, routing decisions adapt automatically.\n")
