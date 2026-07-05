from abc import ABC, abstractmethod

from agentos_state.global_state_tensor import GlobalStateTensor


class CognitiveModule(ABC):
    """Shared contract for cognitive modules mounted on bus."""

    @abstractmethod
    async def evaluate_state(self, tensor: GlobalStateTensor) -> None:
        raise NotImplementedError
