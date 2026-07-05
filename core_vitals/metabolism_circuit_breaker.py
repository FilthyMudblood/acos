import math
import time
from collections import deque
from typing import Dict, Tuple

from agentos_state.global_state_tensor import GlobalStateTensor
from core_vitals.config import HYPOTHALAMUS_PROFILES
from protocol_schema import PulseSnapshot


class HypothalamusEngine:
    """
    Metabolism scheduler and compute allocator.
    """

    def __init__(self, profile_name: str = "CONSERVATIVE", base_budget: int = 2000):
        self.config = HYPOTHALAMUS_PROFILES.get(profile_name) or HYPOTHALAMUS_PROFILES["CONSERVATIVE"]
        self.h_buffer = deque(maxlen=5)
        self.dh_buffer = deque(maxlen=3)
        self.start_time = time.time()
        self.accumulated_tokens = 0
        self.base_budget = base_budget
        self.effective_tokens = 0.0
        self.base_score = 100.0
        self.k_penalty = 2.5
        self.survival_threshold = 30.0
        self.current_priority = 100.0
        # Metabolic warm-up thresholds:
        # - grace_period_tokens: absolute silent zone
        # - meltdown_activation_tokens: d2h-based kill switch activation threshold
        self.grace_period_tokens = 200
        self.meltdown_activation_tokens = max(400, int(self.base_budget * 0.2))

    def count_tokens(self, text: str) -> int:
        if not text:
            return 0
        parts = text.split()
        if parts:
            non_ws = sum(len(p) for p in parts)
            return len(parts) + max(0, (len(text) - non_ws) // 4)
        return max(1, len(text) // 4)

    def compute_health_index(self, metrics: Dict[str, float]) -> Tuple[float, float, float]:
        h = (
            self.config["w1_stab"] * float(metrics.get("l_stab", 1.0))
            + self.config["w2_eff"] * float(metrics.get("r_eff", 1.0))
            + self.config["w3_safe"] * float(metrics.get("c_safe", 1.0))
            + self.config["w4_align"] * float(metrics.get("g_align", 1.0))
        )
        self.h_buffer.append(h)
        dh_dt = 0.0
        d2h_dt2 = 0.0
        if len(self.h_buffer) >= 2:
            dh_dt = self.h_buffer[-1] - self.h_buffer[-2]
            self.dh_buffer.append(dh_dt)
            if len(self.dh_buffer) >= 2:
                d2h_dt2 = self.dh_buffer[-1] - self.dh_buffer[-2]
        return h, dh_dt, d2h_dt2

    def update_metabolism(self, chunk_text: str, h_current: float = 1.0, retries: int = 0) -> Dict[str, float]:
        chunk_tokens = self.count_tokens(chunk_text)
        self.accumulated_tokens += chunk_tokens
        error_rate = max(0.0, 1.0 - h_current)
        complexity_factor = 1.0 + (error_rate * 2.0) + (retries * 0.5)
        effective_cost = chunk_tokens * complexity_factor
        self.effective_tokens += effective_cost
        elapsed = time.time() - self.start_time
        if elapsed < 0.1:
            return {
                "r_eff": 1.0,
                "total_tokens": float(self.accumulated_tokens),
                "tps": 0.0,
                "effective_cost": self.effective_tokens,
            }
        tps = self.accumulated_tokens / elapsed
        r_eff = max(0.0, 1.0 - (tps / 200.0))
        return {
            "r_eff": float(r_eff),
            "total_tokens": float(self.accumulated_tokens),
            "tps": float(tps),
            "effective_cost": float(self.effective_tokens),
        }

    def decide_intervention(self, h: float, dh: float, d2h: float, retries: int = 0) -> str:
        if self.accumulated_tokens < self.grace_period_tokens:
            return "NORMAL"
        if self.effective_tokens > self.base_budget:
            return "BUDGET_EXHAUSTED"
        if self.accumulated_tokens < self.meltdown_activation_tokens:
            return "NORMAL"
        error_rate = max(0.0, 1.0 - h)
        instability_index = error_rate
        self.current_priority = self.base_score * math.exp(-self.k_penalty * instability_index)
        if self.current_priority < self.survival_threshold:
            return "HARD_MELTDOWN"
        if d2h <= -0.1 and self.accumulated_tokens >= self.meltdown_activation_tokens:
            return "HARD_MELTDOWN"
        return "NORMAL"


class HypothalamusPulseListener:
    """Out-of-band metabolic pulse listener."""

    def __init__(self, base_budget: int) -> None:
        self._engine = HypothalamusEngine(profile_name="CONSERVATIVE", base_budget=base_budget)

    async def on_pulse(self, tensor: GlobalStateTensor, snapshot: PulseSnapshot) -> None:
        if tensor.is_resolved:
            return

        latest_trace = tensor.pfc_trace[-1].content if tensor.pfc_trace else ""
        latest_text = str(latest_trace)[:400]
        metabolism = self._engine.update_metabolism(latest_text, retries=snapshot.retries)
        budget_ratio = 0.0
        if self._engine.base_budget > 0:
            budget_ratio = max(0.0, min(1.0, snapshot.current_tokens / self._engine.base_budget))
        r_eff = max(0.0, min(1.0, float(metabolism.get("r_eff", 1.0)) * (1.0 - budget_ratio)))
        h, dh, d2h = self._engine.compute_health_index(
            {
                "l_stab": max(0.0, min(1.0, 1.0 - snapshot.logical_entropy)),
                "r_eff": r_eff,
                "c_safe": max(0.0, min(1.0, 1.0 - snapshot.tci_score)),
                "g_align": 0.9,
            }
        )
        intervention = self._engine.decide_intervention(h, dh, d2h, retries=snapshot.retries)
        if intervention in {"HARD_MELTDOWN", "BUDGET_EXHAUSTED"}:
            await tensor.resolve(
                output=(
                    f"[METABOLIC_MELTDOWN] {intervention}: "
                    f"d2h/dt2 breach or budget exhaustion detected by hypothalamus."
                ),
                attractor_name="AGENT_OS_METABOLIC_MELTDOWN",
            )
