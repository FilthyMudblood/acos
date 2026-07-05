from agentos_state.global_state_tensor import GlobalStateTensor, IntentType, MetabolicBudget
from protocol_schema import AegisIngressPayload


class IngressTensorAdapter:
    """Noesis ingress adapter: payload -> tensor."""

    def from_ingress(self, payload: AegisIngressPayload) -> GlobalStateTensor:
        tensor = GlobalStateTensor(session_id=payload.session_id, raw_input=payload.sanitized_input)
        tensor.budget = MetabolicBudget(
            max_tokens=2000,
            max_steps=payload.budget.max_steps,
            temperature_baseline=0.7,
            allow_tools=len(payload.allowed_tools) > 0,
        )
        tensor.intent = IntentType.TASK_EXECUTION
        tensor.tci_score = payload.budget.tci_score
        tensor.authorized_tools = payload.allowed_tools
        return tensor
