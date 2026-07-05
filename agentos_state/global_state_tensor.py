import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class IntentType(Enum):
    CHITCHAT = "chitchat"
    TASK_EXECUTION = "task_execution"
    DEEP_REASONING = "deep_reasoning"
    CRITICAL_SAFETY = "critical_safety"


@dataclass
class MetabolicBudget:
    """下丘脑分配的代谢预算（绝对算力边界）"""

    max_tokens: int
    max_steps: int
    temperature_baseline: float
    allow_tools: bool


@dataclass
class DampingSignal:
    """ACC 注入的柔性阻尼信号"""

    entropy_score: float
    correction_prompt: str
    temperature_delta: float


@dataclass
class CognitiveStep:
    """PFC 在拓扑空间中走过的脚印"""

    step_id: int
    action_type: str
    content: Any
    metabolic_cost: int


class GlobalStateTensor:
    """
    全局状态张量 (Global State Tensor) - Runtime 物理安全版
    所有脑区围绕此张量进行异步观测与修改，所有写操作必须通过内部 Lock 保障原子性。
    """

    def __init__(self, session_id: str, raw_input: str):
        self.session_id = session_id
        self.raw_input = raw_input

        self.intent: Optional[IntentType] = None
        self.budget: Optional[MetabolicBudget] = None

        self.working_memory: List[Dict[str, Any]] = []
        self.active_attractor: Optional[str] = None
        self.metadata: Dict[str, Any] = {}
        self.history: List[Dict[str, Any]] = []

        self.pfc_trace: List[CognitiveStep] = []
        self.active_damping_signals: List[DampingSignal] = []

        self.is_resolved: bool = False
        self.final_output: Optional[str] = None

        self._lock: Optional[asyncio.Lock] = None

    async def _get_lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    async def resolve(self, output: str, attractor_name: str) -> bool:
        lock = await self._get_lock()
        async with lock:
            if self.is_resolved:
                return False
            self.is_resolved = True
            self.final_output = output
            self.active_attractor = attractor_name
            self.history.append(
                {
                    "type": "RESOLVE",
                    "data": {"output": str(output), "attractor": attractor_name},
                }
            )
            return True

    async def append_trace(self, step: CognitiveStep) -> None:
        lock = await self._get_lock()
        async with lock:
            self.pfc_trace.append(step)
            self.history.append(
                {
                    "type": "ACTION",
                    "data": {"step_id": step.step_id, "content": str(step.content)},
                }
            )

    async def inject_damping(self, signal: DampingSignal) -> None:
        lock = await self._get_lock()
        async with lock:
            self.active_damping_signals.append(signal)
            self.history.append(
                {
                    "type": "DAMPING",
                    "data": {
                        "entropy_score": signal.entropy_score,
                        "correction_prompt": signal.correction_prompt,
                        "temperature_delta": signal.temperature_delta,
                    },
                }
            )

    async def inject_memory(self, docs: List[Dict[str, Any]]) -> None:
        lock = await self._get_lock()
        async with lock:
            existing_sources = {doc.get("source") for doc in self.working_memory}
            for doc in docs:
                if doc.get("source") not in existing_sources:
                    self.working_memory.append(doc)

    async def inject_observation(self, tool_name: str, observation_data: Any) -> None:
        lock = await self._get_lock()
        async with lock:
            record = {
                "source": f"tool::{tool_name}::{len(self.working_memory) + 1}",
                "content": str(observation_data),
                "type": "observation",
            }
            self.working_memory.append(record)
            self.history.append(
                {
                    "type": "OBSERVATION",
                    "data": {
                        "tool_name": tool_name,
                        "observation": str(observation_data),
                    },
                }
            )

    async def inject_tool_error(self, tool_name: str, error_message: str) -> None:
        lock = await self._get_lock()
        async with lock:
            record = {
                "source": f"tool_error::{tool_name}::{len(self.working_memory) + 1}",
                "content": str(error_message),
                "type": "tool_error",
            }
            self.working_memory.append(record)
            self.history.append(
                {
                    "type": "OBSERVATION",
                    "data": {
                        "tool_name": tool_name,
                        "observation": f"[TOOL_ERROR] {error_message}",
                    },
                }
            )

    async def update_metadata(self, patch: Dict[str, Any]) -> None:
        lock = await self._get_lock()
        async with lock:
            self.metadata.update(patch)

    def get_current_entropy_context(self) -> str:
        if not self.pfc_trace:
            return ""
        recent_steps = self.pfc_trace[-3:]
        return "\n".join([f"[{s.action_type}]: {str(s.content)[:100]}" for s in recent_steps])
