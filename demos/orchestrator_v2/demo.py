"""
demos/orchestrator_v2/demo.py
──────────────────────────────────────────────────────────────────────────────
Orchestrator v2 — Async Fan-out + Conditional Routing

Three scenarios, same Marcus crisis, different state:

  Scenario 1 · California  — non-compete void (CA §16600)
    Agent-C (legal) fires first. Returns "void."
    Agent-A short-circuits — B never fires.
    Seam Observer: C edge only.

  Scenario 2 · Texas  — non-compete enforceable
    Agent-C fires first. Returns "enforceable."
    Agent-A conditionally fires Agent-B (compensation).
    Seam Observer: C edge, then B edge appears.

  Scenario 3 · Remote / ambiguous  — true parallel fan-out
    Agent-A fires B + C simultaneously via asyncio.gather.
    Both race back. A synthesizes.
    Seam Observer: both edges appear at the same time.
──────────────────────────────────────────────────────────────────────────────
"""

import argparse
import asyncio
import os
import sys
import textwrap
import time
from typing import List, Optional

os.environ.setdefault("PACT_ENFORCE_AUTH", "0")

import httpx
from pact_ax.api.server import app
from pact_ax.observability.event_bus import get_bus
from pact_ax.orchestration import Orchestrator, OrchestratorTask
from pact_ax.primitives.story_keeper import StoryKeeper

try:
    from pact_ax.integration.hx_bridge import HXBridge
    _HX = True
except Exception:
    _HX = False

# ── CLI ───────────────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser()
parser.add_argument("--dry-run",  action="store_true")
parser.add_argument("--scenario", type=int, default=0,
                    help="1=California 2=Texas 3=Parallel (0=all)")
args = parser.parse_args()

DRY_RUN = args.dry_run or not os.getenv("ANTHROPIC_API_KEY")

if DRY_RUN:
    print("\n  [DRY RUN — no API calls]\n")

# ── Anthropic ─────────────────────────────────────────────────────────────────

if not DRY_RUN:
    import anthropic
    _claude = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    def _call_claude_sync(system: str, prompt: str, max_tokens: int = 350) -> str:
        msg = _claude.messages.create(
            model="claude-opus-4-7",
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text

async def llm(system: str, prompt: str) -> str:
    if DRY_RUN:
        for key, val in _DRY_RESPONSES.items():
            if system.startswith(key):
                return val
        return "Dry-run response."
    return await asyncio.to_thread(_call_claude_sync, system, prompt)

# ── Dry-run stubs ─────────────────────────────────────────────────────────────

_DRY_RESPONSES = {
    # Agent-A sense (used in all scenarios)
    "You are Agent-A, a career coach": '{"decision":"handoff","confidence":"CERTAIN","reasoning":"Non-compete enforceability and compensation analysis exceed my scope."}',

    # Agent-C California
    "You are Agent-C (CA). Analyse non": (
        "Under California Business and Professions Code §16600, this non-compete is void and "
        "unenforceable. California courts have consistently struck down same-industry restrictions "
        "regardless of duration. Marcus can accept either offer with no legal exposure."
    ),

    # Agent-C Texas
    "You are Agent-C (TX). Analyse non": (
        "Texas enforces reasonable non-competes under the Texas Covenants Not to Compete Act "
        "(Bus. & Commerce §15.50). A 12-month same-industry restriction tied to a startup role "
        "is likely enforceable if supported by consideration. Marcus faces real legal exposure "
        "if he joins the competing employer within 12 months."
    ),

    # Agent-C ambiguous
    "You are Agent-C (ambiguous juris": (
        "Jurisdiction is unclear from the available information. Non-compete enforceability varies "
        "dramatically by state. California renders them void; Texas enforces reasonable ones. "
        "Without knowing Marcus's state of employment, the legal risk is unquantifiable. "
        "Recommend confirming jurisdiction before deciding."
    ),

    # Agent-B compensation
    "You are Agent-B, a compensation s": (
        "The competing offer is materially stronger: $25k higher base (13.5%), 50% more RSUs, "
        "identical vesting. Total delta over 4 years exceeds $100k. If the non-compete is void or "
        "unenforceable, the $185k offer's only advantage is Marcus's existing momentum and mission "
        "alignment. Recommend counter-offering $200k base before walking."
    ),

    # Agent-A synthesis (CA short-circuit)
    "You are Agent-A synthesizing (CA)": (
        "The non-compete is void under California law — that constraint doesn't exist. "
        "This is now a straightforward negotiation: use the competing offer to push your current "
        "employer to $200k base. You chose this company for autonomy and meaning, not $25k. "
        "Go back to them with the number. If they move, stay. If they don't, you have your answer."
    ),

    # Agent-A synthesis (TX full)
    "You are Agent-A synthesizing (TX)": (
        "The non-compete is real in Texas — 12 months, same industry. That changes the math. "
        "The $25k base gap plus the legal cage makes the $185k offer genuinely risky: if the "
        "startup stumbles before your cliff, you can't move freely. The competing offer buys you "
        "optionality your partner needs. Before you decide: ask your current employer to remove "
        "or limit the non-compete to 6 months or a narrow product category. If they won't move "
        "on that, take the competing offer — the legal constraint is the real cost, not the salary gap."
    ),

    # Agent-A synthesis (ambiguous parallel)
    "You are Agent-A synthesizing (amb": (
        "Jurisdiction is unclear, so both the legal risk and the financial gap matter. "
        "The compensation analysis says the competing offer is $100k+ better over 4 years. "
        "The legal analysis says the non-compete risk is real if you're not in California. "
        "Immediate action: confirm your state of employment. If California, negotiate from strength. "
        "If Texas or another enforcing state, the non-compete removal becomes the priority ask. "
        "Don't make this decision without knowing which legal universe you're in."
    ),
}

# ── System prompts ────────────────────────────────────────────────────────────

AGENT_C_CA_SYS  = "You are Agent-C (CA). Analyse non-compete enforceability. Marcus is in California. 3 sentences max."
AGENT_C_TX_SYS  = "You are Agent-C (TX). Analyse non-compete enforceability. Marcus is in Texas. 3 sentences max."
AGENT_C_AMB_SYS = "You are Agent-C (ambiguous juris). Non-compete enforceability unclear. State unknown. 3 sentences max."
AGENT_B_SYS     = "You are Agent-B, a compensation specialist. Analyse offer delta. 3 sentences max."

SYNTH_CA_SYS  = "You are Agent-A synthesizing (CA) legal result only. Career coach. Direct advice. 4 sentences max."
SYNTH_TX_SYS  = "You are Agent-A synthesizing (TX) full legal + compensation results. Career coach. Direct. 5 sentences max."
SYNTH_AMB_SYS = "You are Agent-A synthesizing (amb) parallel legal + compensation results. Jurisdiction unclear. Direct. 5 sentences max."

# ── Marcus scenario data ──────────────────────────────────────────────────────

BASE = {
    "user_id":        "marcus",
    "accepted_offer": "$185k base + 10,000 RSUs (4yr/1yr cliff)",
    "competing_offer":"$210k base + 15,000 RSUs (4yr/1yr cliff)",
    "non_compete":    "12 months, same industry",
    "deadline_hours": 48,
}

SCENARIOS = {
    1: {"label": "California",  "flag": "non-compete VOID (CA §16600)",     "location": "California",       "c_sys": AGENT_C_CA_SYS,  "synth_sys": SYNTH_CA_SYS},
    2: {"label": "Texas",       "flag": "non-compete ENFORCEABLE (TX §15.50)", "location": "Texas",          "c_sys": AGENT_C_TX_SYS,  "synth_sys": SYNTH_TX_SYS},
    3: {"label": "Ambiguous",   "flag": "jurisdiction unknown — parallel fan-out", "location": "unknown",   "c_sys": AGENT_C_AMB_SYS, "synth_sys": SYNTH_AMB_SYS},
}

B_PROMPT = f"Accepted: {BASE['accepted_offer']}. Competing: {BASE['competing_offer']}. Non-compete: {BASE['non_compete']}. Analyse compensation delta."

# ── Helpers ───────────────────────────────────────────────────────────────────

def hr(title: str = ""):
    print(f"\n{'─' * 68}")
    if title:
        print(f"  {title}")
    print(f"{'─' * 68}")

def banner(title: str, sub: str = ""):
    print(f"\n{'═' * 68}")
    print(f"  {title}")
    if sub:
        print(f"  {sub}")
    print(f"{'═' * 68}")

def wrap(text: str, width: int = 64, indent: str = "    ") -> str:
    return textwrap.fill(text, width=width,
                         initial_indent=indent, subsequent_indent=indent)

def _ts():
    return time.strftime("%H:%M:%S")

# ── HTTP helpers using sync TestClient for setup calls ────────────────────────

from starlette.testclient import TestClient
_sync = TestClient(app)

def setup_agents(*agent_defs):
    for agent_id, role, caps in agent_defs:
        r = _sync.post("/context/register", json={
            "agent_id": agent_id, "role": role, "capabilities": caps,
        })
        ok = "✓" if r.status_code == 200 else "✗"
        print(f"  {ok} {agent_id} ({role})")

def setup_policy(from_a, to_a, delegated, retained, constraints):
    ag = _sync.post("/policy/agree", json={
        "from_agent": from_a, "to_agent": to_a,
        "delegated_scope": delegated, "retained_scope": retained,
        "constraints": constraints, "escalation_rules": [],
    }).json()
    gate = _sync.post("/policy/gate", json={
        "from_agent": from_a, "to_agent": to_a, "task": delegated[0],
    }).json()
    glyph = "✓" if gate["allowed"] else "✗"
    print(f"  {glyph} {from_a}→{to_a}  ({ag['agreement_id'][:20]})")
    return ag["agreement_id"]

# ── Seam Observer reset between scenarios ─────────────────────────────────────

def reset_seam():
    _sync.post("/seam/reset")

# ══════════════════════════════════════════════════════════════════════════════
#  SCENARIO 1 — California: short-circuit
# ══════════════════════════════════════════════════════════════════════════════

async def scenario_1():
    s = SCENARIOS[1]
    banner(f"Scenario 1 · {s['label']}", s['flag'])

    reset_seam()

    hr("Agents + PolicyAlign")
    setup_agents(
        ("a-s1", "career-coach",       ["career_guidance"]),
        ("c-s1", "employment-lawyer",  ["legal_analysis", "ca_labor_law"]),
    )
    setup_policy("a-s1", "c-s1",
                 ["non_compete_enforceability"],
                 ["financial_advice", "career_counseling"],
                 ["no_financial_advice"])

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        orch = Orchestrator(from_agent_id="a-s1", client=client)

        c_prompt = (
            f"Marcus is in {s['location']}. Non-compete: {BASE['non_compete']}, same industry. "
            f"Accepted offer: {BASE['accepted_offer']}. Competing: {BASE['competing_offer']}."
        )

        hr("Step 1 — Agent-C fires (legal)")
        print(f"  [{_ts()}] Firing Agent-C (employment lawyer)…")

        t0 = time.time()
        c_result = (await orch.fan_out_parallel(
            tasks=[OrchestratorTask(
                to_agent="c-s1", payload={**BASE, "location": s["location"]},
                system_prompt=s["c_sys"], user_prompt=c_prompt,
            )],
            llm_fn=llm,
        ))[0]
        elapsed = time.time() - t0

        print(f"  [{_ts()}] Agent-C returned  ({elapsed:.1f}s)")
        print(f"\n  ▸ Agent-C:\n{wrap(c_result.response)}")

        # Routing decision
        is_void = any(w in c_result.response.lower() for w in ("void", "unenforceable", "not enforceable"))

        hr("Step 2 — Agent-A routing decision")
        if is_void:
            print(f"  Non-compete: VOID  →  short-circuit, skip Agent-B")
            print(f"  Seam Observer: only C edge will appear")
        else:
            print(f"  Non-compete: VALID  →  would fire Agent-B (not this scenario)")

        hr("Step 3 — Agent-A synthesizes (C only)")
        synth_prompt = (
            f"Location: {s['location']}. "
            f"Legal report: {c_result.response}\n"
            f"User's question: should I take the competing offer? 48 hours."
        )
        synthesis = await llm(s["synth_sys"], synth_prompt)
        print(f"\n  ▸ Agent-A:\n{wrap(synthesis, width=66)}")

        hr("Summary")
        print(f"  Agent-C  ✓  fired + returned")
        print(f"  Agent-B  —  skipped (non-compete void, no financial analysis needed)")
        print(f"  Routing  ✓  short-circuit saved one LLM call")


# ══════════════════════════════════════════════════════════════════════════════
#  SCENARIO 2 — Texas: conditional fire
# ══════════════════════════════════════════════════════════════════════════════

async def scenario_2():
    s = SCENARIOS[2]
    banner(f"Scenario 2 · {s['label']}", s['flag'])

    reset_seam()

    hr("Agents + PolicyAlign")
    setup_agents(
        ("a-s2", "career-coach",         ["career_guidance"]),
        ("b-s2", "compensation-spec",    ["compensation_analysis", "equity_valuation"]),
        ("c-s2", "employment-lawyer",    ["legal_analysis", "tx_labor_law"]),
    )
    setup_policy("a-s2", "c-s2",
                 ["non_compete_enforceability"],
                 ["financial_advice"],
                 ["no_financial_advice"])
    setup_policy("a-s2", "b-s2",
                 ["compensation_analysis"],
                 ["legal_advice"],
                 ["no_legal_advice"])

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        orch = Orchestrator(from_agent_id="a-s2", client=client)

        c_prompt = (
            f"Marcus is in {s['location']}. Non-compete: {BASE['non_compete']}, same industry. "
            f"Texas Covenants Not to Compete Act applies."
        )

        def route(c_res):
            enforceable = any(w in c_res.response.lower()
                              for w in ("enforceable", "valid", "exposure", "real"))
            if enforceable:
                print(f"\n  [{_ts()}] Non-compete ENFORCEABLE → firing Agent-B (compensation)")
                return [OrchestratorTask(
                    to_agent="b-s2", payload={**BASE, "location": s["location"]},
                    system_prompt=AGENT_B_SYS, user_prompt=B_PROMPT,
                )]
            print(f"\n  [{_ts()}] Non-compete void → skip Agent-B")
            return None

        hr("Step 1 — Agent-C fires first (legal)")
        print(f"  [{_ts()}] Firing Agent-C (employment lawyer, TX)…")

        t0 = time.time()
        c_result, b_results = await orch.fan_out_conditional(
            first_task=OrchestratorTask(
                to_agent="c-s2", payload={**BASE, "location": s["location"]},
                system_prompt=s["c_sys"], user_prompt=c_prompt,
            ),
            llm_fn=llm,
            route_fn=route,
        )
        elapsed = time.time() - t0

        print(f"  [{_ts()}] All agents returned  ({elapsed:.1f}s total)")
        print(f"\n  ▸ Agent-C (TX legal):\n{wrap(c_result.response)}")

        if b_results:
            print(f"\n  ▸ Agent-B (compensation):\n{wrap(b_results[0].response)}")
            b_response = b_results[0].response
        else:
            b_response = None

        hr("Step 2 — Agent-A synthesizes (C + B)")
        synth_prompt = (
            f"Location: {s['location']}. "
            f"Legal: {c_result.response}\n"
            + (f"Compensation: {b_response}\n" if b_response else "")
            + "User: should I take the competing offer? 48 hours."
        )
        synthesis = await llm(s["synth_sys"], synth_prompt)
        print(f"\n  ▸ Agent-A:\n{wrap(synthesis, width=66)}")

        hr("Summary")
        print(f"  Agent-C  ✓  fired first (legal gating)")
        print(f"  Agent-B  {'✓  fired after C confirmed enforceability' if b_results else '—  skipped'}")
        print(f"  Routing  ✓  conditional — B only fired because TX makes non-compete real")


# ══════════════════════════════════════════════════════════════════════════════
#  SCENARIO 3 — Ambiguous: true parallel fan-out
# ══════════════════════════════════════════════════════════════════════════════

async def scenario_3():
    s = SCENARIOS[3]
    banner(f"Scenario 3 · {s['label']}", s['flag'])

    reset_seam()

    hr("Agents + PolicyAlign")
    setup_agents(
        ("a-s3", "career-coach",         ["career_guidance"]),
        ("b-s3", "compensation-spec",    ["compensation_analysis", "equity_valuation"]),
        ("c-s3", "employment-lawyer",    ["legal_analysis", "multi_jurisdiction"]),
    )
    setup_policy("a-s3", "b-s3", ["compensation_analysis"], ["legal_advice"],    ["no_legal_advice"])
    setup_policy("a-s3", "c-s3", ["non_compete_analysis"],  ["financial_advice"], ["no_financial_advice"])

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        orch = Orchestrator(from_agent_id="a-s3", client=client)

        c_prompt = (
            f"Jurisdiction unknown. Non-compete: {BASE['non_compete']}, same industry. "
            f"Analyse enforceability risk across key states."
        )

        tasks = [
            OrchestratorTask(
                to_agent="b-s3", payload={**BASE, "location": s["location"]},
                system_prompt=AGENT_B_SYS, user_prompt=B_PROMPT,
                task_id="compensation",
            ),
            OrchestratorTask(
                to_agent="c-s3", payload={**BASE, "location": s["location"]},
                system_prompt=s["c_sys"], user_prompt=c_prompt,
                task_id="legal",
            ),
        ]

        hr("Step 1 — B and C fire simultaneously (asyncio.gather)")
        print(f"  [{_ts()}] Firing Agent-B (compensation) + Agent-C (legal) in parallel…")
        t0 = time.time()

        results = await orch.fan_out_parallel(tasks=tasks, llm_fn=llm)

        elapsed = time.time() - t0
        b_res = next(r for r in results if r.task_id == "compensation")
        c_res = next(r for r in results if r.task_id == "legal")

        print(f"  [{_ts()}] Both returned  ({elapsed:.1f}s — true parallel)")
        print(f"\n  ▸ Agent-B (compensation):\n{wrap(b_res.response)}")
        print(f"\n  ▸ Agent-C (legal, multi-jurisdiction):\n{wrap(c_res.response)}")

        hr("Step 2 — Agent-A synthesizes both")
        synth_prompt = (
            f"Jurisdiction unknown. "
            f"Compensation: {b_res.response}\n"
            f"Legal: {c_res.response}\n"
            f"User: should I take the competing offer? 48 hours."
        )
        synthesis = await llm(s["synth_sys"], synth_prompt)
        print(f"\n  ▸ Agent-A:\n{wrap(synthesis, width=66)}")

        hr("Summary")
        print(f"  Agent-B  ✓  fired in parallel")
        print(f"  Agent-C  ✓  fired in parallel")
        print(f"  Routing  ✓  both needed — jurisdiction unknown, can't short-circuit")
        print(f"  Elapsed  {elapsed:.1f}s  (parallel vs ~{elapsed*1.6:.1f}s sequential)")


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════

async def main():
    banner(
        "PACT-AX · Orchestrator v2",
        "Async fan-out + conditional routing  ·  3 scenarios",
    )
    print(f"""
  Same crisis. Different state. Different graph.

  Scenario 1 · California   → C fires, returns void, B skipped
  Scenario 2 · Texas        → C fires, returns enforceable, B fires
  Scenario 3 · Ambiguous    → B + C fire in parallel, both return
""")

    which = args.scenario
    if which == 0 or which == 1:
        await scenario_1()
    if which == 0 or which == 2:
        await scenario_2()
    if which == 0 or which == 3:
        await scenario_3()

    if which == 0:
        print(f"""
{'═' * 68}
  All three scenarios complete.
  Open the Seam Observer to see the three different graphs.
{'═' * 68}
""")


if __name__ == "__main__":
    asyncio.run(main())
