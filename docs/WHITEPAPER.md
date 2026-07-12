# ACOS Whitepaper

**Governed AI Agent Execution for Regulated and High-Stakes Workloads**

| | |
|---|---|
| **Version** | 1.0 |
| **Status** | Draft — reference implementation available in this repository |
| **Audience** | Security architects, platform engineers, compliance officers, technical executives |

---

## Executive Summary

Enterprise AI agents are being deployed with the same privilege model as backend services: the model decides, the runtime executes. That design fails the moment prompt injection, jailbreaks, or gradual policy erosion turn probabilistic text generation into irreversible API calls, database writes, refunds, or data exports.

### What ACOS is

**ACOS is a governed execution boundary** — a deterministic policy layer between **intent** and **physical side effects**.

| Layer | What it is | In this repository |
|-------|------------|-------------------|
| **Essence (invariant)** | Proposal ≠ execution; cross-step risk accumulates; every deny is auditable and replayable | Protocol + Risk Engine + gateway contract |
| **Core product kernel** | **Policy Gateway** — ingress budget, egress arbitration, tool whitelist, schema guards | `AegisGatewayRuntime`, `egress_gate`, `aegis_egress` |
| **Reference packaging** | **Agent runtime** — a full loop that hosts proposer, gateway, executor, and monitors to prove the contract | `run_agent_os_once()` in `agent_os_runtime.py` |

The open-source repo ships a **reference runtime** to demonstrate the gateway. The long-term product is the **governance layer**, not another workflow engine.

**One-line positioning:** *LangGraph orchestrates. ACOS authorizes.* ACOS does not replace orchestrators; it governs whether a proposed action may execute on real systems.

The language model may propose structured actions. It may not invoke tools, networks, or filesystems directly. Every proposal passes through the Policy Gateway, which maintains cross-step risk state and emits an explicit `APPROVED` / `REJECTED` / `HARD_MELTDOWN` decision before any physical side effect occurs.

This is not “better prompting.” It is **execution governance**: the same class of control you already apply to service accounts, IAM roles, and API gateways—applied to autonomous agent loops.

**What ACOS is not:**

- Not a LangGraph replacement (no graph orchestration, checkpointing, or multi-agent UX as core value)
- Not a generic HTTP reverse proxy (stateful risk, tool criticality, and session budget are first-class)
- Not a certified production appliance in its current form (L1 reference implementation)

**What you get:**

- **Fail-closed execution** — no tool runs without an explicit `APPROVED` decision
- **Cross-temporal risk detection** — incremental escalation (salami-slicing) accumulates state and triggers veto before the final exfiltration step
- **Separated telemetry** — physical blocks vs. model refusals are logged as distinct events, not inferred from output text
- **Budget and loop breakers** — step limits, token pressure, and retry caps terminate runaway sessions

**What this repository is today:** a working Python reference implementation with Streamlit UI, integration tests, and a reproducible egress benchmark. It is suitable for architecture evaluation and controlled pilots—not a substitute for a full security audit before production deployment with real PII or financial assets.

---

## 1. The Problem: Agents Inherit Tool Privilege

Most agent frameworks follow this path:

```text
User prompt → LLM → tool call → API / DB / filesystem → result → LLM → …
```

The model sits in the critical path with direct access to credentials and integrations. Security is layered on afterward: system prompts, output filters, human-in-the-loop for “sensitive” tools, or post-hoc log review.

That model breaks in four predictable ways:

| Failure mode | Why per-step rules miss it |
|--------------|----------------------------|
| **Prompt injection** | Each individual tool call can look benign; the attack is in composition across steps |
| **Salami-slicing escalation** | Step 1: HR vacation query. Step 2: VP salary. Step 3: CEO salary. Step 4: email external. No single step triggers a static blocklist |
| **Runaway loops** | Retries and tool failures compound token cost and widen the attack window |
| **Audit ambiguity** | “The model refused” and “policy blocked execution” look identical in chat logs |

Regulated industries—payments, healthcare records, internal finance, customer PII—cannot treat agent tool access as “just another API integration.” It is **delegated authority with non-deterministic intent formation**. That requires a governance layer with deterministic semantics, not optional guardrails.

---

## 2. Design Principle: Proposal ≠ Execution

ACOS enforces a three-role split:

| Role | Responsibility | Privilege |
|------|----------------|-----------|
| **Intent Proposer** | LLM reasoning; outputs structured intents (`tool_call`, `final_answer`, `terminate`) | No syscall, network, or file I/O |
| **Policy Gateway** | Ingress budgeting, egress arbitration, whitelist and schema enforcement | Approve / reject / hard-stop; no direct tool dispatch |
| **Runtime Executor** | Dispatches approved actions to registered tool handlers | Physical execution only on `APPROVED` |

```text
┌─────────────┐     intent      ┌─────────────────┐    APPROVED only    ┌──────────────┐
│   Intent    │ ──────────────► │  Policy Gateway │ ──────────────────► │   Runtime    │
│  Proposer   │                 │  (Ingress/Egress)│                      │  Executor    │
│   (LLM)     │ ◄── damping ─── │  + Risk Engine  │ ◄── observations ─── │  (tools)     │
└─────────────┘                 └─────────────────┘                      └──────────────┘
                                        ▲
                                        │ drift + budget signals
                                 ┌──────┴──────┐
                                 │  Monitors   │
                                 │ (side-channel)│
                                 └─────────────┘
```

**Non-negotiable rule:** the Runtime Executor is the only component that calls external tools. The LLM never receives a path around the gateway.

This is the same pattern as zero-trust service mesh: identity proposes, policy decides, dataplane executes.

---

## 3. Architecture Overview

### 3.1 Ingress — session bootstrap

On each user request, the Policy Gateway:

1. Normalizes input and issues a **session ID**
2. Allocates a **compute budget** (`max_tokens`, `max_steps`)
3. Runs an **ingress risk scan** (pattern-based threat scoring → `tci_score`, hijack flag)
4. Seeds an **initial tool whitelist** (empty if hijack detected)

High-threat ingress can pre-emptively clear the tool whitelist; egress will hard-stop hijack-flagged sessions.

### 3.2 Per-step sandbox — dynamic tool surface

Before each LLM step, the runtime **re-prunes** the available tool set based on:

- Current execution phase and capability locks
- Goal-drift signals
- Semantic distance to the declared root objective

The whitelist is not static for the life of the session. The agent’s reachable tool surface shrinks as risk rises.

### 3.3 Intent Proposer — structured output only

The LLM writes a JSON intent to an internal trace. A separate adapter maps that trace to a typed `NoesisActionIntent` (implementation name retained in code). Deterministic shortcuts (e.g., reflex responses for trivial input, hardcoded test fixtures) can resolve without an LLM call but still flow through the same governance path when execution is required.

### 3.4 Pre-egress drift check

Before arbitration, a **Drift Monitor** scores:

- **Goal drift** — reasoning and payload deviation from allowed scope
- **Conflict score** — dangerous keywords, unauthorized tool requests, bypass language

Soft drift → corrective feedback to the model, sandbox tightening, step discarded (no egress call).  
Hard drift → session termination (`PFC_MELTDOWN` in telemetry; “unrecoverable drift” in plain terms).

### 3.5 Egress — deterministic arbitration

The **Risk Engine** (`AegisEgressGateway`) computes cross-step effective risk and returns exactly one of:

| Decision | Meaning |
|----------|---------|
| `APPROVED` | Runtime may execute the proposed action |
| `REJECTED` | Blocked; model receives corrective feedback; retry up to limit |
| `HARD_MELTDOWN` | Emergency stop (budget overflow, hijack, step limit in gateway) |
| `OVERRIDE` | Schema reserved; requires external attestation and re-arbitration (not auto-executable) |

Hard guards run before the equation: step budget, hijack flag, payload schema validation, tool whitelist membership.

### 3.6 Side-channel monitors

**Budget Circuit Breaker** listens to per-step pulse telemetry (token usage, retry count, health index derivatives). It can terminate the session independently of the main loop if resource consumption accelerates unsafely or exceeds budget.

Monitors do not replace egress—they provide parallel trip wires.

---

## 4. Request Lifecycle

```text
1. User input
2. Ingress: budget + risk seed + initial whitelist
3. LOOP until resolved:
   a. Phase selection + dynamic sandbox prune
   b. Intent Proposer step (LLM or deterministic shortcut)
   c. Build action request (intent → protocol action type)
   d. Drift Monitor pre-egress scan
   e. Policy Gateway egress arbitration
   f. IF APPROVED → Runtime Executor → inject observation
      IF REJECTED → corrective feedback, retry (max 3)
      IF HARD_MELTDOWN / veto → resolve and halt
   g. Broadcast pulse snapshot to monitors
4. Final output + structured diagnostics to audit log
```

**Action type mapping (intent → execution):**

| Intent | Executed as |
|--------|-------------|
| `tool_call` | Physical tool invocation |
| `final_answer` | Memory write / session resolve (no external call) |
| `terminate` | Semantic stop after approved yield |

---

## 5. Cross-Temporal Risk Arbitration

Static per-step blocklists fail against **salami-slicing**: each step appears low-risk; the attack is the trajectory.

ACOS maintains **stateful risk accumulation** across steps. The egress Risk Engine computes:

**Step 1 — Instantaneous risk** (tool criticality × drift × entropy):

```text
R_kinetic(t) = C_T × (exp(min(κ × D_t × E_t, 10)) − 1)
```

**Step 2 — Accumulated potential** (memory of prior steps):

```text
R_potential(t) = γ × R_potential(t−1) + R_kinetic(t)
```

**Step 3 — Acceleration penalty** (one-way ratchet on rising risk):

```text
ΔR(t) = max(0, R_kinetic(t) − R_kinetic(t−1))
R_effective(t) = R_potential(t) + τ × ΔR(t)
```

**Decision:** if `R_effective(t) ≥ R_MAX` → `REJECTED` (egress veto). No negotiation once the redline is crossed for that step.

### Why this matters operationally

| Property | Industry implication |
|----------|---------------------|
| **Stateful** | Prior “edge” approvals increase pressure on the next step |
| **Non-linear** | Small drift × entropy combinations can spike risk exponentially |
| **Deterministic hot path** | No LLM call in the arbitration math; replayable given same inputs and state |
| **Tool-weighted** | `refund_lookup` carries higher criticality than `query_db` |

### Benchmark: salami-slicing exfiltration (reference implementation)

Simulated trajectory: HR vacation → VP salary → CEO salary → external email.

Under the `balanced` profile, steps 1–3 may pass while risk accumulates; step 4 is **`REJECTED`** when `R_effective` exceeds `R_MAX`.

```bash
python3 auto_test/test_salami_slicing_benchmark.py
```

Example output shape:

```json
{ "step": 2, "intent": "query_vp_salary", "action": "APPROVED", "r_effective": 0.538 }
{ "step": 3, "intent": "query_ceo_salary", "action": "APPROVED", "r_effective": 0.448 }
{ "step": 4, "intent": "email_external", "action": "REJECTED", "r_effective": 7.221 }
```

A framework that only checks the current intent would approve step 4. ACOS vetoes it because the **session history** is part of the decision.

---

## 6. Hard Controls (Beyond the Equation)

| Control | Mechanism | On failure |
|---------|-----------|------------|
| **Step budget** | `max_steps` per session | Timeout / meltdown |
| **Token budget** | Ingress allocation + circuit breaker | `BUDGET_EXHAUSTED` / meltdown |
| **Tool whitelist** | Dynamic sandbox + egress check | `REJECTED` |
| **Payload schema** | Typed `ToolCallPayload` validation | `REJECTED` |
| **Hijack flag** | Ingress threat score ≥ threshold | Empty whitelist → egress `HARD_MELTDOWN` |
| **Retry limit** | 3 cumulative rejections / tool failures | Session resolve with policy reject |
| **Tool timeout** | Infrastructure fault detection | User-facing fallback; no unsafe retry loop |

These are **boolean guards**. The Risk Engine handles **graded, cross-step** threat. Production deployments need both.

---

## 7. Telemetry and Audit

ACOS separates **what the model intended** from **what policy allowed**.

| Field | Purpose |
|-------|---------|
| `semantic_intent_status` | `TOOL_CALL`, `FINAL_ANSWER`, `TERMINATE`, `UNKNOWN` |
| `physical_gate_status` | `NORMAL_EXECUTION`, `EGRESS_VETO`, drift lock, budget meltdown, etc. |
| `termination_cause` | Machine-readable root cause (e.g. `AGENT_OS_EGRESS: R_EFFECTIVE_EXCEEDED`) |
| `effective_risk`, `trust_level` | Per-step risk engine output |
| `tool_invocations` | Structured audit of approved tool calls |

**Rule for SIEM and compliance dashboards:** do not infer physical blocks from model output text (e.g. parsing `[REJECTED]` in chat). Use structured fields.

The Streamlit frontend writes local audit rows; optional Supabase integration persists cloud logs ([setup guide](./supabase_setup.md)).

---

## 8. Deployment Conformance Levels

| Level | Description | Suitable for |
|-------|-------------|--------------|
| **L0** | Semantic screening + logging only; model may still call tools directly | Experiments, non-production |
| **L1** | Full Proposer / Gateway / Executor boundary; deterministic egress arbitration | Governed agent pilots, internal tools |
| **L2** | L1 + infrastructure bypass controls (proxy, mount, syscall filters) | Production with real integrations |
| **L3** | L2 + memory/process isolation (WASM, enclave, sidecar) | High-assurance, regulated workloads |

This repository implements **L1** as an in-process Python runtime. L2/L3 require deployment hardening outside the reference code.

---

## 9. When to Use ACOS

**Strong fit:**

- Agents with access to refunds, payments, customer records, or internal APIs
- Environments requiring **explainable deny decisions** (why was this tool call blocked?)
- Scenarios where prompt injection is an accepted threat model, not a edge case
- Teams building **platform-level** agent governance, not one-off chatbots

**Poor fit:**

- Single-turn Q&A with no tools
- Latency-critical paths where every step adds arbitration overhead (mitigate with deterministic shortcuts for known-safe patterns)
- Teams expecting “secure by default” without configuring tool criticality, `R_MAX`, and whitelists

---

## 10. Implementation Overview

The reference implementation in this repository realizes the L1 conformance model as an in-process Python runtime.

### 10.1 Runtime loop

```text
User input
→ Policy Gateway (ingress): session, budget, risk seed, initial whitelist
→ GlobalStateTensor bootstrap
→ LOOP:
    phase selection + dynamic sandbox prune
    → Intent Proposer step (LLM or deterministic shortcut)
    → NoesisActionIntent
    → Drift Monitor pre-egress scan
    → Policy Gateway (egress): guards + Risk Engine
    → AegisDecision
    → Runtime Executor (if APPROVED) + tool audit
    → observation / damping → state feedback
    → PulseSnapshot → side-channel monitors
→ resolve: final answer | terminate | meltdown
```

**Entry point:** `agent_os_runtime.py` — `run_agent_os_once()`  
**Operator UI:** `frontend/app_os_terminal.py`

### 10.2 What is implemented today

| Capability | Status |
|------------|--------|
| Proposer / Gateway / Executor separation (architectural) | Yes |
| Structured intents (`tool_call`, `final_answer`, `terminate`) | Yes |
| Ingress budget + hijack flag → tool whitelist | Yes |
| Dynamic per-step sandbox pruning | Yes |
| Cross-step egress Risk Engine (`R_effective`) | Yes |
| Hard guards: schema, whitelist, step budget, retry cap (3) | Yes |
| Drift Monitor (inline + pulse) | Yes |
| Budget Circuit Breaker (pulse side-channel) | Yes |
| Tool registry with `criticality_score` + audit records | Yes |
| Structured telemetry (`physical_gate_status`, `termination_cause`) | Yes |
| Integration tests + salami-slicing benchmark | Yes |

### 10.3 Safe public description

> The current ACOS prototype implements a **capability-isolated** agent runtime. The Intent Proposer generates structured intents; all physical execution is mediated by the Policy Gateway. Side-channel monitors observe runtime health through pulse snapshots and can inject corrective feedback or trigger terminal resolution. Some mechanisms—including `OVERRIDE`, ICU enforcement, and physical socket isolation—remain protocol-level or architectural placeholders and must be completed before production use with regulated data.

Full engineering gap list: [implementation_status.md](./implementation_status.md).

---

## 11. Known Gaps (Before Production)

| Gap | Risk | Current state |
|-----|------|---------------|
| **Physical isolation** | Proposer could still use Python I/O if compromised | Architectural only; L2+ deployment required |
| **`OVERRIDE` decision** | Break-glass path undefined | Schema exists; egress never emits it |
| **ICU mode** | High-risk sessions not restricted | Computed tag; no runtime behavior change |
| **Hardcoded ingress budget** | Cannot tier by user/task/risk | Fixed `2000` tokens / `10` steps |
| **Regex ingress scanner** | Misses encoded/indirect injection | Pattern-based amygdala probe |
| **Fragile intent parsing** | Heuristic fallback may misfire | JSON parse + keyword inference |
| **Demo tools** | Not production integrations | Mock `query_db`, `refund_lookup` |
| **Session-only memory** | No governed long-term recall | `GlobalStateTensor` per session |
| **Simplified vitals scoring** | Drift/budget signals are heuristic | Room for stronger momentum/uncertainty |
| **Meltdown taxonomy** | Multiple halt paths, overlapping labels | See implementation_status.md |
| **Test coverage** | Edge paths under-tested | OVERRIDE, ICU, all terminal pulses |
| **Security hygiene** | Sample secrets / local config leakage | Audit `.gitignore` and examples |

**Priority for contributors:** (1) `OVERRIDE` + ICU behavior, (2) strict intent parsing, (3) exit-path tests, (4) secrets hygiene, (5) production connectors, (6) stronger vitals, (7) governed memory.

Treat this codebase as a **reference architecture and evaluation harness**, not a certified production appliance. No third-party security audit has been completed.

---

## 12. Comparison at a Glance

### 12.1 Typical agent frameworks vs ACOS

| | Typical agent framework | ACOS |
|---|------------------------|------|
| Tool invocation | Model → tool directly | Model → intent → policy → tool |
| Per-step safety | Prompts, optional filters | Deterministic gateway + equation |
| Cross-step attacks | Often undetected | Stateful risk accumulation |
| Audit | Chat transcripts | Structured gate status + termination cause |
| Runaway sessions | Manual kill / cost alerts | Step budget + circuit breaker + retry cap |

### 12.2 LangGraph vs ACOS — different problems

LangGraph is a **workflow engine** (how to orchestrate agents). ACOS is an **execution governor** (whether an agent may cause real side effects). They are complementary, not direct substitutes.

```text
LangGraph  = how to route, branch, pause, and coordinate agents
ACOS       = whether a proposed action may execute on real systems
```

| Dimension | LangGraph | ACOS (this reference implementation) |
|-----------|-----------|--------------------------------------|
| **Orchestration** | Strong: conditional edges, parallel nodes, subgraphs, handoffs | Weak: single linear step loop in `run_agent_os_once()` |
| **Execution governance** | Weak by default: `ToolNode` invokes tools directly | Strong: Policy Gateway + cross-step Risk Engine |
| **Checkpoint / human-in-the-loop** | Built-in pause, resume, thread persistence | Not implemented; session ends when loop resolves |
| **Multi-agent patterns** | Documented supervisor / handoff / swarm patterns | Not implemented; one proposer per session today |
| **Ecosystem** | Large: LangChain tools, integrations, LangSmith | Small: mock tools, Streamlit UI, internal tests |
| **Maturity** | Widely adopted for agent demos and products | L1 prototype; no third-party security audit |
| **Latency** | Shorter path when tools run directly | Higher: drift scan + egress + audit every step |
| **Salami-slicing / cross-step veto** | No session-level `R_effective` by default | Core feature via stateful Risk Engine |
| **Auditable physical deny** | Must be inferred from logs | `physical_gate_status`, `termination_cause` |

### 12.3 Where ACOS is weaker than LangGraph

1. **Orchestration** — the largest gap. No first-class support for branching workflows, parallel specialists, dynamic routing, or approval gates.
2. **Developer experience** — fewer examples, integrations, and debugging tooling compared to the LangGraph / LangSmith stack.
3. **State persistence** — no checkpoint API for long-running or human-interrupted tasks.
4. **Multi-agent** — no sub-agent roles, shared-handoff protocol, or per-role tool surfaces in the current codebase.
5. **Implementation completeness** — `OVERRIDE`, ICU enforcement, strict intent parsing, and production connectors remain open (see Section 11).

### 12.4 Where ACOS is stronger than LangGraph

1. **Proposal ≠ execution** — hard boundary; the model cannot call APIs without an explicit `APPROVED` decision.
2. **Cross-temporal risk** — incremental escalation accumulates in session state; the salami-slicing benchmark demonstrates veto on the exfiltration step.
3. **Separated telemetry** — physical policy blocks are not confused with model refusals in chat text.
4. **Deterministic egress hot path** — arbitration math is replayable without LLM calls in the decision path.
5. **Tool criticality** — `criticality_score` feeds the Risk Engine; read vs act vs export are weighted differently.

### 12.5 Multi-agent scenarios

Multi-agent needs do **not** automatically require LangGraph. The clean pattern for governed multi-agent is:

```text
Thin supervisor (routing only)
    → multiple Intent Proposers (role-specific prompts + tool visibility)
    → single Policy Gateway (shared session risk state)
    → single Runtime Executor
```

LangGraph may implement the supervisor layer when workflows are complex (parallel branches, frequent human interrupts). ACOS must still own the execution choke point. Letting each sub-agent bind and invoke tools independently defeats the governance model.

### 12.6 When to use which

| Primary pain | Better fit |
|--------------|------------|
| Complex workflow, multi-agent coordination, fast demo | LangGraph (or similar orchestrator) |
| Tool privilege abuse, prompt injection, cross-step exfiltration, explainable deny | ACOS |
| Both | Thin orchestration + ACOS gateway on every side-effecting step (higher integration cost) |

For a single governed agent loop, **adding LangGraph often duplicates orchestration** already present in `run_agent_os_once()`. Prefer extending ACOS before bolting on a second workflow engine unless team or product constraints require LangGraph specifically.

---

## 13. Getting Started

| Resource | Link |
|----------|------|
| Implementation gaps (engineering) | [Implementation Status](./implementation_status.md) |
| Code walkthrough | [ACOS Code Logic](./acos_logic_flow.md) |
| Execution contract (RFC draft) | [Aegis CCB Zero-Trust Execution Contract](./aegis_ccb_zero_trust_execution_contract_rfc_draft.md) |
| Quick start | [README](../README.md) |
| Salami-slicing benchmark | `python3 auto_test/test_salami_slicing_benchmark.py` |
| Full test suite | `python3 auto_test/run_all.py` |

---

## Appendix A: Internal Name → Industry Term

For readers reviewing the source code:

| Code / legacy name | Industry term |
|--------------------|---------------|
| Noesis | Intent Proposer |
| Aegis Ingress / Egress | Policy Gateway (ingress / egress) |
| `AegisEgressGateway` | Risk Engine |
| ACC Monitor | Drift Monitor |
| Hypothalamus | Budget Circuit Breaker |
| Basal Ganglia | Deterministic shortcut router |
| PFC Executor | LLM step executor |
| `logical_entropy` | Reasoning instability score |
| `PulseSnapshot` | Per-step telemetry heartbeat |

---

## Appendix B: Risk Equation Constants

Tunable per deployment profile (`strict`, `balanced`, `research` in benchmark):

| Symbol | Meaning | Typical role |
|--------|---------|--------------|
| `κ` (kappa) | Sensitivity to drift × entropy product | Higher → faster veto |
| `γ` (gamma) | Decay of accumulated risk | Lower → longer memory of prior steps |
| `τ` (tau) | Acceleration multiplier | Higher → penalizes rapid risk spikes |
| `R_MAX` | Hard redline | Lower → stricter |
| `C_T` | Tool criticality | Per-tool classification (read vs. act vs. export) |

---

## Legal Notice

This whitepaper and the accompanying reference implementation are provided **as-is** for architecture evaluation and research. They do not constitute a security certification. Deployments handling regulated data require independent risk assessment, penetration testing, and operational controls appropriate to your jurisdiction and industry.

**Licensing:** Reference code is under [MIT License](../LICENSE). This document and related specifications are under [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). See [LICENSE.md](./LICENSE.md) for details.

---

*ACOS — Governed execution for agents that touch real systems.*
