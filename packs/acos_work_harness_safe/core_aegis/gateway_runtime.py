from typing import Any, Dict, List, Optional

from protocol_schema import AegisDecision, AegisIngressPayload, NoesisActionRequest

from .amygdala_policy import global_amygdala
from .config import DEFAULT_EGRESS_EQUATION_CONFIG, DEFAULT_SAFE_TOOLS
from .egress_gate import EgressGate
from .ingress_gate import IngressGate


class AegisGatewayRuntime:
    """Composed Aegis gateway runtime: ingress + egress."""

    def __init__(
        self,
        default_tools: Optional[List[str]] = None,
        tool_criticality_scores: Optional[Dict[str, float]] = None,
    ) -> None:
        self._session_state: Dict[str, Dict[str, Any]] = {}
        self._ingress = IngressGate(
            default_tools=default_tools or ["query_db", "refund_lookup"],
            amygdala_probe=global_amygdala,
        )
        self._egress = EgressGate(
            safe_tools=DEFAULT_SAFE_TOOLS,
            equation_config=DEFAULT_EGRESS_EQUATION_CONFIG,
            tool_criticality_scores=tool_criticality_scores,
        )

    def get_session_state(self, session_id: str) -> Dict[str, Any]:
        return dict(self._session_state.get(session_id, {}))

    def ingress_gate(self, raw_input: str) -> AegisIngressPayload:
        ingress, policy_state = self._ingress.issue(raw_input)
        self._session_state[ingress.session_id] = policy_state
        return ingress

    def egress_gate(self, request: NoesisActionRequest, ingress: AegisIngressPayload) -> AegisDecision:
        session_policy_state = self._session_state.get(request.session_id, {})
        decision, updated_state = self._egress.decide(request, ingress, session_policy_state)
        self._session_state[request.session_id] = updated_state
        return decision


# Backward-compatible alias for existing code.
AegisGatewayKernel = AegisGatewayRuntime
