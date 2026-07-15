# Architecture Decisions

Use this file for long-lived technical decisions (ADR-lite style).

## Decision Template
- ID: DEC-YYYYMMDD-XX
- Title:
- Status: proposed | accepted | deprecated | superseded
- Context:
- Decision:
- Alternatives considered:
- Consequences:
- Rollback plan:
- References:

---

## Example
- ID: DEC-20260425-01
- Title: Keep runtime orchestration logic in `agent_os_runtime.py`
- Status: accepted
- Context: Several features need shared lifecycle and state transitions.
- Decision: Centralize orchestration in one runtime entry module and keep adapters thin.
- Alternatives considered: Split orchestration into each feature module.
- Consequences: Easier tracing and debugging, but runtime file grows faster.
- Rollback plan: Extract orchestration services when file size and coupling exceed team thresholds.
- References: docs/agentos_architecture.md

---

- ID: DEC-20260714-01
- Title: Product surface is Policy Gateway SDK; runtime is reference packaging
- Status: accepted
- Context:
  - Integrating ACOS via `run_agent_os_once()` forces a second orchestrator alongside LangGraph.
  - Differentiation is authorize/audit/execute, not graph routing.
- Decision:
  - Public integrator surface is `ingress_gate` / `egress_gate` / `execute_approved` (+ protocol types + `PhysicalToolRegistry`).
  - `run_agent_os_once()` remains the reference loop (Path B), not the default embedding API (Path A).
  - Spec lives in `docs/integration_guide.md`; public `execute_approved` lives in `core_runtime/execute.py` (fail-closed on non-APPROVED).
- Alternatives considered:
  - Ship only standalone runtime and ask users to fork the loop.
  - Build a full LangGraph-compatible framework inside ACOS.
- Consequences:
  - Clear ownership vs LangGraph; smaller public API; reference runtime can thin over time.
  - Temporary dual call paths until execute is extracted.
- Rollback plan:
  - Keep private dispatcher; document Path B only if Path A adoption fails.
- References:
  - docs/integration_guide.md
  - docs/WHITEPAPER.md §12
  - core_aegis/gateway_runtime.py

---

- ID: DEC-20260430-02
- Title: Retire heuristic egress stack; enforce equation-only arbitration
- Status: accepted
- Context:
  - Early Aegis relied on regex/pattern scans, bigram-style text checks, and linear risk weighting.
  - After AC-OS architecture upgrade, Noesis is a constrained proposer and Aegis is a deterministic arbiter.
  - Legacy heuristic modules created duplicate governance paths and increased maintenance entropy.
- Decision:
  - Keep egress sovereignty on `core_aegis/egress_gate.py + core_aegis/aegis_egress.py` only.
  - Remove legacy heuristic modules from active code (including archived compatibility links when they become dead).
  - Treat modules with no active runtime call chain as dead code and remove them instead of preserving soft compatibility by default.
- Alternatives considered:
  - Keep legacy modules as fallback.
  - Keep archive modules importable/compilable indefinitely.
- Consequences:
  - Governance path is single-source and mathematically deterministic.
  - Fewer ghost dependencies and less risk of accidental policy bypass.
  - Historical behavior is no longer recoverable via direct module reuse.
- Rollback plan:
  - Reintroduce fallback only if a production incident proves equation-only path is insufficient, and gate it behind an explicit runtime flag.
- References:
  - docs/ac_os_core_architecture_manifest_v1_2.yaml
  - core_aegis/egress_gate.py
  - core_aegis/aegis_egress.py
