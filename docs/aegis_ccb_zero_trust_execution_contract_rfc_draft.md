# Aegis CCB Zero-Trust Execution Contract

- Status: Draft
- Version: v1.0
- Scope: Execution boundary, cross-temporal arbitration, metabolic intervention, and telemetry semantics for AC-OS compatible runtimes.

## 0. Normative Language

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**, **MAY**, and **OPTIONAL** in this document are to be interpreted as described by RFC 2119 and RFC 8174.

## 1. Purpose

This RFC defines the non-bypassable execution contract between Noesis (proposer), Aegis (arbiter), and the Runtime Kernel (executor).
The design goal is deterministic physical governance over probabilistic cognition.

## 2. Terminology (Normative)

- **Noesis**: The cognition plane that proposes intents.
- **Aegis**: The governance plane that arbitrates intents.
- **ACC (Anterior Cingulate Cortex)**: A unified monitoring organ functioning independently of execution flow, responsible for real-time assessment of logical entropy and intent conflict.
- **Runtime Kernel**: The sole physical executor for tools, network, and filesystem actions.
- **Step-clock**: A monotonic internal proposal counter used for deterministic replay and state progression, fully decoupled from wall-clock time.
- **Physical veto**: A governance denial that strictly blocks physical execution.
- **Semantic terminate**: A Noesis-side logical refusal or termination intent.
- **External authority**: A non-Noesis principal (for example a human operator, signed policy service, or break-glass controller) that is authorized to issue override attestations.

## 3. Execution Boundary and Isolation

### 3.1 Sovereignty Contract

Any conforming architecture MUST enforce all of the following:

1. **Noesis MUST NOT** own direct syscall, network, or file execution privileges. It **MAY ONLY** emit structured `Intent` messages through stdout or memory pipe.
2. **Aegis MUST** run as an isolated process or restricted sandbox and perform deterministic arbitration over intents.
3. **Runtime Kernel MUST** be the only entity with network I/O, file I/O, and process spawn privileges. Runtime **SHALL ONLY** execute instructions marked as `APPROVED` by Aegis.

### 3.2 Bypass Prohibition

For L2+ compliance deployments, infrastructure controls (for example proxy policies, mount policies, and syscall filters) **MUST** reject all requests not routed through the Aegis-authorized execution path.

## 4. Execution Lifecycle and Deterministic Hot Path

Implementations **MAY** use cyclic execution topology (for example finite-state-machine loop topology), but **MUST** enforce strict boundaries between probabilistic evaluation and deterministic enforcement.

### 4.1 Capability-Gated Pruning

Pre-egress tool pruning **MUST NOT** rely solely on semantic similarity, because semantic similarity does not imply behavioral relevance. Behavioral capability locks **MUST** be evaluated as deterministic boolean operators in the hot path.

### 4.2 Corrective Damping

ACC and PFC damping interventions **MUST** support immediate short-circuit semantic retries without triggering physical egress arbitration.

## 5. Deterministic Time Semantics

### 5.1 Step-clock Requirement

Arbitration-critical decay, state transitions, and history accumulation **MUST** use Step-clock and **MUST NOT** rely on wall-clock time.

### 5.2 Replayability Requirement

Given an identical Step-clock sequence, inputs, constants, and persisted governance state, arbitration output **MUST** be absolute, deterministic, and replayable.

### 5.3 Initialization and Recovery Requirement

To guarantee replay closure, implementations **MUST** define and persist explicit initial and recovery state:

- At `t=0`: `R_kinetic(0)=0`, `R_potential(0)=0`, `R_effective(0)=0`.
- At `t=0`: trust tags **SHALL** be initialized to implementation-defined defaults and recorded in state.
- After each arbitration step (including veto), state for `t+1` **MUST** be committed atomically before the next step begins.
- On crash/restart, runtime **MUST** resume from the latest committed Step-clock state. If no state exists, it **MUST** restart from the `t=0` baseline.

## 6. Cross-Temporal Decision Engine (Normative)

### 6.1 Stateful Arbitration Requirement

Egress arbitration **MUST** preserve cross-step risk state. At minimum, it **SHALL** persist:

- Prior kinetic risk term(s)
- Cross-temporal accumulated risk (potential energy)
- Last effective risk and trust tags
- Last emitted arbitration status

### 6.2 Output Contract

Arbitration **SHALL** output exactly one of the following:

- `APPROVED`
- `REJECTED`
- `OVERRIDE`
- `HARD_MELTDOWN`

Runtime **MUST NOT** perform any physical execution unless status is strictly `APPROVED`.

### 6.3 Status Semantics and Closure

To avoid state ambiguity, implementations **MUST** apply the following meaning:

- `APPROVED`: deterministic egress allow decision for the current intent.
- `REJECTED`: deterministic egress veto for the current intent.
- `OVERRIDE`: escalation-required state; indicates external authority attestation is required. `OVERRIDE` alone is non-executable and **MUST NOT** trigger physical execution of the current intent.
- `HARD_MELTDOWN`: emergency metabolic trip state with forced model channel severance and task isolation.

If an external authority grants a break-glass action, it **MUST** be represented as a new intent carrying signed override evidence and re-enter arbitration; direct execution from an `OVERRIDE` status is forbidden.

## 7. Egress Arbitration and Absolute Risk Quantification

### 7.1 Principle

Aegis egress **MUST** compute cross-temporal effective risk `R_effective(t)` before any physical action. Heuristic linear weighted scoring **MUST NOT** be the primary source of truth in production Equation Profile deployments.

### 7.2 Inputs and Constants

Normalized inputs bounded in `[0, 1]`:

- `D_t`: Goal drift score (ACC-derived)
- `E_t`: Logical entropy score (ACC-derived)
- `C_T`: Tool criticality

Physical constants:

- `kappa`: sensitivity constant, `kappa >= 0`
- `gamma`: temporal decay or memory factor, `0 <= gamma <= 1`
- `tau`: momentum multiplier, `tau >= 0`
- `R_MAX`: hard physical redline, `R_MAX > 0`

### 7.3 Aegis Equation (Normative Profile)

Step 1: Instantaneous kinetic risk

`R_kinetic(t) = C_T * (exp(min(kappa * D_t * E_t, 10.0)) - 1)`

Step 2: Temporal potential accumulation

`R_potential(t) = gamma * R_potential(t-1) + R_kinetic(t)`

Step 3: Gradient momentum (one-way ratchet)

`DeltaR(t) = max(0, R_kinetic(t) - R_kinetic(t-1))`

Step 4: Final collapse

`R_effective(t) = R_potential(t) + tau * DeltaR(t)`

### 7.4 Hard Constraints

- If `R_effective(t) < R_MAX`, system **MAY** allow execution.
- If `R_effective(t) >= R_MAX`, system **MUST** veto immediately and emit damping or isolation signals.
- No silent negotiation path is allowed once the hard redline is crossed for the current step.

### 7.5 Deterministic Mapping to Arbitration Status

For each intent step, exactly one status **MUST** be emitted:

1. If metabolic hard-trip condition is true, emit `HARD_MELTDOWN`.
2. Else if explicit external authority override challenge is required by policy, emit `OVERRIDE`.
3. Else if `R_effective(t) >= R_MAX`, emit `REJECTED`.
4. Else emit `APPROVED`.

This precedence order is normative and **MUST** be applied identically in replay.

### 7.6 Engineering Contracts

1. **Deterministic hot path**: The egress hot path **MUST** only use local mathematics and state operations. It **MUST NOT** initiate network requests, database queries, or LLM calls.
2. **Mandatory state commit**: Both allow and veto paths **MUST** commit updated risk state for `t+1`.
3. **Numerical safety**: Because `kappa >= 0`, `D_t in [0, 1]`, and `E_t in [0, 1]`, exponent input is non-negative and **MUST** be upper-bounded to avoid overflow (for example `min(exponent, 10.0)`). All non-finite arithmetic results (`NaN`, `+Inf`, `-Inf`) **MUST** fail closed to `REJECTED` or `HARD_MELTDOWN` according to policy.

## 8. Metabolic Constraint and Hypothalamus Intervention

### 8.1 Token Derivative Monitoring

The metabolic guard **MUST** track absolute resource consumption rate `h(t)` and a Step-clock-based discrete acceleration term:

`a_h(t) = h(t) - 2 * h(t-1) + h(t-2)`

Continuous-time derivatives (`d^2h/dt^2`) are non-normative explanatory notation only. Enforcement **MUST** use Step-clock discrete form.

For cold-start steps where `t < 2`, runtime **MUST** define `a_h(t) = 0` or apply an implementation-defined first-order velocity-only check. Acceleration-based meltdown trigger evaluation **SHALL ONLY** be enforced for `t >= 2`.

### 8.2 Hard Meltdown Trigger

When `a_h(t)` exceeds the configured deterioration threshold, the system **MUST**:

1. Trigger `HARD_MELTDOWN` and forcefully sever the model execution channel.
2. Flush the affected task buffer and context.
3. Emit an auditable `Metabolic_Exhaustion_Error`.

The system **MUST NOT** allow autonomous self-restart of the constrained task without external authority intervention.

## 9. Telemetry Separation Contract (Normative)

To prevent telemetry pollution, systems **MUST** strictly separate physical and semantic outcomes in logging and monitoring architecture.

### 9.1 Required Fields

- `physical_gate_status`:
  - `NORMAL_EXECUTION`
  - `PFC_PRUNING_LOCK`
  - `ACC_SOFT_DAMPING`
  - `HYPOTHALAMUS_MELTDOWN`
  - `EGRESS_VETO`

- `semantic_intent_status`:
  - `TOOL_CALL`
  - `FINAL_ANSWER`
  - `TERMINATE`
  - `UNKNOWN`

- `termination_cause`:
  - Implementation-defined root-cause string.
  - Examples:
    - `NOESIS_TERMINATE: SQL_INJECTION_HEURISTIC`
    - `NOESIS_TERMINATE: NO_VALID_INTENT_EXTRACTED`
    - `AEGIS_EGRESS: R_EFFECTIVE_EXCEEDED`

### 9.2 Mandatory Status Mapping

Structured telemetry **MUST** map arbitration output as follows:

- `APPROVED` -> `physical_gate_status=NORMAL_EXECUTION`
- `REJECTED` -> `physical_gate_status=EGRESS_VETO`
- `HARD_MELTDOWN` -> `physical_gate_status=HYPOTHALAMUS_MELTDOWN`
- `OVERRIDE` -> `physical_gate_status=EGRESS_VETO` until a separately authorized re-arbitrated intent becomes `APPROVED`

### 9.3 Interpretation Rule

Monitoring systems **MUST NOT** infer physical veto status solely from output text tokens (for example parsing `[REJECTED]` from model output). Dashboards and audit logs **SHALL** prioritize structured telemetry fields over textual previews.

## 10. Conformance Levels

- `L0` (Semantic Safety): Supports semantic screening and logging, but does not enforce full physical non-bypass guarantees.
- `L1` (Governed Execution): Enforces Noesis/Aegis/Runtime boundary and deterministic egress arbitration.
- `L2` (Infrastructure Hardened): Meets L1 plus infrastructure bypass prohibition controls defined in Section 3.2.
- `L3` (Hardware or Embedded Enclave): Meets L2 plus strict physical memory isolation (for example WASM runtime isolation or native enclave segmentation), with optional offline execution guarantees where required by deployment policy.

Claims of `L1+`, `L2+`, or `L3` compliance **MUST** document runtime evidence for boundary isolation, deterministic replay checks, and telemetry separation. `L3` claims **SHOULD** additionally document memory-isolation attestation and offline-mode behavior constraints when applicable.

## 11. Security Rationale

This contract upgrades AI safety from semantic patching to absolute physical determinism:

- Noesis cannot directly execute physical actions.
- Aegis enforces deterministic mathematical arbitration.
- Runtime executes only mathematically approved actions.
- Metabolic breakers forcefully terminate runaway acceleration trajectories.
- Telemetry preserves strict separation between physical vetoes and semantic negotiations.

## 12. Release Notes (v0.3 -> v1.0)

- Formalized deterministic replay closure with explicit initialization and crash recovery requirements.
- Added closed arbitration semantics for `APPROVED`, `REJECTED`, `OVERRIDE`, and `HARD_MELTDOWN`, including non-executable `OVERRIDE`.
- Hardened risk hot path with deterministic status precedence and non-finite fail-closed requirements.
- Migrated metabolic acceleration semantics to Step-clock discrete form and added cold-start protections for `t < 2`.
- Added mandatory telemetry status mapping and interpretation guardrails against text-token inference.
- Expanded conformance model from `L0-L2` to `L0-L3`, including hardware or enclave isolation expectations for `L3`.
