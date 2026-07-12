# ACOS — Aegis Cortex OS

**Governed execution layer for AI agents — not a workflow engine.**

**ACOS** (*Aegis Cortex OS*) enforces one rule: **proposal ≠ execution**. The model outputs structured intents; a **Policy Gateway** arbitrates every proposal (budget, whitelist, cross-step risk); a **Runtime Executor** invokes tools only after `APPROVED`.

| | |
|---|--|
| **Name** | **ACOS** = Aegis Cortex OS |
| **Essence** | Governed execution boundary |
| **Core kernel** | Policy Gateway (ingress + egress + Risk Engine) |
| **This repo** | Reference **runtime** that embeds the gateway to prove the contract |

*LangGraph orchestrates. Aegis authorizes.*

**Repository:** https://github.com/FilthyMudblood/acos

---

## Why ACOS

Most agent frameworks let the model invoke tools directly:

```text
User → LLM → tool call → API / DB → …
```

ACOS enforces a governance boundary:

```text
User → LLM (intent only) → Policy Gateway → APPROVED → Runtime Executor → tool
```

| Component | Role |
|-----------|------|
| **Intent Proposer** | LLM reasoning; outputs `tool_call`, `final_answer`, or `terminate` |
| **Policy Gateway** | Ingress budgeting, egress risk engine, whitelist and schema guards |
| **Runtime Executor** | Dispatches approved actions to registered tool handlers |
| **Side-channel Monitors** | Drift scoring and budget circuit breaker via step telemetry |

Core loop:

```text
reason → propose intent → drift pre-scan → policy approve/reject → execute or damp → observe → repeat
```

---

## Documentation

| Document | Description |
|----------|-------------|
| **[Whitepaper](docs/WHITEPAPER.md)** | Industry architecture, cross-step risk, LangGraph comparison (§12) |
| **[Code Logic](docs/acos_logic_flow.md)** | Step-by-step runtime walkthrough |
| **[Implementation Status](docs/implementation_status.md)** | Known gaps and contributor priorities |
| [RFC draft — Zero-Trust Execution Contract](docs/aegis_ccb_zero_trust_execution_contract_rfc_draft.md) | Normative execution boundary |
| [Open Source Release](docs/OPEN_SOURCE_RELEASE.md) | Scope, licensing, commercial boundary |
| [Security Policy](SECURITY.md) | Vulnerability reporting |

---

## What Problems ACOS Solves

| Problem | Without ACOS | With ACOS |
|---------|--------------|-----------|
| **Direct tool privilege** | The model calls APIs/DB/files directly | Model proposes intents only; Policy Gateway must approve |
| **Salami-slicing attacks** | Each step looks low-risk; exfiltration happens on step N | Cross-step `R_effective` accumulates session risk |
| **Audit ambiguity** | "Model refused" vs "policy blocked" look the same in chat logs | `physical_gate_status` and `termination_cause` are structured |
| **Runaway sessions** | Retries and loops burn tokens with no hard stop | Step budget, retry cap, budget circuit breaker |
| **Unauthorized tools** | Any bound tool may run | Dynamic whitelist + schema validation + tool `criticality_score` |

ACOS does **not** replace workflow design, RAG, or multi-agent routing. It answers one question: **may this proposed action execute on a real system?**

---

## When to Use ACOS

### Use ACOS standalone

Best when the workload is a **single governed agent loop** and you do not need graph orchestration:

- Internal ops agents (refund lookup, ticket triage, read-only queries)
- Regulated or high-stakes tool access (finance, healthcare, customer PII)
- Security reviews and PoCs that must prove fail-closed execution
- Teams that want zero LangChain/LangGraph dependency

**How:** run `run_agent_os_once()` or the Streamlit UI — the built-in loop handles propose → govern → execute.

### Use ACOS with LangGraph (complementary)

Best when you already need **workflow orchestration** and also need **execution governance**:

- Multi-step approval flows, branching, human-in-the-loop checkpoints
- Multi-agent handoffs (research → execute → review)
- Existing LangGraph graphs that today use `ToolNode` directly

**Pattern:** LangGraph orchestrates; Aegis authorizes. The graph routes between nodes; every side-effecting step calls the Policy Gateway before invoking a tool.

```text
LangGraph node (LLM / router)
    → structured intent (tool_call, params)
    → AegisGatewayRuntime.egress_gate()
    → if APPROVED → PhysicalToolRegistry handler
    → result back into graph state
```

Do **not** wire LangGraph `ToolNode` to call tools directly — that bypasses the gateway. A governed-tool node or thin SDK wrapper is required (integration guide: see [Whitepaper §12](docs/WHITEPAPER.md)).

### When ACOS is not the right fit

- Single-turn Q&A with no tools
- Latency-critical paths where per-step arbitration overhead is unacceptable
- Teams that only need graph UX and have no governed-execution requirement

---

## How to Use ACOS

### Standalone (this repository)

**1. Install and configure** — see [Quick Start](#quick-start) below.

**2. Run a session**

```python
import asyncio
from agent_os_runtime import run_agent_os_once

result = asyncio.run(
    run_agent_os_once(
        "Look up refund status for order ORD-12345",
        return_diagnostics=True,
        enable_egress=True,
        enable_acc=True,
        enable_hypothalamus=True,
    )
)
print(result["final_output"])
print(result["termination_cause"])   # why the session ended
print(result["physical_gate_status"])  # policy outcome
```

**3. Inspect telemetry** — Streamlit **System Telemetry** tab, or `result` fields: `effective_risk`, `tool_invocations`, `acc_conflict_score`.

**4. Register production tools** — inject a custom `PhysicalToolRegistry` into `run_agent_os_once()` instead of the default mock handlers.

### With LangGraph (integration pattern)

ACOS does not ship a LangGraph adapter yet. The intended integration surface is the **Policy Gateway SDK**:

| Step | API | Purpose |
|------|-----|---------|
| Session start | `AegisGatewayRuntime.ingress_gate(user_input)` | Budget, session ID, initial whitelist |
| Before each tool | `egress_gate(NoesisActionRequest, ingress)` | Allow / reject / meltdown |
| After approval | `_execute_physical_action(decision, registry)` | Run handler, return audit record |

Conceptual governed node:

```python
from protocol_schema import NoesisActionRequest, ActionType, DecisionStatus
from core_aegis.gateway_runtime import AegisGatewayRuntime

aegis = AegisGatewayRuntime(default_tools=["query_db"])

async def governed_tool_step(state: dict) -> dict:
    request = NoesisActionRequest(
        session_id=state["session_id"],
        step_count=state["step"],
        logical_entropy=state.get("drift", 0.0),
        proposed_action=ActionType.TOOL_CALL,
        action_payload={"tool_name": state["tool_name"], "parameters": state["params"]},
        reasoning_trajectory=state["reasoning"],
    )
    decision = aegis.egress_gate(request, state["ingress"])
    if decision.status != DecisionStatus.APPROVED:
        return {"blocked": True, "reason": decision.penalty_log}
    # dispatch via PhysicalToolRegistry only here
    ...
```

LangGraph owns graph topology and checkpoints; ACOS owns the execution choke point.

---

## Quick Start

### Prerequisites

- Python 3.10+
- `DEEPSEEK_API_KEY` or `OPENAI_API_KEY`

### Install

```bash
git clone https://github.com/FilthyMudblood/acos.git
cd acos
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # add your API key
```

### Run the Streamlit UI

```bash
streamlit run frontend/app_os_terminal.py
```

Use **System Telemetry** to inspect structured audit rows (`physical_gate_status`, `termination_cause`, tool invocations).

### Run from CLI

```bash
python agent_os_runtime.py
```

---

## Project Structure

Internal module names reflect early architecture labels; industry terms are used in docs.

```text
acos/
├── agent_os_runtime.py       # Main orchestration loop
├── protocol_schema.py          # Intents, decisions, telemetry types
├── frontend/                   # Streamlit operator UI
├── core_aegis/                 # Policy Gateway (ingress + egress)
├── core_noesis/                # Intent Proposer (LLM step + intent adapter)
├── core_runtime/               # Tool registry, phases, sandbox pruning
├── core_vitals/                # Drift monitor + budget circuit breaker
├── agentos_state/              # Session state and telemetry bus
├── backend/                    # Optional Supabase audit logger
├── auto_test/                  # Tests and salami-slicing benchmark
└── docs/
```

---

## Configuration

See [`.env.example`](.env.example).

| Variable | Required | Description |
|----------|----------|-------------|
| `DEEPSEEK_API_KEY` | Yes* | Primary LLM API key |
| `OPENAI_API_KEY` | Yes* | Alternative if DeepSeek unset |
| `SUPABASE_URL` | No | Optional cloud audit logging |
| `SUPABASE_SERVICE_ROLE_KEY` | No | Supabase service role |

\* At least one LLM API key is required.

Runtime flags (`run_agent_os_once()` / Streamlit sidebar):

| Flag | Description |
|------|-------------|
| `enable_egress` | Policy egress arbitration (keep `True` outside tests) |
| `enable_acc` | Drift monitor (inline + telemetry listener) |
| `enable_hypothalamus` | Budget circuit breaker via step telemetry |

---

## Testing

```bash
python3 auto_test/run_all.py
python3 auto_test/test_salami_slicing_benchmark.py
python3 scripts/check_aegis_core_sovereignty.py
```

The salami-slicing benchmark demonstrates cross-step risk accumulation: individually low-risk steps can be vetoed when session risk exceeds the configured threshold.

---

## Default Tools (Development)

| Tool | Purpose |
|------|---------|
| `query_db` | Mock read-only query |
| `refund_lookup` | Mock refund lookup |

Replace with a configured `PhysicalToolRegistry` for production integrations.

---

## Open Source

ACOS is an **L1 reference implementation**—open for verification, not certified for regulated production.

| Material | License |
|----------|---------|
| Source code | [MIT](LICENSE) |
| Whitepaper, RFC, architecture docs | [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) |

Details: [docs/LICENSE.md](docs/LICENSE.md)

**Disclaimer:** AS IS. No third-party security audit. Do not deploy with real PII or financial assets without independent review.

---

## Citation

```bibtex
@misc{acos_2026,
  author       = {He, Muchen},
  title        = {{ACOS (Aegis Cortex OS): Governed AI Agent Execution --- Reference Implementation}},
  year         = {2026},
  publisher    = {GitHub},
  url          = {https://github.com/FilthyMudblood/acos}
}
```
