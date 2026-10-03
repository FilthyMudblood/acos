#!/usr/bin/env python3
"""L1 realism: read-only FS + MCP-behind-Executor wiring tests."""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core_runtime.connectors import (
    McpBackendSketch,
    McpToolProxy,
    ReadOnlyFilesystemConnector,
    ReadOnlyFsError,
)
from core_runtime.execute import execute_approved
from core_runtime.runtime_stack import PhysicalToolRegistry, ToolSpec
from protocol_schema import ActionType, AegisDecision, DecisionStatus


class ReadOnlyFsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tmpdir.name)
        (self.root / "notes.txt").write_text("hello-acos", encoding="utf-8")
        (self.root / "sub").mkdir()
        (self.root / "sub" / "inner.txt").write_text("inner", encoding="utf-8")
        self.fs = ReadOnlyFilesystemConnector(self.root)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_read_text_ok(self) -> None:
        out = asyncio.run(self.fs.read_text("notes.txt"))
        self.assertEqual(out["content"], "hello-acos")
        self.assertEqual(out["mode"], "read_only")

    def test_path_escape_rejected(self) -> None:
        with self.assertRaises(ReadOnlyFsError):
            asyncio.run(self.fs.read_text("../etc/passwd"))
        with self.assertRaises(ReadOnlyFsError):
            asyncio.run(self.fs.read_text("/etc/passwd"))

    def test_write_forbidden(self) -> None:
        with self.assertRaises(ReadOnlyFsError):
            asyncio.run(self.fs.write_text("notes.txt", "nope"))

    def test_executor_only_after_approved(self) -> None:
        handlers = self.fs.as_tool_handlers()
        registry = PhysicalToolRegistry(
            [
                ToolSpec(
                    name="fs_read_text",
                    handler=handlers["fs_read_text"],
                    capabilities={"read", "fs"},
                    criticality_score=0.2,
                )
            ]
        )
        rejected = AegisDecision(
            session_id="s-fs",
            status=DecisionStatus.REJECTED,
            executed_action=ActionType.TOOL_CALL,
            executed_payload={"tool_name": "fs_read_text", "parameters": {"path": "notes.txt"}},
            remaining_budget_tokens=100,
            rejection_reason="policy",
        )
        result, audit = asyncio.run(execute_approved(rejected, registry))
        self.assertFalse(result.ok)
        self.assertIsNone(audit)

        approved = AegisDecision(
            session_id="s-fs",
            status=DecisionStatus.APPROVED,
            executed_action=ActionType.TOOL_CALL,
            executed_payload={"tool_name": "fs_read_text", "parameters": {"path": "notes.txt"}},
            remaining_budget_tokens=100,
        )
        result2, audit2 = asyncio.run(execute_approved(approved, registry))
        self.assertTrue(result2.ok)
        assert result2.tool_result is not None
        self.assertEqual(result2.tool_result["content"], "hello-acos")
        self.assertIsNotNone(audit2)


class McpBehindExecutorTests(unittest.TestCase):
    def test_mcp_reachable_only_via_registry_handler(self) -> None:
        backend = McpBackendSketch(server_name="demo-mcp")

        async def lookup_order(order_id: str) -> dict:
            return {"order_id": order_id, "status": "paid"}

        backend.register(
            "lookup_order",
            lookup_order,
            description="read order",
            criticality_hint=0.3,
        )
        proxy = McpToolProxy(backend, "lookup_order")
        registry = PhysicalToolRegistry(
            [
                ToolSpec(
                    name="lookup_order",
                    handler=proxy.handler,
                    capabilities={"read", "mcp"},
                    criticality_score=0.3,
                )
            ]
        )

        # Direct backend call is possible in-process (L1 limit) but the *product*
        # contract is that hosts wire tools only through execute_approved.
        approved = AegisDecision(
            session_id="s-mcp",
            status=DecisionStatus.APPROVED,
            executed_action=ActionType.TOOL_CALL,
            executed_payload={
                "tool_name": "lookup_order",
                "parameters": {"order_id": "ORD-1"},
            },
            remaining_budget_tokens=50,
        )
        result, audit = asyncio.run(execute_approved(approved, registry))
        self.assertTrue(result.ok)
        assert result.tool_result is not None
        self.assertEqual(result.tool_result["tool"], "lookup_order")
        self.assertEqual(result.tool_result["result"]["order_id"], "ORD-1")
        self.assertEqual(len(backend.call_log), 1)
        self.assertIsNotNone(audit)

        rejected = AegisDecision(
            session_id="s-mcp",
            status=DecisionStatus.HARD_MELTDOWN,
            executed_action=ActionType.TOOL_CALL,
            executed_payload={
                "tool_name": "lookup_order",
                "parameters": {"order_id": "ORD-2"},
            },
            remaining_budget_tokens=0,
            rejection_reason="meltdown",
        )
        result2, _ = asyncio.run(execute_approved(rejected, registry))
        self.assertFalse(result2.ok)
        self.assertEqual(len(backend.call_log), 1, "non-APPROVED must not call MCP backend")

    def test_list_tools_metadata(self) -> None:
        backend = McpBackendSketch()

        async def ping() -> dict:
            return {"ok": True}

        backend.register("ping", ping, description="health", criticality_hint=0.1)
        names = [t.name for t in backend.list_tools()]
        self.assertEqual(names, ["ping"])


if __name__ == "__main__":
    unittest.main()
