#!/usr/bin/env python3
"""
Work recipe: Copilot (or any host) proposes structured intents;
ACOS harness authorizes; a deterministic "data agent" runs only if APPROVED.

Run from pack root:
  python examples/copilot_intent_harness.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import Any, Dict, Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core_aegis.gateway_runtime import AegisGatewayRuntime
from core_runtime.execute import execute_approved
from core_runtime.intent_helpers import is_executable, make_tool_call_request
from core_runtime.runtime_stack import PhysicalToolRegistry, ToolSpec
from protocol_schema import AegisIngressPayload, DecisionStatus


async def run_report(report_id: str, customer_scope: str = "self") -> Dict[str, Any]:
    return {
        "report_id": report_id,
        "customer_scope": customer_scope,
        "rows": 42,
        "status": "ok",
        "note": "deterministic pipeline stub — replace with your data agent",
    }


async def export_customer_csv(scope: str) -> Dict[str, Any]:
    return {"scope": scope, "exported": True, "warning": "high-criticality stub"}


def build_registry() -> PhysicalToolRegistry:
    return PhysicalToolRegistry(
        [
            ToolSpec(
                name="run_report",
                handler=run_report,
                capabilities={"read", "report"},
                criticality_score=0.30,
            ),
            ToolSpec(
                name="export_customer_csv",
                handler=export_customer_csv,
                capabilities={"export"},
                criticality_score=0.95,
            ),
        ]
    )


async def governed_step(
    aegis: AegisGatewayRuntime,
    registry: PhysicalToolRegistry,
    ingress: AegisIngressPayload,
    *,
    step: int,
    tool_name: str,
    params: Dict[str, Any],
    reasoning: str,
    logical_entropy: float = 0.1,
    acc_conflict_score: Optional[float] = 0.05,
) -> Dict[str, Any]:
    request = make_tool_call_request(
        session_id=ingress.session_id,
        step_count=step,
        tool_name=tool_name,
        parameters=params,
        reasoning_trajectory=reasoning,
        logical_entropy=logical_entropy,
        acc_conflict_score=acc_conflict_score,
        acc_entropy_score=logical_entropy,
    )
    decision = aegis.egress_gate(request, ingress)
    out: Dict[str, Any] = {
        "session_id": ingress.session_id,
        "step": step,
        "tool": tool_name,
        "status": decision.status.value,
        "executed": False,
        "result": None,
        "reason": decision.rejection_reason or decision.penalty_log,
    }
    if not is_executable(decision) or decision.status != DecisionStatus.APPROVED:
        return out
    result, _audit = await execute_approved(decision, registry)
    out["executed"] = bool(result.ok)
    out["result"] = result.model_dump() if hasattr(result, "model_dump") else result
    return out


async def main() -> None:
    registry = build_registry()
    aegis = AegisGatewayRuntime(
        default_tools=registry.get_tool_names(),
        tool_criticality_scores=registry.as_criticality_map(),
    )

    # One Staff session — keep the same ingress so cross-step risk can accumulate
    ingress = aegis.ingress_gate("Staff: monthly KPI then export")
    print(f"[ingress] session={ingress.session_id} tools={ingress.allowed_tools}")

    # Copilot would fill tool_name/params; here they are hardcoded intents
    print(
        await governed_step(
            aegis,
            registry,
            ingress,
            step=1,
            tool_name="run_report",
            params={"report_id": "monthly_kpi", "customer_scope": "self"},
            reasoning="Staff asked for monthly KPI report",
            logical_entropy=0.10,
            acc_conflict_score=0.05,
        )
    )
    print(
        await governed_step(
            aegis,
            registry,
            ingress,
            step=2,
            tool_name="export_customer_csv",
            params={"scope": "all_customers"},
            reasoning="Follow-up export all customers",
            logical_entropy=0.85,
            acc_conflict_score=0.80,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
