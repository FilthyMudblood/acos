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
from core_runtime.runtime_stack import PhysicalToolRegistry, ToolSpec
from protocol_schema import AegisIngressPayload, ComputeBudget, ControlAction, NoesisActionIntent

from agent_os_runtime import run_agent_os_once


async def lookup_order(order_id: str):
    return {"status": "found", "order_id": order_id, "amount": 128.5}


class FakeNoesisRuntimeKernel:
    last_tensor = None

    def __init__(self, api_key=None, base_url=None):
        pass

    def bootstrap_from_ingress(self, ingress: AegisIngressPayload) -> GlobalStateTensor:
        tensor = GlobalStateTensor(session_id=ingress.session_id, raw_input=ingress.sanitized_input)
        tensor.budget = SimpleNamespace(max_steps=ingress.budget.max_steps)
        FakeNoesisRuntimeKernel.last_tensor = tensor
        return tensor

    async def run_step(self, tensor: GlobalStateTensor) -> NoesisActionIntent:
        has_observation = any(event.get("type") == "OBSERVATION" for event in tensor.history)
        if not has_observation:
            return NoesisActionIntent(
                action_type=ControlAction.TOOL_CALL,
                tool_name="lookup_order",
                parameters={"order_id": "ORD-42"},
                thought_summary="Need to inspect order details before answering.",
            )

        return NoesisActionIntent(
            action_type=ControlAction.FINAL_ANSWER,
            final_answer="Order ORD-42 found with amount 128.5.",
            thought_summary="Observation received; final answer can be returned.",
        )


class TestRuntimeToolSuccess(unittest.TestCase):
    def test_tool_success_observation_then_final_answer(self):
        tool_registry = PhysicalToolRegistry(
            [
                ToolSpec(
                    name="lookup_order",
                    handler=lookup_order,
                    capabilities={"read", "lookup"},
                    description="Order lookup test adapter.",
                    criticality_score=0.2,
                )
            ]
        )

        with patch("agent_os_runtime.NoesisRuntimeKernel", FakeNoesisRuntimeKernel):
            result = asyncio.run(
                run_agent_os_once(
                    "lookup order ORD-42",
                    return_diagnostics=True,
                    enable_hypothalamus=False,
                    enable_acc=False,
                    physical_tool_registry=tool_registry,
                )
            )

        self.assertTrue(result.get("resolved"))
        self.assertEqual(result.get("final_output"), "Order ORD-42 found with amount 128.5.")
        self.assertEqual(result.get("steps"), 2)
        self.assertEqual(result.get("physical_gate_status"), "NORMAL_EXECUTION")
        self.assertEqual(result.get("pulse_count"), 2)
        last_pulse = result.get("last_pulse_snapshot", {})
        self.assertTrue(last_pulse.get("last_step_data", {}).get("terminal"))
        self.assertEqual(
            last_pulse.get("last_step_data", {}).get("terminal_cause"),
            "AGENT_OS_APPROVED_FINAL_ANSWER",
        )

        invocations = result.get("tool_invocations", [])
        self.assertEqual(len(invocations), 1)
        self.assertEqual(invocations[0]["tool_name"], "lookup_order")
        self.assertTrue(invocations[0]["ok"])
        self.assertEqual(invocations[0]["input"], {"order_id": "ORD-42"})
        self.assertEqual(invocations[0]["output"]["status"], "found")
        self.assertEqual(invocations[0]["decision"]["status"], "APPROVED")
        self.assertIn("effective_risk", invocations[0]["risk"])

        tensor = FakeNoesisRuntimeKernel.last_tensor
        self.assertIsNotNone(tensor)
        observations = [event for event in tensor.history if event.get("type") == "OBSERVATION"]
        self.assertEqual(len(observations), 1)
        self.assertIn("[TOOL_SUCCESS]", observations[0]["data"]["observation"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
