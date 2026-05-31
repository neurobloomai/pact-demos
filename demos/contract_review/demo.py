"""
Contract Review Pipeline Demo
──────────────────────────────
A complete multi-agent contract review scenario using pact-ax-client SDK.

Scenario
────────
ACME Corp sends NeuroBloom a mutual NDA for signature. An orchestrator agent
receives it, discovers the best available contract reviewer, checks trust,
hands off the document, collects findings, updates trust based on outcome,
and records the episode to both agents' episodic memory. A final consensus
vote confirms whether the contract should be approved.

Pipeline steps:
  1. Register specialist capabilities
  2. Build initial trust history
  3. Route to best contract reviewer (trust-weighted)
  4. Check trust score before handoff
  5. Hand off contract + metadata
  6. Reviewer analyses the contract
  7. Consensus vote: approve / reject / request_changes
  8. Trust updated based on outcome
  9. Both agents record episode to memory
  10. Summary printed

Run:
  python demos/contract_review/demo.py

Requires pact-ax server on http://localhost:8765 (PACT_ENFORCE_AUTH=0).
"""

import sys
import textwrap
import time

from pact_ax_client import Agent, Vote
from pact_ax_client.exceptions import PactAXError

BASE = "http://127.0.0.1:8765"

# ── Sample contract ────────────────────────────────────────────────────────────

NDA_TEXT = """
MUTUAL NON-DISCLOSURE AGREEMENT

This Agreement is entered into as of May 31, 2026, between:
  NeuroBloom.ai, Inc. ("Company A")
  ACME Corp. ("Company B")

1. CONFIDENTIAL INFORMATION
   Each party may disclose confidential information to the other solely for
   evaluating a potential business relationship ("Purpose").

2. OBLIGATIONS
   Each party agrees to: (a) hold the other party's Confidential Information
   in strict confidence; (b) not disclose it to third parties without prior
   written consent; (c) use it only for the Purpose.

3. TERM
   This Agreement shall remain in effect for two (2) years from the date above.

4. GOVERNING LAW
   This Agreement shall be governed by the laws of the State of California.
""".strip()

# ── Simulated review logic ─────────────────────────────────────────────────────

REVIEWS = {
    "nda-specialist": {
        "risk_level":      "low",
        "recommendation":  "approve",
        "confidence":      0.88,
        "findings": [
            "Standard mutual NDA — both parties equally bound.",
            "2-year term within normal range (1–3 years typical).",
            "California governing law — favorable for Company A.",
            "No carve-outs for prior knowledge — recommend adding standard exclusions.",
        ],
    },
    "contract-reviewer-b": {
        "risk_level":      "low",
        "recommendation":  "approve",
        "confidence":      0.81,
        "findings": [
            "Confidentiality obligations are symmetric and clearly defined.",
            "No auto-renewal clause — good for flexibility.",
            "Missing dispute resolution clause — minor gap.",
        ],
    },
    "legal-generalist": {
        "risk_level":      "medium",
        "recommendation":  "request_changes",
        "confidence":      0.65,
        "findings": [
            "Term and governing law appear standard.",
            "Scope of 'Confidential Information' is broad — could benefit from tighter definition.",
            "Recommend legal counsel review before signature.",
        ],
    },
}

# ── Helpers ────────────────────────────────────────────────────────────────────

W = 64

def banner(step, title):
    print(f"\n{'─' * W}")
    print(f"  {step}  {title}")
    print(f"{'─' * W}")


def wait_for_server(base_url: str, retries: int = 30):
    import urllib.request
    import urllib.error
    for _ in range(retries):
        try:
            urllib.request.urlopen(base_url + "/health")
            return
        except Exception:
            time.sleep(0.5)
    print(f"Could not reach pact-ax server at {base_url}")
    print("Start it with: uvicorn pact_ax.api.server:app --port 8765 --reload")
    sys.exit(1)


# ── Pipeline ───────────────────────────────────────────────────────────────────

def run():
    print(f"\n{'═' * W}")
    print("  PACT-AX  ·  Contract Review Pipeline")
    print("  Scenario: ACME Corp sends NeuroBloom a mutual NDA for review")
    print(f"{'═' * W}")

    wait_for_server(BASE)

    with Agent("orchestrator",        base_url=BASE) as orch, \
         Agent("nda-specialist",      base_url=BASE) as specialist, \
         Agent("contract-reviewer-b", base_url=BASE) as reviewer_b, \
         Agent("legal-generalist",    base_url=BASE) as generalist:

        # ── 1. Register capabilities ───────────────────────────────────────
        banner("1.", "Register specialist capabilities")

        registrations = [
            (specialist,  "contract_review", "Expert NDA and IP agreement review",      ["legal", "nda", "ip"]),
            (reviewer_b,  "contract_review", "Specialises in service and vendor NDAs",  ["legal", "nda"]),
            (generalist,  "contract_review", "General contract analysis and red-lining", ["legal"]),
        ]

        for agent, skill, desc, tags in registrations:
            cap = agent.register_capability(skill, description=desc, tags=tags)
            print(f"  ✓ {agent.agent_id:<22} → {cap.skill}  {cap.tags}")

        # ── 2. Build trust history ─────────────────────────────────────────
        banner("2.", "Build trust history: orchestrator → specialists")

        trust_updates = [
            ("nda-specialist",      "positive", 0.9),
            ("nda-specialist",      "positive", 1.0),
            ("contract-reviewer-b", "positive", 0.7),
            ("legal-generalist",    "negative", 0.8),
        ]

        for target, outcome, impact in trust_updates:
            orch.update_trust(target, outcome=outcome, impact=impact)

        for target in ["nda-specialist", "contract-reviewer-b", "legal-generalist"]:
            ts = orch.get_trust(target)
            bar = "█" * int(ts.score * 10) + "░" * (10 - int(ts.score * 10))
            print(f"  {target:<24} {bar}  {ts.score:.2f}")

        # ── 3. Route ───────────────────────────────────────────────────────
        banner("3.", "Route: who is the best agent to review this NDA?")

        decision = orch.route("contract_review", min_trust=0.4, top_k=3)

        if not decision.routed:
            print("  No capable agent found above min_trust threshold — aborting.")
            return

        print(f"  best_agent     = {decision.best_agent!r}")
        print(f"  strategy       = {decision.strategy_used}")
        print(f"\n  Candidates (ranked by trust × capability):")
        for c in decision.candidates:
            marker = " ◀ selected" if c.agent_id == decision.best_agent else ""
            print(f"    {c.agent_id:<24} trust={c.trust_score:.2f}{marker}")

        reviewer_id = decision.best_agent

        # ── 4. Check trust ─────────────────────────────────────────────────
        banner("4.", f"Trust check before handoff → {reviewer_id!r}")

        ts = orch.get_trust(reviewer_id)
        print(f"  trust_score    = {ts.score:.2f}")
        print(f"  recommendation = {ts.recommendation}")

        if ts.recommendation == "block":
            print("  Trust too low — aborting handoff.")
            return

        # ── 5. Handoff ─────────────────────────────────────────────────────
        banner("5.", f"Handoff contract → {reviewer_id!r}")

        result = orch.handoff(
            reviewer_id,
            state_data={
                "contract_text": NDA_TEXT,
                "metadata": {
                    "parties":        ["NeuroBloom.ai, Inc.", "ACME Corp."],
                    "type":           "mutual_nda",
                    "effective_date": "2026-05-31",
                    "priority":       "high",
                    "submitted_by":   "legal@acmecorp.com",
                },
            },
            reason="contract_review_request",
        )
        print(f"  packet_id  = {result.packet_id}")
        print(f"  received   = {result.received}")
        print(f"  to_agent   = {result.to_agent}")

        # ── 6. Review ──────────────────────────────────────────────────────
        banner("6.", f"{reviewer_id!r} reviews the contract")

        review = REVIEWS.get(reviewer_id, REVIEWS["nda-specialist"])
        print(f"  risk_level     = {review['risk_level'].upper()}")
        print(f"  recommendation = {review['recommendation']}")
        print(f"  confidence     = {review['confidence']:.0%}")
        print()
        for finding in review["findings"]:
            print(f"    • {textwrap.fill(finding, width=56, subsequent_indent='      ')}")

        # ── 7. Consensus vote ──────────────────────────────────────────────
        banner("7.", "Consensus vote: approve / request_changes / reject")

        other_votes = [
            Vote("legal-team-lead",    review["recommendation"], 0.90),
            Vote("compliance-officer", review["recommendation"], 0.85),
        ]
        consensus = orch.vote(
            review["recommendation"],
            review["confidence"],
            other_votes=other_votes,
        )

        print(f"  outcome          = {consensus.outcome}")
        print(f"  winning_decision = {consensus.winning_decision!r}")
        print(f"  confidence       = {consensus.confidence_score:.0%}")
        print(f"  strategy         = {consensus.strategy_used}")

        # ── 8. Update trust ────────────────────────────────────────────────
        banner("8.", "Update trust based on review outcome")

        outcome = "positive" if consensus.reached else "negative"
        updated = orch.update_trust(reviewer_id, outcome=outcome, impact=0.8)
        print(f"  {reviewer_id}: {ts.score:.2f}  →  {updated.score:.2f}  ({outcome})")

        # ── 9. Record episodes ─────────────────────────────────────────────
        banner("9.", "Both agents record the episode to episodic memory")

        reviewer_agent = {
            "nda-specialist":      specialist,
            "contract-reviewer-b": reviewer_b,
            "legal-generalist":    generalist,
        }[reviewer_id]

        orch_ep = orch.remember(
            "contract_review",
            partner_id=reviewer_id,
            outcome=outcome,
            importance=0.85,
            tags=["legal", "nda", "acme"],
        )
        rev_ep = reviewer_agent.remember(
            "contract_review",
            partner_id="orchestrator",
            outcome=outcome,
            importance=0.9,
            tags=["legal", "nda"],
        )
        print(f"  orchestrator   episode {orch_ep.id!r}")
        print(f"  {reviewer_id:<22} episode {rev_ep.id!r}")

        # ── 10. Summary ────────────────────────────────────────────────────
        banner("✓", "Summary")

        s = orch.memory_summary()
        print(f"  contract outcome      = {consensus.winning_decision.upper()}")
        print(f"  reviewer              = {reviewer_id}")
        print(f"  final trust score     = {updated.score:.2f}")
        print(f"  orchestrator episodes = {s.total_episodes}")
        print(f"  outcome breakdown     = {s.outcome_breakdown}")

    print(f"\n{'═' * W}")
    print("  Pipeline complete.")
    print(f"{'═' * W}\n")


if __name__ == "__main__":
    run()
