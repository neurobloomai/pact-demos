"""
Orchestrate REST Demo
──────────────────────
Demonstrates all three fan-out patterns via the /orchestrate REST endpoints:

  1. Parallel   — three agents analyse concurrently, all results returned
  2. Conditional — legal-check agent gates whether compliance agents fire
  3. Race        — first agent to find a risk wins, others cancelled

Run with pact-ax server on http://localhost:8765 (PACT_ENFORCE_AUTH=0).
Set ANTHROPIC_API_KEY for real LLM calls; stubs gracefully without it.
"""

import json
import os
import sys
import time
import urllib.request

BASE = "http://127.0.0.1:8765"
DRY  = not os.environ.get("ANTHROPIC_API_KEY")


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
    print(f"\n{'═' * 62}")
    print(f"  {text}")
    print('═' * 62)


def show_results(results, winner=None):
    for r in results:
        mark = " 🏆 WINNER" if winner and r.get("task_id") == winner.get("task_id") else ""
        resp = r["response"][:120].replace("\n", " ")
        print(f"  [{r['task_id']}]{mark}")
        print(f"    {resp}...")
    print()


for _ in range(20):
    try:
        get("/health")
        break
    except Exception:
        time.sleep(0.5)

if DRY:
    print("  [stub mode — set ANTHROPIC_API_KEY for real LLM responses]\n")


# ── Scenario 1: Parallel ───────────────────────────────────────────────────────

banner("Scenario 1 — Parallel: three agents analyse an NDA simultaneously")

tasks = [
    {
        "to_agent": "agent-legal",
        "system_prompt": "You are a legal analyst specialising in contract law.",
        "user_prompt": "Identify the top 3 legal risks in this NDA: unlimited liability, "
                       "perpetual confidentiality, automatic renewal with no termination.",
        "task_id": "legal-risk",
        "payload": {}
    },
    {
        "to_agent": "agent-finance",
        "system_prompt": "You are a financial risk analyst.",
        "user_prompt": "What are the financial implications of unlimited liability and "
                       "perpetual confidentiality in an NDA?",
        "task_id": "finance-risk",
        "payload": {}
    },
    {
        "to_agent": "agent-compliance",
        "system_prompt": "You are a compliance officer.",
        "user_prompt": "Does unlimited liability + perpetual confidentiality comply with "
                       "GDPR data retention requirements?",
        "task_id": "compliance-check",
        "payload": {}
    },
]

print("\n  Firing 3 agents simultaneously...")
t0 = time.time()
result = post("/orchestrate/parallel", {
    "from_agent": "orchestrator",
    "tasks": tasks
})
elapsed = time.time() - t0
print(f"  All 3 returned in {elapsed:.1f}s\n")
show_results(result["results"])


# ── Scenario 2: Conditional ────────────────────────────────────────────────────

banner("Scenario 2 — Conditional: legal check gates compliance agents")

print("\n  First task: jurisdiction check for California NDA...")
print("  If result mentions 'enforceable' → fire compliance + IP agents")
print("  If result mentions 'void' → stop (no downstream work needed)\n")

result2 = post("/orchestrate/conditional", {
    "from_agent": "orchestrator",
    "first_task": {
        "to_agent": "agent-jurisdiction",
        "system_prompt": "You are a California employment law expert.",
        "user_prompt": "Is a non-compete clause in a California employment contract "
                       "enforceable? Answer with 'void' or 'enforceable' in your response.",
        "task_id": "jurisdiction-check",
        "payload": {}
    },
    "next_tasks": [
        {
            "to_agent": "agent-compliance",
            "system_prompt": "You are a compliance officer.",
            "user_prompt": "What compliance steps are needed for an enforceable NDA in California?",
            "task_id": "compliance-detail",
            "payload": {}
        },
        {
            "to_agent": "agent-ip",
            "system_prompt": "You are an IP attorney.",
            "user_prompt": "What IP protection clauses should accompany an enforceable NDA?",
            "task_id": "ip-clauses",
            "payload": {}
        }
    ],
    "route_keyword": "enforceable"
})

first = result2["first_result"]
print(f"  Jurisdiction result [{first['task_id']}]:")
print(f"    {first['response'][:150].replace(chr(10), ' ')}...")
print(f"\n  Routed to next tasks: {result2['routed']}")
if result2["routed"]:
    print(f"  Next results:")
    show_results(result2["next_results"])
else:
    print("  → Short-circuited: non-compete is void in CA, no downstream work needed.\n")


# ── Scenario 3: Race ───────────────────────────────────────────────────────────

banner("Scenario 3 — Race: first agent to identify a critical risk wins")

print("\n  Three agents scan different risk domains.")
print("  First to say 'critical' cancels the others.\n")

result3 = post("/orchestrate/race", {
    "from_agent": "orchestrator",
    "tasks": [
        {
            "to_agent": "agent-legal",
            "system_prompt": "You are a legal risk analyst. Be concise.",
            "user_prompt": "Scan this contract term: 'Vendor may share data with any "
                           "third party without notice.' Rate it: critical / moderate / low.",
            "task_id": "legal-scan",
            "payload": {}
        },
        {
            "to_agent": "agent-privacy",
            "system_prompt": "You are a privacy engineer. Be concise.",
            "user_prompt": "Is 'Vendor may share data with any third party without notice' "
                           "a critical privacy violation? Rate: critical / moderate / low.",
            "task_id": "privacy-scan",
            "payload": {}
        },
        {
            "to_agent": "agent-security",
            "system_prompt": "You are a security auditor. Be concise.",
            "user_prompt": "Does 'Vendor may share data with any third party without notice' "
                           "represent a critical security risk? Rate: critical / moderate / low.",
            "task_id": "security-scan",
            "payload": {}
        }
    ],
    "stop_keyword": "critical"
})

winner = result3["winner"]
print(f"  Winner: [{winner['task_id']}]")
print(f"    {winner['response'][:150].replace(chr(10), ' ')}...")
print(f"\n  Completed before cancel: {len(result3['completed_before_cancel'])}")
for r in result3["completed_before_cancel"]:
    print(f"    [{r['task_id']}] {r['response'][:80].replace(chr(10), ' ')}...")

banner("Done — Orchestrate REST complete")
print("  /orchestrate/parallel  → all 3 agents ran concurrently")
print("  /orchestrate/conditional → downstream work gated on first result")
print("  /orchestrate/race      → fastest critical-flag winner cancelled the rest\n")
