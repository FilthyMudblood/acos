# Runtime Change Log (2026-04-30)

## Scope

Stabilization and architecture cleanup for AC-OS control loop:

- sandbox pruning + capability lock alignment
- egress equation hard-stop wiring
- hypothalamus warm-up and activation thresholds
- test structure consolidation under `auto_test/`

## Key Parameter Baseline

- `BASE_PRUNING_THRESHOLD = 0.10`
- `HARD_DRIFT_THRESHOLD = 0.92`
- `MAX_CONTEXT_TOOLS = 8`
- Hypothalamus warm-up:
  - `grace_period_tokens = 200`
  - `meltdown_activation_tokens = max(400, base_budget * 0.2)`

## Behavioral Outcomes

- Runtime no longer depends on `GlobalStateTensor.root_objective` existing.
- Egress equation veto triggers hard stop path:
  - `AGENT_OS_EGRESS_VETO_MELTDOWN`
- Phase-driven flow (`READ -> ACTION`) added via execution feedback.
- Over-pruning guard added to prevent normal multi-tool deadlock.

## Test Status

- `auto_test/test_aegis_egress.py`: pass
- `auto_test/test_agent_os_runtime_egress_veto.py`: pass
- `auto_test/test_agent_os_e2e.py`: full matrix pass in validated run

## Utility

- Added one-command runner:
  - `python auto_test/run_all.py`
  - `python auto_test/run_all.py --include-e2e`
