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
        self._session_state = {"effective_risk": 1.2, "trust_level": 0.0, "icu_mode": True}

    def ingress_gate(self, raw_input: str) -> AegisIngressPayload:
        return AegisIngressPayload(
            session_id="sess_test_egress_veto",
            sanitized_input=raw_input,
            budget=ComputeBudget(max_tokens=1000, max_steps=10, tci_score=0.2),
            allowed_tools=["query_db"],
        )

    def egress_gate(self, request, ingress) -> AegisDecision:
        return AegisDecision(
            session_id=request.session_id,
            status=DecisionStatus.REJECTED,
            rejection_reason="egress equation veto: effective_risk=1.2000 >= R_MAX=1.0000",
            penalty_log="[EGRESS_VETO] blocked",
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
            action_type=ControlAction.TOOL_CALL,
            tool_name="query_db",
            parameters={"query": "select 1"},
            thought_summary="trigger egress veto path",
        )


class TestRuntimeEgressVeto(unittest.TestCase):
    def test_runtime_hard_stops_on_egress_veto(self):
        with patch("agent_os_runtime.AegisGatewayRuntime", FakeAegisGatewayRuntime), patch(
            "agent_os_runtime.NoesisRuntimeKernel", FakeNoesisRuntimeKernel
        ):
            result = asyncio.run(
                run_agent_os_once(
                    "test egress veto",
                    return_diagnostics=True,
                    enable_hypothalamus=False,
                    enable_acc=False,
                )
            )
        self.assertTrue(result.get("resolved"))
        self.assertIn("[HARD_MELTDOWN][EGRESS_VETO]", str(result.get("final_output", "")))
        self.assertEqual(result.get("steps"), 1)
        self.assertEqual(result.get("pulse_count"), 1)
        last_pulse = result.get("last_pulse_snapshot", {})
        self.assertTrue(last_pulse.get("last_step_data", {}).get("terminal"))
        self.assertEqual(
            last_pulse.get("last_step_data", {}).get("terminal_cause"),
            "AGENT_OS_EGRESS: R_EFFECTIVE_EXCEEDED",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
