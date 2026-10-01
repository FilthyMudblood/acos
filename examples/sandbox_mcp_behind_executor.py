#!/usr/bin/env python3
"""
Sandbox sketch: MCP-shaped backend lives *behind* the Runtime Executor.

Correct:
  Intent → Gateway (APPROVED) → execute_approved → registry → MCP sketch

Incorrect (do not do this in product integrations):
  LLM / LangGraph ToolNode ──direct──► MCP server

Run from repo root:
  python examples/sandbox_mcp_behind_executor.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import Any, Dict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core_aegis.gateway_runtime import AegisGatewayRuntime
from core_runtime.connectors import McpBackendSketch, McpToolProxy
from core_runtime.execute import execute_approved
from core_runtime.intent_helpers import is_executable, make_tool_call_request
from core_runtime.runtime_stack import PhysicalToolRegistry, ToolSpec


async def _demo_lookup(order_id: str) -> Dict[str, Any]:
    return {"order_id": order_id, "status": "paid", "amount": 42.0}


async def _demo_export(scope: str) -> Dict[str, Any]:
    return {"scope": scope, "rows": 9999, "sink": "external"}


def build_mcp_behind_executor_stack() -> tuple[AegisGatewayRuntime, PhysicalToolRegistry, McpBackendSketch]:
    backend = McpBackendSketch(server_name="sandbox-mcp")
    backend.register("lookup_order", _demo_lookup, description="read order", criticality_hint=0.25)
    backend.register("export_csv", _demo_export, description="export", criticality_hint=0.95)

    registry = PhysicalToolRegistry(
        [
            ToolSpec(
                name="lookup_order",
                handler=McpToolProxy(backend, "lookup_order").handler,
                capabilities={"read", "mcp"},
                criticality_score=0.25,
            ),
            ToolSpec(
                name="export_csv",
                handler=McpToolProxy(backend, "export_csv").handler,
                capabilities={"export", "mcp"},
                criticality_score=0.95,
            ),
        ]
    )
    gateway = AegisGatewayRuntime(
        default_tools=registry.get_tool_names(),
        tool_criticality_scores=registry.as_criticality_map(),
    )
    return gateway, registry, backend


async def run_once(tool_name: str, params: Dict[str, Any], user_text: str = "sandbox demo") -> None:
    gateway, registry, backend = build_mcp_behind_executor_stack()
    ingress = gateway.ingress_gate(user_text)
    request = make_tool_call_request(
        session_id=ingress.session_id,
        step_count=1,
        tool_name=tool_name,
        parameters=params,
        reasoning_trajectory=f"sandbox request for {tool_name}",
    )
    decision = gateway.egress_gate(request, ingress)
    print(f"tool={tool_name} decision={decision.status.value} reason={decision.rejection_reason}")
    if not is_executable(decision):
        print("  skipped execute_approved (fail-closed)")
        print(f"  mcp_calls_so_far={len(backend.call_log)}")
        return
    result, audit = await execute_approved(decision, registry)
    print(f"  execute_ok={result.ok} tool_result={result.tool_result}")
    print(f"  mcp_calls={backend.call_log}")
    if audit:
        print(f"  audit_tool={audit.get('tool_name')}")


async def main() -> None:
    print("=== MCP behind Executor (lookup) ===")
    await run_once("lookup_order", {"order_id": "ORD-42"})
    print("=== MCP behind Executor (export; may reject under risk/guards) ===")
    await run_once("export_csv", {"scope": "all_customers"})


if __name__ == "__main__":
    asyncio.run(main())
