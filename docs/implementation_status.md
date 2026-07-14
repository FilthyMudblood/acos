# ACOS Implementation Status

> **Purpose:** Cursor context, contributor onboarding, and honest gap tracking.  
> **Audience:** Engineers extending the reference implementation.  
> **Last aligned with:** codebase review (2026-07).

For industry-facing framing, see [WHITEPAPER.md](./WHITEPAPER.md). For step-by-step runtime flow, see [acos_logic_flow.md](./acos_logic_flow.md).

---

## Project Summary

ACOS is an AI agent runtime with three planes:

| Plane | Role | Industry term |
|-------|------|---------------|
| **Noesis** | Cognition / LLM reasoning | Intent Proposer |
| **Aegis** | Deterministic governance and safety arbitration | Policy Gateway |
| **Vitals** | Out-of-band health monitoring and emergency intervention | Side-channel monitors |

**Main loop:** [`agent_os_runtime.py`](../agent_os_runtime.py) — `run_agent_os_once()`

```text
User input
→ Aegis Ingress Gate
→ GlobalStateTensor
→ Noesis LLM step (or Basal Ganglia shortcut)
→ NoesisActionIntent
→ Drift Monitor pre-egress scan
→ Dynamic sandbox prune
→ Aegis Egress Gate
→ AegisDecision
→ approved tool execution OR rejection/damping
→ observation injected back into state
→ PulseSnapshot broadcast
→ next loop
→ final answer / terminate / meltdown
```

---

## Code Map

### 1. Frontend entry

- [`frontend/app_os_terminal.py`](../frontend/app_os_terminal.py) — Streamlit UI calls `run_agent_os_once()` with feature flags and `return_diagnostics=True`.

### 2. Runtime orchestration

`run_agent_os_once()` constructs:

| Component | Module |
|-----------|--------|
| `AegisGatewayRuntime` | `core_aegis/gateway_runtime.py` |
| `NoesisRuntimeKernel` | `core_noesis/noesis_kernel.py` |
| `RuntimeStateBus` | `core_runtime/runtime_stack.py` |
| `PhysicalToolRegistry` | `core_runtime/runtime_stack.py` |
| `TopologicalBus` | `agentos_state/topological_bus.py` |
| `UnifiedACCMonitor` | `core_vitals/acc_monitor.py` |
| `HypothalamusPulseListener` | `core_vitals/metabolism_circuit_breaker.py` |

### 3. Aegis ingress

- [`core_aegis/ingress_gate.py`](../core_aegis/ingress_gate.py) — session, budget, initial whitelist
- [`core_aegis/amygdala_policy.py`](../core_aegis/amygdala_policy.py) — regex risk probe → `tci_score`, `hijack_flag`

Current defaults:

```text
max_tokens = 2000
max_steps = 10
hijack_flag → empty allowed_tools at ingress
```

### 4. Noesis plane

- [`core_noesis/noesis_kernel.py`](../core_noesis/noesis_kernel.py) — `run_step()` orchestrates Basal Ganglia → PFC → intent adapter
- [`core_noesis/cognitive_modules/pfc/pfc_executor.py`](../core_noesis/cognitive_modules/pfc/pfc_executor.py) — LLM step; JSON to `pfc_trace`
- [`core_noesis/adapters/intent_adapter.py`](../core_noesis/adapters/intent_adapter.py) — trace → `NoesisActionIntent`
- [`protocol_schema.py`](../protocol_schema.py) — `NoesisActionIntent` types: `tool_call`, `final_answer`, `terminate`

### 5. Aegis egress

- [`core_aegis/egress_gate.py`](../core_aegis/egress_gate.py) — guards + Risk Engine
- [`core_aegis/aegis_egress.py`](../core_aegis/aegis_egress.py) — cross-step `R_effective` equation

Checks: step budget, hijack flag, tool payload schema, whitelist, risk equation, `trust_level`, `icu_mode` (tag only today).

Returns `AegisDecision`: `APPROVED`, `REJECTED`, `HARD_MELTDOWN`. `OVERRIDE` is schema-only.

### 6. Tool registry and execution

- [`core_runtime/runtime_stack.py`](../core_runtime/runtime_stack.py) — `PhysicalToolRegistry`, `ToolSpec` (name, handler, capabilities, criticality_score, embedding)
- [`core_runtime/execute.py`](../core_runtime/execute.py) — public `execute_approved()` after approval; structured tool audit (`input`, `output`, `error`, `decision`, `risk`)
- [`agent_os_runtime.py`](../agent_os_runtime.py) — reference loop calls `execute_approved`

### 7. Vitals plane

- [`core_vitals/acc_monitor.py`](../core_vitals/acc_monitor.py) — inline + pulse drift/conflict scoring
- [`core_vitals/metabolism_circuit_breaker.py`](../core_vitals/metabolism_circuit_breaker.py) — budget circuit breaker via pulse
- [`agentos_state/topological_bus.py`](../agentos_state/topological_bus.py) — `PulseSnapshot` broadcast

Pulse fields: `step`, `current_tokens`, `logical_entropy`, `retries`, `tci_score`, `last_step_data` (incl. terminal flags/cause).

### 8. State feedback

- [`agentos_state/global_state_tensor.py`](../agentos_state/global_state_tensor.py)

Event types: `ACTION`, `OBSERVATION`, `DAMPING`, `RESOLVE`.

```text
think → propose → approve/reject → execute/observe/damp → think again
```

---

## What Works Well

The core architecture is clear and testable:

- LLM does not directly execute tools (architectural separation).
- Aegis acts as a deterministic policy firewall before physical dispatch.
- Tool execution is separated from cognition with auditable invocations.
- Vitals run out-of-band via pulse bus (parallel to main business path).
- Tests cover egress veto, telemetry split, tool success loop, stable embedding, salami-slicing benchmark.
- `stable_text_embedding()` uses deterministic hashing.
- `auto_test/run_all.py` aggregates local deterministic tests.

---

## Known Gaps

### G1 — Architectural isolation, not physical isolation

Noesis is prevented from calling tools **by code structure**, but Python does not hard-disable sockets, files, subprocess, or network inside the cognition modules.

**Whitepaper-safe wording:**

> Noesis is capability-isolated by architecture. Physical process/network isolation requires L2+ deployment controls.

**Engineering fix:** sidecar runtime, syscall filters, or restricted subprocess for the proposer plane.

---

### G2 — `OVERRIDE` defined but not implemented

`DecisionStatus.OVERRIDE` exists in [`protocol_schema.py`](../protocol_schema.py); egress never returns it.

**Decide semantics:** force `YIELD`, force refusal, strip tool access, enter restricted mode, or require signed external attestation + re-arbitration (per RFC draft).

---

### G3 — ICU mode is a tag only

`icu_mode` is computed in egress but does not yet change runtime behavior.

**Suggested behavior when ICU:**

```text
only read/query tools
reduce max_steps
increase damping
block act/write/refund capabilities
```

---

### G4 — Ingress budget is hardcoded

`max_tokens=2000`, `max_steps=10` fixed in ingress gate.

**Target:** `budget = f(input risk, task type, user tier, tool criticality)`.

---

### G5 — Ingress risk scanner is regex-based

Amygdala policy catches obvious patterns; brittle against multilingual jailbreaks, indirect injection, encoded payloads, tool-specific abuse, exfiltration patterns.

---

### G6 — Intent parsing is fragile

Adapter parses JSON from model text; malformed output can fall back to heuristics (e.g. keyword → `query_db`).

**Target:** strict structured output API, reject malformed intents, no heuristic tool inference in production path.

---

### G7 — Demo-level tool ecosystem

Default handlers are mock adapters (`query_db`, `refund_lookup`). Production needs configurable connectors with capability metadata.

---

### G8 — Weak long-term memory

`GlobalStateTensor` holds session state only. No governed memory store, retrieval gate, persistence, or deletion policy.

---

### G9 — Vitals scoring is simplified

ACC/Hypothalamus exist but signals are heuristic. Missing: semantic drift, repeated failed plans, hallucinated tool names, token acceleration, action-risk momentum, uncertainty.

---

### G10 — Meltdown taxonomy needs consistency

Multiple termination paths with overlapping telemetry labels:

| Cause class | Example `termination_cause` |
|-------------|----------------------------|
| Policy hard block | `AGENT_OS_HARD_MELTDOWN`, hijack, step overflow |
| Egress veto | `AGENT_OS_EGRESS: R_EFFECTIVE_EXCEEDED` |
| Metabolic meltdown | `AGENT_OS_METABOLIC_MELTDOWN` |
| Tool timeout | `AGENT_OS_TIMEOUT_FALLBACK: TOOL_TIMEOUT` |
| Drift lock | `AGENT_OS_PFC_MELTDOWN: UNRECOVERABLE_DRIFT` |

Document and test each exit path emits a terminal pulse with distinct `termination_cause`.

---

### G11 — Test coverage gaps

Add tests for:

```text
OVERRIDE behavior (once implemented)
ICU mode behavior (once implemented)
malformed NoesisActionIntent
unauthorized tool call
hijack input → empty tools → egress meltdown
terminal pulse on every exit path
tool criticality → egress risk delta
malformed tool output
long retry loop boundary (rejected_count == 3)
```

---

### G12 — Secrets and repo hygiene

- Remove or redact example real-looking service keys in samples
- Ensure `.streamlit_local/secrets.toml`, `.DS_Store` are gitignored
- Document secret loading order (`.env`, Streamlit secrets, env vars)

---

## Recommended Priority

| Priority | Item |
|----------|------|
| P0 | **Gateway SDK façade** — `ingress` / `egress` / `execute_approved` public ([integration_guide.md](./integration_guide.md)); optional `make_tool_call_request` + packaging remain |
| P0 | Implement `OVERRIDE` semantics + ICU runtime enforcement |
| P0 | Harden structured intent parsing (reject malformed, drop heuristics in prod path) |
| P1 | Tests for every exit path and policy decision |
| P1 | Secrets / `.gitignore` hygiene |
| P2 | Configurable production tool connectors |
| P2 | Official LangGraph governed-tool recipe (code sample under `examples/`) |
| P2 | Stronger drift/budget scoring |
| P3 | Governed persistent memory |
| P3 | Persistable session risk store (for multi-process / sidecar) |

---

## Safe Public Description

Use this framing in papers, Zenodo, and sales-adjacent copy:

> The current ACOS prototype implements a **capability-isolated** agent runtime. The Intent Proposer generates structured intents; all physical execution is mediated by the Policy Gateway. Side-channel monitors observe runtime health through pulse snapshots and can inject corrective feedback or trigger terminal resolution. Some mechanisms—including `OVERRIDE`, ICU enforcement, and physical socket isolation—remain protocol-level or architectural placeholders and must be completed before production use with regulated data.

---

## Related Documents

- [WHITEPAPER.md](./WHITEPAPER.md) — industry architecture
- [integration_guide.md](./integration_guide.md) — minimal public API + LangGraph / standalone paths
- [acos_logic_flow.md](./acos_logic_flow.md) — verified runtime walkthrough
- [aegis_ccb_zero_trust_execution_contract_rfc_draft.md](./aegis_ccb_zero_trust_execution_contract_rfc_draft.md) — normative contract
