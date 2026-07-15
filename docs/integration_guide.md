# ACOS Integration Guide

> **Status:** Public SDK surface for Path A. `ingress_gate` / `egress_gate` / `execute_approved` are callable without `run_agent_os_once`.  
> **Audience:** Platform engineers embedding ACOS into LangGraph, custom workflows, or services.  
> **Companion:** [WHITEPAPER.md](./WHITEPAPER.md) §12 · [implementation_status.md](./implementation_status.md)

---

## Positioning

```text
Your orchestrator (LangGraph / custom / business code)  →  routes & prompts
ACOS Policy Gateway                                      →  authorize & audit
Your tools (via PhysicalToolRegistry)                    →  side effects only after APPROVED
```

- **Do not** give the LLM a path that calls tools without `egress` → `execute`.
- **Do not** treat `run_agent_os_once()` as the product API for third-party graphs; it is the reference runtime.

---

## Minimal Public API (v0)

Integrators should only need these modules and types.

### Types (already stable)

| Type | Module | Role |
|------|--------|------|
| `AegisIngressPayload` | `protocol_schema` | Session budget, whitelist, sanitized input |
| `NoesisActionRequest` | `protocol_schema` | Structured intent (proposal only) |
| `AegisDecision` | `protocol_schema` | `APPROVED` / `REJECTED` / `HARD_MELTDOWN` (+ `OVERRIDE` reserved) |
| `ToolCallPayload` | `protocol_schema` | `{tool_name, parameters}` |
| `PhysicalExecutionResult` | `protocol_schema` | Handler outcome |
| `DecisionStatus`, `ActionType` | `protocol_schema` | Enums |
| `ToolSpec`, `PhysicalToolRegistry` | `core_runtime.runtime_stack` | Tool + criticality registration |

### Public façade (implemented)

```python
from protocol_schema import (
    AegisIngressPayload,
    AegisDecision,
    NoesisActionRequest,
    PhysicalExecutionResult,
    DecisionStatus,
    ActionType,
)
from core_aegis.gateway_runtime import AegisGatewayRuntime
from core_runtime.execute import execute_approved
from core_runtime.runtime_stack import PhysicalToolRegistry, ToolSpec


class AegisGatewayRuntime:
    def __init__(
        self,
        default_tools: list[str] | None = None,
        tool_criticality_scores: dict[str, float] | None = None,
    ) -> None: ...

    def ingress_gate(self, raw_input: str) -> AegisIngressPayload:
        """Open a session: budget, session_id, initial whitelist, risk seed."""
        ...

    def egress_gate(
        self,
        request: NoesisActionRequest,
        ingress: AegisIngressPayload,
    ) -> AegisDecision:
        """Arbitrate one proposal. Updates session risk state. No I/O."""
        ...

    def get_session_state(self, session_id: str) -> dict:
        """Read-only snapshot of cross-step policy state (for audit / UI)."""
        ...


# core_runtime/execute.py
async def execute_approved(
    decision: AegisDecision,
    registry: PhysicalToolRegistry,
) -> tuple[PhysicalExecutionResult, dict | None]:
    """
    Sole physical dispatch entry.
    Fail-closed: refuses unless decision.status == APPROVED.
    Returns (result, tool_audit_row | None).
    """
    ...
```

**Invariants the façade must enforce:**

1. `egress_gate` never calls tools, sockets, or files.
2. `execute_approved` refuses non-`APPROVED` decisions (fail-closed).
3. Session risk is keyed by `session_id` and survives across steps until the host ends the session.
4. Every deny / meltdown exposes a stable reason string (`penalty_log` / rejection taxonomy).

### Thin helpers (implemented)

```python
from core_runtime.intent_helpers import make_tool_call_request, is_executable

request = make_tool_call_request(
    session_id=ingress.session_id,
    step_count=1,
    tool_name="query_orders",
    parameters={"order_id": "ORD-1"},
    reasoning_trajectory="lookup order",
)
decision = aegis.egress_gate(request, ingress)
if is_executable(decision):
    result, audit = await execute_approved(decision, registry)
```

Runnable LangGraph-style recipe (no `langgraph` package required for the default demo):

```bash
python examples/langgraph_governed_tool.py
```

---

## Integration paths

### Path A — Gateway insert (recommended)

Use when you already have LangGraph, Temporal, Celery, or handmade loops.

```text
session start
  → gateway.ingress_gate(user_text)
  → store ingress + session_id in host state

each side-effecting step
  → host LLM / router emits tool_name + params (+ reasoning)
  → request = NoesisActionRequest(...)
  → decision = gateway.egress_gate(request, ingress)
  → if not APPROVED: write penalty into host state; do not call tool
  → else: result, audit = await execute_approved(decision, registry)
  → feed observation back to host state

session end
  → host decides END / human interrupt; ACOS does not own checkpointing
```

**LangGraph sketch** (see [`examples/langgraph_governed_tool.py`](../examples/langgraph_governed_tool.py)):

```python
from core_runtime.execute import execute_approved
from core_runtime.intent_helpers import is_executable, make_tool_call_request
from protocol_schema import DecisionStatus

async def governed_tool_node(state: dict) -> dict:
    request = make_tool_call_request(
        session_id=state["session_id"],
        step_count=state["step"] + 1,
        tool_name=state["tool_name"],
        parameters=state.get("params") or {},
        reasoning_trajectory=state.get("reasoning") or "graph tool proposal",
        logical_entropy=float(state.get("logical_entropy", 0.0)),
    )
    decision = state["aegis"].egress_gate(request, state["ingress"])
    if not is_executable(decision):
        return {
            "blocked": True,
            "physical_gate_status": decision.status.value,
            "penalty_log": decision.penalty_log,
        }
    result, audit = await execute_approved(decision, state["registry"])
    return {"blocked": False, "tool_result": result, "tool_audit": audit}
```

Rules for LangGraph:

| Do | Don't |
|----|--------|
| Custom governed node that calls ACOS | Wire stock `ToolNode` straight to tools |
| One gateway instance (or one session risk store) per conversation | Per-subagent independent risk that never merges |
| Map LangChain tool names → `ToolSpec` with `criticality_score` | Treat all tools as equal risk |

### Path B — Standalone reference runtime

Use for single-loop PoCs, demos, and salami-benchmarks:

```python
from agent_os_runtime import run_agent_os_once

result = await run_agent_os_once(
    "…",
    return_diagnostics=True,
    physical_tool_registry=my_registry,  # production connectors
)
```

This path **includes** proposer + vitals + loop. Prefer Path A when an orchestrator already exists.

---

## Ownership boundaries (what ACOS should / should not own)

| Concern | Owner | Notes |
|---------|-------|-------|
| Graph routing, branching, handoffs | Host (e.g. LangGraph) | Not ACOS core |
| Checkpoint / resume UX | Host | ACOS session risk is in-memory unless you persist it |
| Intent formation (LLM prompts) | Host or reference Noesis | SDK path does not require `core_noesis` |
| Authorize tool / budget / cross-step risk | **ACOS gateway** | Non-negotiable |
| Physical tool I/O | **ACOS execute + registry** | Only after `APPROVED` |
| Drift / pulse monitors | Optional (reference runtime) | Not required for Path A v0 |
| Human-in-the-loop pause UI | Host | ACOS may later emit `OVERRIDE` / wait-for-attest |

---

## Today → target gap checklist

| Item | Today | Target |
|------|-------|--------|
| `ingress_gate` / `egress_gate` | Public on `AegisGatewayRuntime` | Done |
| `execute_approved` | Public in `core_runtime/execute.py`; runtime uses it | Done |
| Fail-closed on non-APPROVED execute | Enforced inside `execute_approved` | Done |
| Intent helper without Noesis | `make_tool_call_request` / `is_executable` in `core_runtime/intent_helpers.py` | Done |
| LangGraph recipe | `examples/langgraph_governed_tool.py` | Done (optional `langgraph` compile helper) |
| Package entry | Import deep modules | Eventually `from acos import …` (packaging later) |
| Official LangGraph adapter package | None | Optional later |
| Persist session risk | In-process dict | Host responsibility or future sidecar |

---

## Registering tools (both paths)

```python
from core_runtime.runtime_stack import PhysicalToolRegistry, ToolSpec

async def query_orders(order_id: str) -> dict:
    ...

registry = PhysicalToolRegistry(
    [
        ToolSpec(
            name="query_orders",
            handler=query_orders,
            capabilities={"read"},
            criticality_score=0.3,
        ),
        ToolSpec(
            name="export_csv",
            handler=export_csv,
            capabilities={"export"},
            criticality_score=0.9,
        ),
    ]
)

aegis = AegisGatewayRuntime(
    default_tools=registry.get_tool_names(),
    tool_criticality_scores=registry.as_criticality_map(),
)
```

Higher `criticality_score` advances cross-step `R_effective` faster — treat export / write / refund as high.

---

## Minimal success criteria for “SDK-ready”

An external developer can, without calling `run_agent_os_once`:

1. Open a session with `ingress_gate`.
2. Submit N tool intents through `egress_gate`.
3. Execute only `APPROVED` actions via `execute_approved`.
4. Observe a deny that is attributable (`status` + reason) and replayable for the same risk seed sequence.
5. Pass the salami-slicing style sequence (escalating reads → export) and see veto on the exfiltration step.

---

## Related

- Reference loop: [`agent_os_runtime.py`](../agent_os_runtime.py)
- Gateway: [`core_aegis/gateway_runtime.py`](../core_aegis/gateway_runtime.py)
- Gaps: [implementation_status.md](./implementation_status.md) (G2 OVERRIDE, G3 ICU, G6 intent parsing)
