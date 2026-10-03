import asyncio
import os
import sys
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core_runtime.execute import execute_approved
from core_runtime.runtime_stack import PhysicalToolRegistry, ToolSpec
from protocol_schema import ActionType, AegisDecision, DecisionStatus


async def ping(name: str):
    return {"pong": name}


class ExecuteApprovedTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = PhysicalToolRegistry(
            [
                ToolSpec(
                    name="ping",
                    handler=ping,
                    capabilities={"read"},
                    criticality_score=0.2,
                )
            ]
        )

    def test_refuses_non_approved(self) -> None:
        decision = AegisDecision(
            session_id="s1",
            status=DecisionStatus.REJECTED,
            executed_action=ActionType.TOOL_CALL,
            executed_payload={"tool_name": "ping", "parameters": {"name": "x"}},
            remaining_budget_tokens=100,
            rejection_reason="test veto",
        )
        result, audit = asyncio.run(execute_approved(decision, self.registry))
        self.assertFalse(result.ok)
        self.assertIn("not APPROVED", result.error or "")
        self.assertIsNone(audit)

    def test_runs_approved_tool(self) -> None:
        decision = AegisDecision(
            session_id="s1",
            status=DecisionStatus.APPROVED,
            executed_action=ActionType.TOOL_CALL,
            executed_payload={
                "tool_name": "ping",
                "parameters": {"name": "acos"},
                "effective_risk": 0.1,
            },
            remaining_budget_tokens=100,
        )
        result, audit = asyncio.run(execute_approved(decision, self.registry))
        self.assertTrue(result.ok)
        self.assertEqual(result.tool_result, {"pong": "acos"})
        self.assertIsNotNone(audit)
        assert audit is not None
        self.assertEqual(audit["tool_name"], "ping")
        self.assertEqual(audit["decision"]["status"], "APPROVED")


if __name__ == "__main__":
    unittest.main()
