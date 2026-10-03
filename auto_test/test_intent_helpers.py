import os
import sys
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core_runtime.intent_helpers import is_executable, make_tool_call_request
from protocol_schema import ActionType, AegisDecision, DecisionStatus


class IntentHelpersTests(unittest.TestCase):
    def test_make_tool_call_request_shape(self) -> None:
        request = make_tool_call_request(
            session_id="sess-1",
            step_count=2,
            tool_name="query_db",
            parameters={"query": "select 1"},
            reasoning_trajectory="lookup refund",
            logical_entropy=0.1,
        )
        self.assertEqual(request.session_id, "sess-1")
        self.assertEqual(request.step_count, 2)
        self.assertEqual(request.proposed_action, ActionType.TOOL_CALL)
        self.assertEqual(request.action_payload["tool_name"], "query_db")
        self.assertEqual(request.action_payload["parameters"], {"query": "select 1"})
        self.assertEqual(request.reasoning_trajectory, "lookup refund")
        self.assertEqual(request.logical_entropy, 0.1)

    def test_make_tool_call_request_defaults(self) -> None:
        request = make_tool_call_request(
            session_id="s",
            step_count=0,
            tool_name="ping",
        )
        self.assertEqual(request.action_payload["parameters"], {})
        self.assertEqual(request.reasoning_trajectory, "tool proposal")
        self.assertEqual(request.logical_entropy, 0.0)

    def test_make_tool_call_request_acc_signals(self) -> None:
        request = make_tool_call_request(
            session_id="s",
            step_count=1,
            tool_name="export_csv",
            acc_conflict_score=0.9,
            acc_entropy_score=0.8,
        )
        self.assertEqual(request.action_payload["acc_conflict_score"], 0.9)
        self.assertEqual(request.action_payload["acc_entropy_score"], 0.8)

    def test_make_tool_call_request_rejects_blank_tool(self) -> None:
        with self.assertRaises(ValueError):
            make_tool_call_request(session_id="s", step_count=0, tool_name="  ")

    def test_is_executable(self) -> None:
        approved = AegisDecision(
            session_id="s",
            status=DecisionStatus.APPROVED,
            remaining_budget_tokens=10,
        )
        rejected = AegisDecision(
            session_id="s",
            status=DecisionStatus.REJECTED,
            remaining_budget_tokens=10,
            rejection_reason="veto",
        )
        self.assertTrue(is_executable(approved))
        self.assertFalse(is_executable(rejected))


if __name__ == "__main__":
    unittest.main()
