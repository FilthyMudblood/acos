#!/usr/bin/env python3
"""
Recipe: LangGraph-style governed tool node over the ACOS Policy Gateway SDK.

Pattern:
  graph / host owns routing
  ACOS owns authorize + physical execute

Does NOT use LangGraph's stock ToolNode (that would bypass the gateway).

Install (optional, only if you want real StateGraph wiring at the bottom):
  pip install langgraph

Run from repo root (no LangGraph required for the default demo):
  python examples/langgraph_governed_tool.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import Any, Dict, Optional, TypedDict

# Allow `python examples/...` from repo root or examples/
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core_aegis.gateway_runtime import AegisGatewayRuntime
from core_runtime.execute import execute_approved
from core_runtime.intent_helpers import is_executable, make_tool_call_request
from core_runtime.runtime_stack import PhysicalToolRegistry, ToolSpec
from protocol_schema import AegisIngressPayload, DecisionStatus


# ---------------------------------------------------------------------------
# Demo tools (replace with real connectors in production)
# ---------------------------------------------------------------------------
async def query_orders(order_id: str) -> Dict[str, Any]:
    return {"order_id": order_id, "status": "paid", "amount": 128.5}


async def export_csv(scope: str) -> Dict[str, Any]:
    return {"exported_rows": 5000, "scope": scope, "destination": "s3://exfil"}


def build_demo_registry() -> PhysicalToolRegistry:
    return PhysicalToolRegistry(
        [
            ToolSpec(
                name="query_orders",
                handler=query_orders,
                capabilities={"read", "query"},
                criticality_score=0.25,
            ),
            ToolSpec(
                name="export_csv",
                handler=export_csv,
                capabilities={"export"},
                criticality_score=0.95,
            ),
        ]
    )


# ---------------------------------------------------------------------------
# LangGraph-shaped state + nodes (same signature you wire into StateGraph)
# ---------------------------------------------------------------------------
class GraphState(TypedDict, total=False):
    user_input: str
    session_id: str
    step: int
    ingress: AegisIngressPayload
    aegis: AegisGatewayRuntime
    registry: PhysicalToolRegistry
    tool_name: str
    params: Dict[str, Any]
    reasoning: str
    logical_entropy: float
    acc_conflict_score: float
    blocked: bool
    physical_gate_status: str
    penalty_log: Optional[str]
    tool_result: Optional[Dict[str, Any]]
    tool_audit: Optional[Dict[str, Any]]


def open_session_node(state: GraphState) -> GraphState:
    """Session start: ingress_gate once per conversation."""
    aegis = state["aegis"]
    ingress = aegis.ingress_gate(state["user_input"])
    return {
        "ingress": ingress,
        "session_id": ingress.session_id,
        "step": 0,
    }


async def governed_tool_node(state: GraphState) -> GraphState:
    """
    Side-effecting step: build intent → egress → execute_approved only if APPROVED.

    Drop this node into LangGraph instead of ToolNode.
    """
    step = int(state.get("step") or 0) + 1
    entropy = float(state.get("logical_entropy") or 0.0)
    conflict = state.get("acc_conflict_score")
    request = make_tool_call_request(
        session_id=state["session_id"],
        step_count=step,
        tool_name=state["tool_name"],
        parameters=state.get("params") or {},
        reasoning_trajectory=state.get("reasoning") or "graph tool proposal",
        logical_entropy=entropy,
        acc_conflict_score=float(conflict) if conflict is not None else None,
        acc_entropy_score=entropy,
    )
    decision = state["aegis"].egress_gate(request, state["ingress"])
    if not is_executable(decision):
        return {
            "step": step,
            "blocked": True,
            "physical_gate_status": decision.status.value,
            "penalty_log": decision.penalty_log or decision.rejection_reason,
            "tool_result": None,
            "tool_audit": None,
        }

    result, audit = await execute_approved(decision, state["registry"])
    return {
        "step": step,
        "blocked": False,
        "physical_gate_status": DecisionStatus.APPROVED.value,
        "penalty_log": None,
        "tool_result": result.model_dump() if result else None,
        "tool_audit": audit,
    }


# ---------------------------------------------------------------------------
# Minimal host loop (stands in for LangGraph when the package is absent)
# ---------------------------------------------------------------------------
async def run_demo() -> None:
    registry = build_demo_registry()
    aegis = AegisGatewayRuntime(
        default_tools=registry.get_tool_names(),
        tool_criticality_scores=registry.as_criticality_map(),
    )

    state: GraphState = {
        "user_input": "Look up order then export payroll for all staff",
        "aegis": aegis,
        "registry": registry,
    }
    state.update(open_session_node(state))
    print(f"[ingress] session_id={state['session_id']} tools={state['ingress'].allowed_tools}")

    # Step 1 — low-criticality read + calm ACC signals (typically APPROVED)
    state.update(
        {
            "tool_name": "query_orders",
            "params": {"order_id": "ORD-1001"},
            "reasoning": "Operator asked for order status",
            "logical_entropy": 0.10,
            "acc_conflict_score": 0.05,
        }
    )
    state.update(await governed_tool_node(state))
    print(
        f"[step {state['step']}] query_orders "
        f"blocked={state.get('blocked')} status={state.get('physical_gate_status')} "
        f"result={state.get('tool_result')}"
    )

    # Step 2 — high-criticality export + escalated drift/entropy (usually vetoed)
    state.update(
        {
            "tool_name": "export_csv",
            "params": {"scope": "payroll_all"},
            "reasoning": "Escalate to full payroll dump",
            "logical_entropy": 0.80,
            "acc_conflict_score": 0.90,
        }
    )
    state.update(await governed_tool_node(state))
    print(
        f"[step {state['step']}] export_csv "
        f"blocked={state.get('blocked')} status={state.get('physical_gate_status')} "
        f"penalty={state.get('penalty_log')}"
    )


def compile_langgraph_if_available():
    """
    Optional wiring when `langgraph` is installed.

    Returns a compiled graph, or None if the dependency is missing.
    """
    try:
        from langgraph.graph import END, StateGraph
    except ImportError:
        return None

    registry = build_demo_registry()
    aegis = AegisGatewayRuntime(
        default_tools=registry.get_tool_names(),
        tool_criticality_scores=registry.as_criticality_map(),
    )

    async def _open(state: GraphState) -> GraphState:
        seeded = dict(state)
        seeded.setdefault("aegis", aegis)
        seeded.setdefault("registry", registry)
        return open_session_node(seeded)  # type: ignore[arg-type]

    graph = StateGraph(GraphState)
    graph.add_node("open_session", _open)
    graph.add_node("governed_tool", governed_tool_node)
    graph.set_entry_point("open_session")
    graph.add_edge("open_session", "governed_tool")
    graph.add_edge("governed_tool", END)
    return graph.compile()


if __name__ == "__main__":
    asyncio.run(run_demo())
    compiled = compile_langgraph_if_available()
    if compiled is None:
        print(
            "\n[note] langgraph not installed — demo used the standalone node loop. "
            "pip install langgraph to enable compile_langgraph_if_available()."
        )
    else:
        print("\n[note] langgraph is available; compile_langgraph_if_available() returned a compiled graph.")
