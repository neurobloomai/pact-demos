"""
demos/orchestrator/demo.py
──────────────────────────────────────────────────────────────────────────────
Orchestrator Demo — PACT-AX fan-out + return packet

Scenario
────────
Marcus is in California. Non-compete is unenforceable there.
Agent-A (career-coach) hits its limit and fans out to TWO specialists in parallel:

  Agent-B  — compensation specialist   (offer delta, equity, negotiation)
  Agent-C  — employment lawyer         (non-compete enforceability in CA)

Both return results to Agent-A.
Agent-A synthesizes: sees the CA angle changes everything, gives Marcus the real answer.

The difference:
  Without Orchestrator  →  Marcus gets two disconnected specialist answers
  With Orchestrator     →  Agent-A combines B+C and spots the CA insight
──────────────────────────────────────────────────────────────────────────────
"""

import argparse
import os
import sys
import textwrap
from typing import Any, Dict, List

os.environ.setdefault("PACT_ENFORCE_AUTH", "0")

from starlette.testclient import TestClient
from pact_ax.api.server import app
from pact_ax.primitives.story_keeper import StoryKeeper

try:
    from pact_ax.integration.hx_bridge import HXBridge
    _HX_AVAILABLE = True
except Exception:
    _HX_AVAILABLE = False

# ── CLI ───────────────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser()
parser.add_argument("--dry-run", action="store_true")
args = parser.parse_args()
DRY_RUN = args.dry_run or not os.getenv("ANTHROPIC_API_KEY")

if DRY_RUN:
    print("\n  [DRY RUN — no API calls]\n")

# ── Anthropic client ──────────────────────────────────────────────────────────

if not DRY_RUN:
    import anthropic
    _claude = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    def call_claude(system: str, user: str, max_tokens: int = 400) -> str:
        msg = _claude.messages.create(
            model="claude-opus-4-7",
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return msg.content[0].text

# ── Dry-run stubs ─────────────────────────────────────────────────────────────

DRY_AGENT_A_SENSE = {
    "decision": "handoff",
    "confidence": "CERTAIN",
    "reasoning": (
        "Non-compete enforceability and equity analysis both exceed my scope. "
        "Fanning out to compensation specialist and employment lawyer in parallel."
    ),
}

DRY_B_RESPONSE = textwrap.dedent("""\
    The competing offer is materially stronger: $25k higher base, 5,000 additional RSUs.
    At current stage valuations the equity delta is $50–100k. Non-compete scope is identical
    across both offers. Recommend negotiating base on the accepted offer before the 48-hour
    window closes, or accepting the competing offer outright.\
""")

DRY_C_RESPONSE = textwrap.dedent("""\
    California Business and Professions Code §16600 renders non-compete agreements
    unenforceable as a matter of public policy, with narrow exceptions that do not apply
    here. Marcus is a California resident employed by a California company. The 12-month
    non-compete clause in the accepted offer is void and unenforceable. He can accept
    either offer and move freely within his industry without legal exposure.\
""")

DRY_SYNTHESIS = textwrap.dedent("""\
    Marcus — the legal picture changes everything here, and I want to lead with that.
    The non-compete in your accepted offer is void under California law. It cannot be
    enforced. The constraint you've been worried about — being locked out of your industry
    for 12 months — doesn't exist. That removes the only meaningful risk from the lower
    offer. Now the decision is purely financial and cultural: the competing offer pays
    $25k more and includes 5,000 additional RSUs, but you chose the first company for
    autonomy and meaning. With the non-compete off the table, you're free to negotiate
    from strength: go back to the $185k company, tell them you have a competing offer,
    and ask for $200k base. They want you. The legal risk your partner feared isn't real
    in California. This is now a negotiation, not a forced choice.\
""")

# ── Helpers ───────────────────────────────────────────────────────────────────

client = TestClient(app)

def hr(title: str = ""):
    w = 68
    print(f"\n{'─' * w}")
    if title:
        print(f"  {title}")
    print(f"{'─' * w}")

def banner(title: str, subtitle: str = ""):
    w = 68
    print(f"\n{'═' * w}")
    print(f"  {title}")
    if subtitle:
        print(f"  {subtitle}")
    print(f"{'═' * w}")

def wrap(text: str, width: int = 62, indent: str = "    ") -> str:
    return textwrap.fill(text, width=width, initial_indent=indent,
                         subsequent_indent=indent)

def box(title: str, lines: List[str], extras: List[tuple] = None) -> str:
    w = 65
    border = "─" * w
    rows = [f"  ┌─ {title} {'─' * max(0, w - len(title) - 5)}┐"]
    for line in lines:
        rows.append(f"  │  {line:<{w - 2}}│")
    if extras:
        for label, content in extras:
            rows.append(f"  │  {'─' * (w - 2)}│")
            if label:
                rows.append(f"  │  {label:<{w - 2}}│")
            for cl in textwrap.wrap(content, width=w - 4):
                rows.append(f"  │  {cl:<{w - 2}}│")
    rows.append(f"  └{'─' * (w + 1)}┘")
    return "\n".join(rows)

# ── Marcus's story ────────────────────────────────────────────────────────────

INTERACTIONS = [
    ("marcus", "I just quit my stable job to join a Series B startup as head of engineering. "
               "My partner thinks I'm crazy but I believe in the mission."),
    ("marcus", "Three weeks in — it's harder than I expected but I still feel it was right. "
               "The autonomy here is unlike anything I've had before."),
    ("marcus", "Two months in. We closed a new round. I feel like I made the right call. "
               "My partner is coming around too."),
    ("marcus", "I just got a competing offer from a much bigger company — $210k base vs my "
               "current $185k, more RSUs, but there's a 12-month non-compete if I leave my "
               "current role. I'm in California. I have 48 hours to decide."),
]

SCENARIO = {
    "user_id":          "marcus",
    "location":         "California",
    "accepted_offer":   "$185k base + 10,000 RSUs (4yr/1yr cliff)",
    "competing_offer":  "$210k base + 15,000 RSUs (4yr/1yr cliff)",
    "non_compete":      "12 months, same industry",
    "deadline_hours":   48,
}

# ── AGENT SYSTEM PROMPTS ──────────────────────────────────────────────────────

AGENT_A_SENSE_SYSTEM = """\
You are Agent-A, a career coach AI. Evaluate whether to handle this situation yourself
or fan out to specialists. Output JSON with keys:
  decision (handle|handoff), confidence (CERTAIN|CONFIDENT|MODERATE|LOW),
  reasoning (one sentence)
Non-compete enforceability and equity analysis are outside your scope."""

AGENT_B_SYSTEM = """\
You are Agent-B, a compensation specialist. Analyse the offer delta concisely.
Focus on: base salary gap, RSU difference, vesting parity, negotiation options.
3-4 sentences max. Do not comment on legal matters."""

AGENT_C_SYSTEM = """\
You are Agent-C, an employment lawyer specialising in California labour law.
Analyse the enforceability of the non-compete clause. Be specific about CA Business
and Professions Code §16600. 3-4 sentences max."""

AGENT_A_SYNTHESIS_SYSTEM = """\
You are Agent-A, a career coach. You have just received parallel reports from:
  - Agent-B (compensation specialist)
  - Agent-C (employment lawyer, California)
You also have 3 months of this user's story and identity context.
Synthesise everything into one coherent answer for Marcus. Be direct.
Lead with the most important insight. 5-8 sentences."""


# ═════════════════════════════════════════════════════════════════════════════
#  DEMO
# ═════════════════════════════════════════════════════════════════════════════

def run():
    banner(
        "PACT-AX · Orchestrator Demo",
        "Fan-out: Agent-A → (Agent-B ∥ Agent-C) → Agent-A",
    )
    print(f"\n  User:     Marcus — career pivot, 3 months in")
    print(f"  Location: California  (non-compete void under CA §16600)")
    print(f"  Crisis:   Competing offer + 48-hour deadline\n")

    # ── Step 1: Build Marcus's story ─────────────────────────────────────────
    hr("Step 1 · StoryKeeper — 3 months of narrative")

    hx_bridge = None
    if _HX_AVAILABLE:
        try:
            hx_bridge = HXBridge.for_agent("marcus-orch")
        except Exception:
            hx_bridge = None

    story = StoryKeeper(
        agent_id="agent-a-orch",
        hx_bridge=hx_bridge,
    )
    for _, msg in INTERACTIONS:
        story.process_interaction(
            user_input=msg,
            agent_response="Understood. I'm tracking your journey.",
        )

    state    = story.get_story_state()
    n_inter  = len(story.interactions)
    arc_name = state['arc'].split(":")[0] if ":" in str(state['arc']) else str(state['arc'])
    themes   = state.get('themes', set())
    print(f"  Arc:          {arc_name}")
    print(f"  Interactions: {n_inter}  (3 months + today's crisis)")
    print(f"  Themes:       {', '.join(list(themes)[:8])}")

    # ── Step 2: Register agents ───────────────────────────────────────────────
    hr("Step 2 · ContextShare — register agents")

    for agent_id, role, caps in [
        ("agent-a-orch", "career-coach",           ["career_guidance", "narrative_continuity"]),
        ("agent-b-orch", "compensation-specialist", ["compensation_analysis", "equity_valuation"]),
        ("agent-c-orch", "employment-lawyer",       ["legal_analysis", "non_compete_review", "california_labor_law"]),
    ]:
        r = client.post("/context/register", json={
            "agent_id":     agent_id,
            "role":         role,
            "capabilities": caps,
        })
        print(f"  {'✓' if r.status_code == 200 else '✗'} {agent_id} ({role})")

    # ── Step 3: Agent-A senses its limit ──────────────────────────────────────
    hr("Step 3 · Agent-A — capability sensing")

    user_prompt = (
        f"I have a competing offer. Location: {SCENARIO['location']}. "
        f"Accepted: {SCENARIO['accepted_offer']}. "
        f"Competing: {SCENARIO['competing_offer']}. "
        f"Non-compete: {SCENARIO['non_compete']}. "
        f"Deadline: {SCENARIO['deadline_hours']} hours. What should I do?"
    )

    if DRY_RUN:
        sense = DRY_AGENT_A_SENSE
    else:
        import json as _json
        raw = call_claude(AGENT_A_SENSE_SYSTEM, user_prompt, max_tokens=200)
        try:
            sense = _json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
        except Exception:
            sense = DRY_AGENT_A_SENSE

    print(f"  Decision:   {sense['decision']}")
    print(f"  Confidence: {sense['confidence']}")
    print(f"  Reasoning:  {sense['reasoning']}")

    # ── Step 4: PolicyAlign — negotiate per-agent scopes ─────────────────────
    hr("Step 4 · PolicyAlign — negotiate scope per specialist")

    agree_b = client.post("/policy/agree", json={
        "from_agent":       "agent-a-orch",
        "to_agent":         "agent-b-orch",
        "delegated_scope":  ["compensation_analysis", "equity_valuation", "negotiation_strategy"],
        "retained_scope":   ["emotional_support", "career_counseling", "legal_advice"],
        "constraints":      ["no_legal_advice"],
        "escalation_rules": ["if equity value unclear → flag to agent-a"],
    }).json()

    agree_c = client.post("/policy/agree", json={
        "from_agent":       "agent-a-orch",
        "to_agent":         "agent-c-orch",
        "delegated_scope":  ["non_compete_enforceability", "california_labor_law"],
        "retained_scope":   ["financial_advice", "career_counseling"],
        "constraints":      ["no_financial_advice"],
        "escalation_rules": ["if jurisdiction unclear → flag to agent-a"],
    }).json()

    print(f"  Agreement B ({agree_b['agreement_id']}): compensation + equity")
    print(f"  Agreement C ({agree_c['agreement_id']}): non-compete + CA law")

    # gate checks
    gate_b = client.post("/policy/gate", json={
        "from_agent": "agent-a-orch",
        "to_agent":   "agent-b-orch",
        "task":       "compensation_analysis",
    }).json()
    gate_c = client.post("/policy/gate", json={
        "from_agent": "agent-a-orch",
        "to_agent":   "agent-c-orch",
        "task":       "non_compete_enforceability",
    }).json()

    print(f"  Gate B: {'✓ allowed' if gate_b['allowed'] else '✗ blocked'}  — {gate_b['reason']}")
    print(f"  Gate C: {'✓ allowed' if gate_c['allowed'] else '✗ blocked'}  — {gate_c['reason']}")

    # ── Step 5: Trust gates ───────────────────────────────────────────────────
    hr("Step 5 · Trust — gate both handoffs")

    trust_b = client.get("/trust/agent-a-orch/agent-b-orch").json()
    trust_c = client.get("/trust/agent-a-orch/agent-c-orch").json()
    print(f"  Agent-A → Agent-B trust:  {trust_b.get('trust_score', 0.5):.3f}  ({trust_b.get('recommendation', 'caution')})")
    print(f"  Agent-A → Agent-C trust:  {trust_c.get('trust_score', 0.5):.3f}  ({trust_c.get('recommendation', 'caution')})")

    # ── Step 6: Fan-out StateTransfer ─────────────────────────────────────────
    hr("Step 6 · StateTransfer — fan-out packets")

    story_ctx = state.get("narrative_summary", "")
    base_payload = {
        **SCENARIO,
        "story_context":      story_ctx,
        "policy_agreement_b": agree_b["agreement_id"],
        "policy_agreement_c": agree_c["agreement_id"],
    }

    def _transfer(from_id: str, to_id: str, data: Dict) -> tuple:
        prep = client.post("/transfer/prepare", json={
            "from_agent_id": from_id, "to_agent_id": to_id,
            "reason": "escalation", "state_data": data,
        }).json()
        pid  = prep["packet_id"]
        send = client.post("/transfer/send",    json={"agent_id": from_id, "packet_id": pid}).json()
        recv = client.post("/transfer/receive", json={"agent_id": to_id,   "packet": send}).json()
        return pid, recv.get("success", False)

    def _return_transfer(from_id: str, to_id: str, data: Dict) -> tuple:
        prep = client.post("/transfer/prepare", json={
            "from_agent_id": from_id, "to_agent_id": to_id,
            "reason": "completion", "state_data": data,
        }).json()
        pid  = prep["packet_id"]
        send = client.post("/transfer/send",    json={"agent_id": from_id, "packet_id": pid}).json()
        recv = client.post("/transfer/receive", json={"agent_id": to_id,   "packet": send}).json()
        return pid, recv.get("success", False)

    pid_b, recv_b = _transfer("agent-a-orch", "agent-b-orch", {
        **base_payload, "task": "compensation_analysis",
    })
    pid_c, recv_c = _transfer("agent-a-orch", "agent-c-orch", {
        **base_payload, "task": "non_compete_enforceability",
    })

    print(f"  Packet → Agent-B  ({pid_b[:16]}...)  received: {recv_b}")
    print(f"  Packet → Agent-C  ({pid_c[:16]}...)  received: {recv_c}")

    # ── Step 7: Agents B and C respond ───────────────────────────────────────
    hr("Step 7 · Fan-out — B and C work in parallel")

    b_prompt = (
        f"Accepted: {SCENARIO['accepted_offer']}. "
        f"Competing: {SCENARIO['competing_offer']}. "
        f"Non-compete: {SCENARIO['non_compete']}. "
        f"Deadline: {SCENARIO['deadline_hours']}h. Analyse compensation."
    )
    c_prompt = (
        f"User is in {SCENARIO['location']}. "
        f"Non-compete clause: {SCENARIO['non_compete']}, same industry. "
        f"Analyse enforceability under California law."
    )

    if DRY_RUN:
        response_b = DRY_B_RESPONSE
        response_c = DRY_C_RESPONSE
    else:
        response_b = call_claude(AGENT_B_SYSTEM, b_prompt, max_tokens=300)
        response_c = call_claude(AGENT_C_SYSTEM, c_prompt, max_tokens=300)

    print(f"\n  ▸ Agent-B (compensation):\n{wrap(response_b)}")
    print(f"\n  ▸ Agent-C (employment lawyer, CA):\n{wrap(response_c)}")

    # ── Step 8: Return packets ────────────────────────────────────────────────
    hr("Step 8 · Return packets — B and C hand results back to A")

    ret_pid_b, ret_recv_b = _return_transfer("agent-b-orch", "agent-a-orch", {
        "task": "compensation_analysis", "result": response_b,
    })
    ret_pid_c, ret_recv_c = _return_transfer("agent-c-orch", "agent-a-orch", {
        "task": "non_compete_enforceability", "result": response_c,
    })

    print(f"  Return B → A  ({ret_pid_b[:16]}...)  received: {ret_recv_b}")
    print(f"  Return C → A  ({ret_pid_c[:16]}...)  received: {ret_recv_c}")

    # ── Step 9: Agent-A synthesizes ───────────────────────────────────────────
    hr("Step 9 · Agent-A synthesizes — the CA insight changes everything")

    synthesis_prompt = (
        f"User story: {story_ctx or 'Marcus left stable job for startup in CA for autonomy and meaning.'}\n"
        f"Location: {SCENARIO['location']}\n\n"
        f"Agent-B (compensation) report:\n{response_b}\n\n"
        f"Agent-C (CA employment lawyer) report:\n{response_c}\n\n"
        f"User's question: Should I take the competing offer? I have 48 hours."
    )

    if DRY_RUN:
        synthesis = DRY_SYNTHESIS
    else:
        synthesis = call_claude(AGENT_A_SYNTHESIS_SYSTEM, synthesis_prompt, max_tokens=500)

    print(f"\n  ▸ Agent-A synthesized answer:\n{wrap(synthesis, width=66)}")

    # ── Step 10: Trust updates ────────────────────────────────────────────────
    hr("Step 10 · Trust — record outcomes")

    for from_a, to_a, outcome in [
        ("agent-a-orch", "agent-b-orch", "compensation_analysis_delivered"),
        ("agent-a-orch", "agent-c-orch", "legal_analysis_ca_delivered"),
    ]:
        client.post("/trust/record-outcome", json={
            "from_agent":   from_a,
            "to_agent":     to_a,
            "task":         outcome,
            "success":      True,
            "feedback":     "Result used in synthesis",
        })

    tb_after = client.get("/trust/agent-a-orch/agent-b-orch").json()
    tc_after = client.get("/trust/agent-a-orch/agent-c-orch").json()

    print(f"  Trust A→B: 0.500 → {tb_after.get('trust_score', 0.6):.3f}")
    print(f"  Trust A→C: 0.500 → {tc_after.get('trust_score', 0.6):.3f}")

    # ── Summary ───────────────────────────────────────────────────────────────
    hr("Summary — Orchestrator: fan-out + return + synthesis")
    print(f"  StoryKeeper   ✓  Marcus's 3-month narrative carried through")
    print(f"  StateTransfer ✓  fan-out packets (A→B, A→C) + return packets (B→A, C→A)")
    print(f"  ContextShare  ✓  B got financial context, C got legal context — not everything")
    print(f"  Trust         ✓  both handoffs gated, both outcomes recorded")
    print(f"  PolicyAlign   ✓  B and C each bound to scoped agreements")
    print()
    print(f"  The CA insight:")
    print(f"  Without Orchestrator  →  B and C answer in isolation")
    print(f"  With Orchestrator     →  Agent-A sees that CA §16600 voids the non-compete")
    print(f"                            and gives Marcus one answer that changes everything")
    print()


if __name__ == "__main__":
    run()
