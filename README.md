# pact-demos

Runnable reference implementations for the [PACT ecosystem](https://github.com/neurobloomai).  
Every demo targets a real use case — no toy examples.

---

## Setup

```bash
git clone https://github.com/neurobloomai/pact-demos
cd pact-demos
pip install -r requirements.txt   # pact-ax + pact-hx (editable)
npm install                        # for browser/streaming demos
export ANTHROPIC_API_KEY=sk-ant-... # required for live LLM calls; omit for dry-run
```

---

## Demos

### New primitives

| Demo | Path | What it shows |
|---|---|---|
| **Capability Routing** | `demos/capability_routing/` | Register skills → trust-weighted routing → handoff to best agent |
| **Orchestrate REST** | `demos/orchestrate_rest/` | Fan-out via the PACT-AX REST API — parallel, conditional, race strategies |
| **Seam Observer** | `demos/seam_observer/` | Live SSE stream of agent events — browser UI with clickable demo triggers |

### Core primitives

| Demo | Path | What it shows |
|---|---|---|
| **Four Primitive** | `demos/four_primitive/` | StoryKeeper + StateTransfer + ContextShare + Trust — Marcus's career crisis |
| **Orchestrator** | `demos/orchestrator/` | Fan-out to Agent-B (compensation) + Agent-C (CA employment law) in parallel |
| **Orchestrator v2** | `demos/orchestrator_v2/` | Extended orchestration with trust-weighted selection |
| **Two Agent** | `demos/two_agent/` | Basic A→B handoff with ledger |
| **Trust Network** | `demos/trust_network/` | Trust graph evolving across multiple agents |
| **Multi-Agent Swarm** | `demos/multi_agent_swarm/` | Swarm coordination at scale |
| **Context Security** | `demos/context_security/` | ContextShare with access control |
| **Story Keeper** | `demos/story_keeper/` | Narrative continuity standalone |
| **State Transfer** | `demos/state_transfer/` | Structured handoff packets |

---

## Run a demo

### CLI (fastest)

```bash
python demos/capability_routing/demo.py
python demos/orchestrate_rest/demo.py
python demos/four_primitive/demo.py
python demos/orchestrator/demo.py
```

### Browser (streams live agent events)

```bash
# Seam Observer — watch all agent activity in real time
npm run seam-observer
# open http://localhost:4002

# Full suite with browser UI
ANTHROPIC_API_KEY=sk-ant-... npm run four-primitive
ANTHROPIC_API_KEY=sk-ant-... npm run orchestrator
```

---

## What the SDK looks like alongside these demos

The demos run against the PACT-AX server directly. To build your own agent on the same primitives:

```bash
pip install pact-ax-client
```

```python
from pact_ax_client import Agent

agent = Agent("my-agent", base_url="http://localhost:8000")
agent.register_capability("contract_review", description="Reviews NDAs")

decision = agent.route("contract_review")
if decision.routed:
    result = agent.handoff(decision.best_agent, state_data={"doc": "..."})
    agent.remember("contract_review", partner_id=decision.best_agent, outcome="positive")
```

[pact-ax-client on PyPI](https://pypi.org/project/pact-ax-client/) · [SDK repo](https://github.com/neurobloomai/pact-ax-client)

---

## Ecosystem

| Repo | What it is |
|---|---|
| [`pact`](https://github.com/neurobloomai/pact) | Protocol spec — the why |
| [`pact-ax`](https://github.com/neurobloomai/pact-ax) | Agent collaboration server (84 routes, 743 tests) |
| [`pact-ax-client`](https://github.com/neurobloomai/pact-ax-client) | Python SDK — `pip install pact-ax-client` |
| [`pact-hx`](https://github.com/neurobloomai/pact-hx) | Human experience layer |
| [`pact-demos`](https://github.com/neurobloomai/pact-demos) | This repo |

---

MIT — [neurobloom.ai](https://neurobloom.ai)
