# Project Conventions

Keep rules short and enforceable. Prefer "do X" over abstract wording.

## Naming
- Use descriptive module names by domain (for example: `core_aegis`, `core_noesis`).
- Prefer explicit function names that reflect side effects (`save_*`, `load_*`, `validate_*`).

## Layering
- UI code stays under `frontend/`.
- Core domain logic stays under `core_*` and should not depend on UI modules.
- State containers stay under `agentos_state/` and avoid presentation concerns.
- Aegis egress arbitration must stay equation-only (`core_aegis/egress_gate.py` + `core_aegis/aegis_egress.py`), without parallel heuristic policy paths.

## Error Handling
- Raise specific exceptions with actionable messages.
- Avoid silent fallbacks unless there is a documented reason in this memo.

## Logging and Debugging
- Log decision points, not every line of execution.
- Include enough context in logs to reproduce the issue quickly.

## Testing and Verification
- For behavior changes, add or update at least one verification step.
- For bug fixes, include a regression check path in `CHECKLIST.md` or `KNOWN_ISSUES.md`.
- Remove dead code with no active runtime call chain; do not keep compatibility shims by default unless there is a documented owner and use case.
