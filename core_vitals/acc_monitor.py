from typing import Any, Dict, Tuple

from agentos_state.global_state_tensor import DampingSignal, GlobalStateTensor
from protocol_schema import ActionType, PulseSnapshot


class UnifiedACCMonitor:
    """
    Unified ACC monitor:
    - Cognitive dimension: logical entropy damping
    - Security dimension: conflict scoring and alert marking
    """

    def __init__(self, entropy_threshold: float = 0.8, conflict_threshold: float = 0.7):
        self.entropy_threshold = entropy_threshold
        self.conflict_threshold = conflict_threshold

    def evaluate_scores(self, last_step_data: Dict[str, Any]) -> Tuple[float, float]:
        entropy_score = self._calculate_entropy(last_step_data)
        conflict_score = self._calculate_conflict(last_step_data)
        return entropy_score, conflict_score

    async def on_pulse(self, tensor: GlobalStateTensor, snapshot: PulseSnapshot) -> None:
        if tensor.is_resolved:
            return

        last_step_data = snapshot.last_step_data or {}
        entropy_score, conflict_score = self.evaluate_scores(last_step_data)

        if entropy_score > self.entropy_threshold:
            await tensor.inject_damping(
                DampingSignal(
                    entropy_score=entropy_score,
                    correction_prompt="[ACC_WARNING] High logical entropy. Narrow reasoning and re-evaluate.",
                    temperature_delta=-0.15,
                )
            )

        if conflict_score > self.conflict_threshold:
            await tensor.update_metadata(
                {
                    "acc_conflict_alert": True,
                    "s_score": conflict_score,
                }
            )
        else:
            await tensor.update_metadata(
                {
                    "acc_conflict_alert": False,
                    "s_score": conflict_score,
                }
            )

    def _calculate_entropy(self, data: Dict[str, Any]) -> float:
        if not data:
            return 0.0
        if "logical_entropy" in data:
            return max(0.0, min(1.0, float(data.get("logical_entropy", 0.0))))

        trajectory = str(data.get("reasoning_trajectory", ""))
        if not trajectory:
            return 0.0
        length_factor = min(1.0, len(trajectory) / 1200.0)
        repeat_factor = 0.0
        lowered = trajectory.lower()
        if lowered.count("retry") >= 2 or lowered.count("again") >= 2:
            repeat_factor = 0.2
        return max(0.0, min(1.0, length_factor + repeat_factor))

    def _calculate_conflict(self, data: Dict[str, Any]) -> float:
        if not data:
            return 0.0

        action_payload = data.get("action_payload") or {}
        payload_str = str(action_payload).lower()
        dangerous_keywords = ["drop table", "1=1", "delete", "reset", "admin"]
        for word in dangerous_keywords:
            if word in payload_str:
                return 0.95

        proposed_action = str(data.get("proposed_action", ""))
        allowed_tools = data.get("allowed_tools") or []
        tool_name = str(action_payload.get("tool_name", ""))

        conflict = 0.1
        if proposed_action == ActionType.TOOL_CALL.value:
            conflict += 0.2
            if not tool_name:
                conflict += 0.2
            elif tool_name not in allowed_tools:
                conflict += 0.3

        trajectory = str(data.get("reasoning_trajectory", "")).lower()
        if any(k in trajectory for k in ["bypass", "ignore rules", "root", "privilege"]):
            conflict += 0.3

        return max(0.0, min(1.0, conflict))
