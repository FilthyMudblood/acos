"""
Executable inventory for core_aegis module lifecycle management.

Use this file as the single source of truth when deciding:
- what belongs to active aegis governance plane
- what crosses plane boundaries and should be moved out
- what legacy modules are done vs pending
"""

from typing import Dict, List


ACTIVE_AEGIS_MODULES: List[str] = [
    "gateway_runtime.py",
    "ingress_gate.py",
    "egress_gate.py",
    "aegis_egress.py",
    "amygdala_policy.py",
    "config.py",
]

CROSSPLANE_TO_MOVE_MODULES_PENDING: Dict[str, str] = {}

CROSSPLANE_TO_MOVE_MODULES_DONE: Dict[str, str] = {
    "types.py": "protocol_schema.py",
}

ARCHIVED_MODULES_DONE: Dict[str, str] = {
    "unified_acc.py": "z_archived/core_aegis_compat/unified_acc.py",
}

LEGACY_TO_KILL_MODULES_PENDING: List[str] = []

LEGACY_TO_KILL_MODULES_DONE: List[str] = [
    "trust_evaluator.py",
    "sensory_probe.py",
    "telemetry.py",
    "egress_policy_gateway.py",
]


def get_module_inventory() -> Dict[str, object]:
    return {
        "active_aegis": list(ACTIVE_AEGIS_MODULES),
        "crossplane_to_move_pending": dict(CROSSPLANE_TO_MOVE_MODULES_PENDING),
        "crossplane_to_move_done": dict(CROSSPLANE_TO_MOVE_MODULES_DONE),
        "archived_done": dict(ARCHIVED_MODULES_DONE),
        "legacy_to_kill_pending": list(LEGACY_TO_KILL_MODULES_PENDING),
        "legacy_to_kill_done": list(LEGACY_TO_KILL_MODULES_DONE),
    }


def get_module_lifecycle(module_name: str) -> str:
    normalized = str(module_name or "").strip()
    short_name = normalized.split(".")[-1]
    if not short_name.endswith(".py"):
        short_name = f"{short_name}.py"

    if short_name in ACTIVE_AEGIS_MODULES:
        return "active_aegis"
    if short_name in CROSSPLANE_TO_MOVE_MODULES_PENDING:
        return "crossplane_to_move_pending"
    if short_name in CROSSPLANE_TO_MOVE_MODULES_DONE:
        return "crossplane_to_move_done"
    if short_name in ARCHIVED_MODULES_DONE:
        return "archived_done"
    if short_name in LEGACY_TO_KILL_MODULES_PENDING:
        return "legacy_to_kill_pending"
    if short_name in LEGACY_TO_KILL_MODULES_DONE:
        return "legacy_to_kill_done"
    return "untracked"
