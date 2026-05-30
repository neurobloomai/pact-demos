# pact-demos

All demos and examples for the PACT ecosystem — pact-ax primitives, pact-hx memory layer, and multi-agent orchestration.

## Setup

```bash
pip install -r requirements.txt   # installs pact-ax + pact-hx as editable
npm install                        # for browser demo servers
```

## Demos

| Demo | Path | What it shows |
|---|---|---|
| **Four Primitive** | `demos/four_primitive/` | StoryKeeper + StateTransfer + ContextShare + Trust + PolicyAlign — Marcus's career crisis |
| **Orchestrator** | `demos/orchestrator/` | Fan-out to Agent-B (compensation) + Agent-C (CA employment law) in parallel — CA §16600 voids the non-compete |
| **Two Agent** | `demos/two_agent/` | Basic A→B handoff with ledger |
| **Trust Network** | `demos/trust_network/` | Trust graph across multiple agents |
| **Multi-Agent Swarm** | `demos/multi_agent_swarm/` | Swarm coordination |
| **Context Security** | `demos/context_security/` | ContextShare with access control |
| **Story Keeper** | `demos/story_keeper/` | Narrative continuity standalone |
| **State Transfer** | `demos/state_transfer/` | Structured handoff packets |

## Run a demo

```bash
# CLI
python demos/four_primitive/demo.py
python demos/orchestrator/demo.py

# Browser (streams live output)
ANTHROPIC_API_KEY=sk-ant-... npm run four-primitive
ANTHROPIC_API_KEY=sk-ant-... npm run orchestrator
```

## Environment

```bash
export ANTHROPIC_API_KEY=sk-ant-...   # required for live LLM calls
                                       # omit for dry-run mode
```
