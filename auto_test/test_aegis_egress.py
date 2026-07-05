import os
import sys
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core_aegis.aegis_egress import ACCSignal, AegisEgressGateway, IntentSignal, ToolRiskProfile


class TestAegisEquation(unittest.TestCase):
    def setUp(self) -> None:
        self.gateway = AegisEgressGateway(r_max=1.0, decay_factor=0.8, kappa=3.0, momentum_tau=0.5)

    def test_01_baseline_safe_execution(self) -> None:
        intent = IntentSignal(action="TOOL_CALL", tool=ToolRiskProfile(criticality_score=0.2))
        signal = ACCSignal(drift=0.1, entropy=0.1)
        self.assertTrue(self.gateway.arbitrate(intent, signal))

    def test_02_exponential_explosion_veto(self) -> None:
        intent = IntentSignal(action="TOOL_CALL", tool=ToolRiskProfile(criticality_score=0.9))
        signal = ACCSignal(drift=0.9, entropy=0.8)
        self.assertFalse(self.gateway.arbitrate(intent, signal))

    def test_03_temporal_accumulation_meltdown(self) -> None:
        intent = IntentSignal(action="TOOL_CALL", tool=ToolRiskProfile(criticality_score=0.5))
        signal = ACCSignal(drift=0.5, entropy=0.5)
        self.assertTrue(self.gateway.arbitrate(intent, signal))
        self.assertFalse(self.gateway.arbitrate(intent, signal))

    def test_04_gradient_momentum_penalty(self) -> None:
        safe_intent = IntentSignal(action="TOOL_CALL", tool=ToolRiskProfile(criticality_score=0.1))
        safe_signal = ACCSignal(drift=0.0, entropy=0.0)
        self.gateway.arbitrate(safe_intent, safe_signal)

        sudden_intent = IntentSignal(action="TOOL_CALL", tool=ToolRiskProfile(criticality_score=0.7))
        sudden_signal = ACCSignal(drift=0.6, entropy=0.6)
        self.assertFalse(self.gateway.arbitrate(sudden_intent, sudden_signal))


if __name__ == "__main__":
    unittest.main(verbosity=2)
