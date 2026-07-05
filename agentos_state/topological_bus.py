import asyncio
import logging
from typing import Awaitable, Callable, Dict, List, Optional

from agentos_state.global_state_tensor import GlobalStateTensor
from protocol_schema import PulseSnapshot

logger = logging.getLogger("AgentOS.Bus")

ObserverCallback = Callable[[GlobalStateTensor], Awaitable[None]]
PulseCallback = Callable[[GlobalStateTensor, PulseSnapshot], Awaitable[None]]


class TopologicalBus:
    """
    拓扑状态总线 (White Matter Bus) - 纯异步无锁版
    基于 Pub/Sub 模式的异步事件循环中枢。
    """

    def __init__(self):
        self._current_tensor: Optional[GlobalStateTensor] = None
        self._subscribers: List[ObserverCallback] = []
        self._pulse_listeners: Dict[str, PulseCallback] = {}

    def mount_tensor(self, tensor: GlobalStateTensor) -> None:
        self._current_tensor = tensor
        logger.debug(f"[Bus] Tensor {tensor.session_id} mounted.")

    def subscribe(self, callback: ObserverCallback) -> None:
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    async def push_update(self) -> None:
        if not self._current_tensor:
            logger.error("[Bus Error] Tried to push update without mounted tensor.")
            return

        if self._current_tensor.is_resolved:
            return

        if self._subscribers:
            tasks = [asyncio.create_task(callback(self._current_tensor)) for callback in self._subscribers]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    module_name = self._subscribers[i].__name__
                    logger.error(f"[Bus] Module {module_name} failed: {str(result)}")

    def attach(self, name: str, callback: PulseCallback) -> None:
        """Attach named heartbeat listener, e.g. hypothalamus."""
        self._pulse_listeners[name] = callback

    async def broadcast_pulse(self, tensor: GlobalStateTensor, snapshot: PulseSnapshot) -> None:
        """Broadcast runtime heartbeat to all attached listeners."""
        if not self._pulse_listeners:
            return
        tasks = [asyncio.create_task(callback(tensor, snapshot)) for callback in self._pulse_listeners.values()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                listener_name = list(self._pulse_listeners.keys())[i]
                logger.error(f"[Bus] Pulse listener {listener_name} failed: {str(result)}")

    def get_tensor(self) -> Optional[GlobalStateTensor]:
        return self._current_tensor
