from typing import Optional

from agentos_state.global_state_tensor import GlobalStateTensor
from agentos_state.topological_bus import TopologicalBus
from protocol_schema import AegisIngressPayload, NoesisActionIntent
from core_noesis.cognitive_modules.basal_ganglia.basal_ganglia_gating import BasalGanglia
from core_noesis.adapters.ingress_tensor_adapter import IngressTensorAdapter
from core_noesis.adapters.intent_adapter import derive_action_intent

from .llm_client import NoesisLLMClient


class NoesisRuntimeKernel:
    """
    Step-based Noesis kernel.
    This module does not own a standalone while-loop runtime.
    """

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None) -> None:
        self._ingress_adapter = IngressTensorAdapter()
        self._bus = TopologicalBus()
        self._pfc = NoesisLLMClient(api_key=api_key, base_url=base_url)
        self._bg = BasalGanglia(self._bus)

    def bootstrap_from_ingress(self, ingress: AegisIngressPayload) -> GlobalStateTensor:
        tensor = self._ingress_adapter.from_ingress(ingress)
        self._bus.mount_tensor(tensor)
        return tensor

    async def run_step(self, tensor: GlobalStateTensor) -> NoesisActionIntent:
        if tensor.is_resolved:
            return derive_action_intent(tensor)

        # Basal ganglia bypass has first right of refusal
        # before any expensive PFC call.
        bg_intercepted = await self._bg.evaluate_and_intercept(tensor)
        if bg_intercepted:
            await self._bus.push_update()
            return derive_action_intent(tensor)

        await self._bus.push_update()
        if tensor.is_resolved:
            return derive_action_intent(tensor)

        await self._pfc.step(tensor)
        return derive_action_intent(tensor)
