import uuid
from typing import Any, Dict, Optional

from protocol_schema import AegisIngressPayload, ComputeBudget


class IngressGate:
    """Aegis ingress cleaner and budget allocator."""

    def __init__(self, default_tools: Optional[list[str]] = None, amygdala_probe: Optional[Any] = None) -> None:
        self._default_tools = list(default_tools or ["query_db", "refund_lookup"])
        self._amygdala_probe = amygdala_probe

    def _seed_ingress_state(self, instruction: str) -> Dict[str, Any]:
        state: Dict[str, Any] = {
            "instruction": instruction,
            "module_name": "DEFAULT",
            "tci_score": 0.2,
            "hijack_flag": False,
            "enable_kernel": True,
            "enable_egress_policy_arbitration": True,
            "draft_output": "",
            "final_output": "",
            "decision_path": [],
            "signals": {},
            "metadata": {},
            "trust_level": 1.0,
            "icu_mode": False,
            "current_s_score": 0.0,
            "effective_risk": 0.0,
            "conflict_history": [],
        }
        if self._amygdala_probe is not None:
            try:
                state.update(self._amygdala_probe(state))
            except Exception:
                pass
        return state

    def issue(self, raw_input: str) -> tuple[AegisIngressPayload, Dict[str, Any]]:
        sanitized = (raw_input or "").strip()
        session_id = f"sess_{uuid.uuid4().hex[:12]}"
        policy_state = self._seed_ingress_state(sanitized)
        tci_score = float(policy_state.get("tci_score", 0.2) or 0.2)
        allowed_tools = [] if policy_state.get("hijack_flag", False) else list(self._default_tools)
        payload = AegisIngressPayload(
            session_id=session_id,
            sanitized_input=sanitized,
            budget=ComputeBudget(max_tokens=2000, max_steps=10, tci_score=tci_score),
            allowed_tools=allowed_tools,
        )
        return payload, policy_state
