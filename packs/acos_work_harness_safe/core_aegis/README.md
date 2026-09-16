# core_aegis Module Map

This package is split into two conceptual layers:

## Active Aegis Path (Primary)

- `gateway_runtime.py`: current ingress+egress orchestrator (`AegisGatewayRuntime`)
- `ingress_gate.py`: ingress sanitization and budget issuance
- `egress_gate.py`: current egress gate (equation-driven risk veto)
- `aegis_egress.py`: non-linear egress arbitration equation
- `amygdala_policy.py`: amygdala-style intent/risk probe
- `config.py`: aegis governance and egress configuration constants

## Legacy / Peripheral Surface

- moved out / consolidated:
  - `types.py` -> `protocol_schema.py`
  - `unified_acc.py` -> `z_archived/core_aegis_compat/unified_acc.py`
- physically removed:
  - `sensory_probe.py`
  - `telemetry.py`
  - `trust_evaluator.py`
  - `egress_policy_gateway.py`
- compatibility shims (`gateway_kernel.py`, `kernel.py`) have been moved to `z_archived/core_aegis_compat/`

## Naming Convention

- Prefer `*runtime.py` for active orchestration modules.
- Prefer `*policy.py` for detection/classification logic.
- Keep `*kernel.py` only as compatibility shims; avoid new code there.

## Inventory Source of Truth

- `module_inventory.py` contains executable lifecycle groups:
  - `active_aegis`
  - `crossplane_to_move_pending/done`
  - `legacy_to_kill_pending/done`
- Prefer updating `module_inventory.py` first before any cleanup/removal PR.
