import asyncio
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from agentos_state.global_state_tensor import GlobalStateTensor
from protocol_schema import (
    ActionType,
    AegisDecision,
    AegisIngressPayload,
    ComputeBudget,
    ControlAction,
    DecisionStatus,
    NoesisActionIntent,
)

from agent_os_runtime import run_agent_os_once


class FakeAegisGatewayRuntime:
    def __init__(self, default_tools=None, tool_criticality_scores=None):
        self._session_state = {"effective_risk": 0.0, "trust_level": 1.0, "icu_mode": False}

    def ingress_gate(self, raw_input: str) -> AegisIngressPayload:
        return AegisIngressPayload(
            session_id="sess_test_semantic_terminate",
            sanitized_input=raw_input,
            budget=ComputeBudget(max_tokens=1000, max_steps=10, tci_score=0.1),
            allowed_tools=["query_db"],
        )

    def egress_gate(self, request, ingress) -> AegisDecision:
        return AegisDecision(
            session_id=request.session_id,
            status=DecisionStatus.APPROVED,
            executed_action=request.proposed_action,
            executed_payload=request.action_payload,
            remaining_budget_tokens=900,
        )

    def get_session_state(self, session_id: str):
        return dict(self._session_state)


class FakeNoesisRuntimeKernel:
    def __init__(self, api_key=None, base_url=None):
        pass

    def bootstrap_from_ingress(self, ingress: AegisIngressPayload) -> GlobalStateTensor:
        tensor = GlobalStateTensor(session_id=ingress.session_id, raw_input=ingress.sanitized_input)
        tensor.budget = SimpleNamespace(max_steps=ingress.budget.max_steps)
        return tensor

    async def run_step(self, tensor: GlobalStateTensor) -> NoesisActionIntent:
        return NoesisActionIntent(
            action_type=ControlAction.TERMINATE,
            thought_summary="检测到违规SQL注入模式，已触发拦截并终止。",
        )


class TestRuntimeTelemetrySplit(unittest.TestCase):
    def test_semantic_terminate_does_not_pollute_physical_gate_status(self):
        with patch("agent_os_runtime.AegisGatewayRuntime", FakeAegisGatewayRuntime), patch(
            "agent_os_runtime.NoesisRuntimeKernel", FakeNoesisRuntimeKernel
        ):
            result = asyncio.run(
                run_agent_os_once(
                    "drop table users",
                    return_diagnostics=True,
                    enable_hypothalamus=False,
                    enable_acc=False,
                )
            )

        self.assertTrue(result.get("resolved"))
        self.assertIn("[REJECTED][拦截][终止][TERMINATE]", str(result.get("final_output", "")))
        self.assertEqual(result.get("physical_gate_status"), "NORMAL_EXECUTION")
        self.assertEqual(result.get("semantic_intent_status"), ControlAction.TERMINATE.value.upper())
        self.assertEqual(
            result.get("termination_cause"),
            "AGENT_OS_NOESIS_TERMINATE: SQL_INJECTION_HEURISTIC",
        )
        self.assertEqual(result.get("effective_risk"), 0.0)
        self.assertEqual(result.get("steps"), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
