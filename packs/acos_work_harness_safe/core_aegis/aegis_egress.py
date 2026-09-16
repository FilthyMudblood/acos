import math
from dataclasses import dataclass


@dataclass(frozen=True)
class ToolRiskProfile:
    criticality_score: float


@dataclass(frozen=True)
class IntentSignal:
    action: str
    tool: ToolRiskProfile


@dataclass(frozen=True)
class ACCSignal:
    drift: float
    entropy: float


class AegisEgressGateway:
    """
    Non-linear physical arbitration equation for egress.
    This gateway is stateful across steps and is the only risk judge.
    """

    def __init__(self, r_max: float = 1.0, decay_factor: float = 0.8, kappa: float = 3.0, momentum_tau: float = 0.5):
        self.R_MAX = float(r_max)
        self.DECAY_FACTOR = float(decay_factor)
        self.KAPPA = float(kappa)
        self.MOMENTUM_TAU = float(momentum_tau)

        self._history_potential_r = 0.0
        self._last_kinetic_r = 0.0
        self._last_effective_r = 0.0

    @property
    def last_effective_risk(self) -> float:
        return float(self._last_effective_r)

    def arbitrate(self, intent: IntentSignal, acc_signal: ACCSignal) -> bool:
        """
        Core arbitration:
        Collapse drift/entropy/tool-criticality into a single veto boolean.
        """
        d_t = max(0.0, min(1.0, float(acc_signal.drift)))
        e_t = max(0.0, min(1.0, float(acc_signal.entropy)))
        c_t = max(0.0, min(1.0, float(intent.tool.criticality_score)))

        exponent = min(self.KAPPA * d_t * e_t, 10.0)
        r_kinetic = c_t * (math.exp(exponent) - 1.0)

        self._history_potential_r = (self.DECAY_FACTOR * self._history_potential_r) + r_kinetic

        delta_r = max(0.0, r_kinetic - self._last_kinetic_r)
        self._last_kinetic_r = r_kinetic

        r_effective = self._history_potential_r + (self.MOMENTUM_TAU * delta_r)
        self._last_effective_r = float(r_effective)

        if r_effective >= self.R_MAX:
            self._trigger_veto(intent, r_effective)
            return False
        return True

    def _trigger_veto(self, intent: IntentSignal, r_eff: float) -> None:
        print(f"[EGRESS_VETO] Intent {intent.action} blocked. R_eff: {r_eff:.4f} >= {self.R_MAX}")
