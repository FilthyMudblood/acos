import re
from difflib import get_close_matches
from dataclasses import dataclass
from typing import Dict, List, Optional

from agentos_state.global_state_tensor import GlobalStateTensor
from agentos_state.topological_bus import TopologicalBus
from core_noesis.cognitive_modules.base import CognitiveModule


@dataclass
class HabitSOP:
    attractor_name: str
    regex_pattern: re.Pattern
    static_output: str


class BasalGanglia(CognitiveModule):
    """Basal ganglia fast bypass router."""

    def __init__(self, bus: TopologicalBus):
        self.bus = bus
        self._sops: List[HabitSOP] = self._load_hardcoded_sops()
        self.reflex_dict: Dict[str, str] = {
            "hello": "[Basal Ganglia Bypass] Pong. 请下达明确的业务指令。",
            "hi": "[Basal Ganglia Bypass] 你好，我是 AC-OS。请提供上下文。",
            "ping": "pong",
            "help": "请提供需要分析的文本、调用的工具名称或具体的业务参数。",
        }
        self.short_whitelist = set(self.reflex_dict.keys())
        self.bus.subscribe(self.evaluate_state)

    def _load_hardcoded_sops(self) -> List[HabitSOP]:
        return [
            HabitSOP(
                attractor_name="SOP_SYS_PING",
                regex_pattern=re.compile(r"^\s*(ping|你在吗|hello).*$", re.IGNORECASE),
                static_output="[Basal Ganglia Bypass] Pong. Noesis Kernel is online and fully operational.",
            ),
            HabitSOP(
                attractor_name="SOP_CLEAR_CACHE",
                regex_pattern=re.compile(r".*(清除|清理).*(缓存|cache).*", re.IGNORECASE),
                static_output="[Basal Ganglia Bypass] 执行本地静态脚本：内存黑板已重置，缓存已清空。",
            ),
            HabitSOP(
                attractor_name="SOP_WHO_ARE_YOU",
                regex_pattern=re.compile(r".*(你是谁|your name).*", re.IGNORECASE),
                static_output="[Basal Ganglia Bypass] 我是 Project Noesis，一个基于复杂自适应系统构架的仿生智能体内核。",
            ),
            HabitSOP(
                attractor_name="SOP_REFUND_INQUIRY",
                regex_pattern=re.compile(r".*(退款|退货|钱退给我).*", re.IGNORECASE),
                static_output="[Basal Ganglia Bypass] 请提供您的订单号或交易流水号。系统将在核实后自动发起原路退回流程。",
            ),
        ]

    async def evaluate_and_intercept(self, tensor: GlobalStateTensor) -> bool:
        """
        Evaluate current tensor and decide whether to trigger reflex intercept.
        Return True when intercepted (PFC should not run).
        """
        if tensor.is_resolved:
            return False

        history_action_count = len([e for e in tensor.history if e.get("type") == "ACTION"])
        if history_action_count > 0:
            return False

        raw_input = str(tensor.raw_input or "").strip()
        raw_input_lower = raw_input.lower()

        # Defense 1: dictionary reflex.
        if raw_input_lower in self.reflex_dict:
            return await self._trigger_reflex(
                tensor,
                message=self.reflex_dict[raw_input_lower],
                status="SUCCESS",
                reason="Dictionary Hit",
                attractor_name="BG_DICTIONARY_REFLEX",
            )

        # Defense 1.5: fuzzy dictionary reflex for typo tolerance.
        # Scope is intentionally narrow (single short token) to avoid
        # over-matching normal multi-word business instructions.
        if (
            raw_input_lower
            and len(raw_input_lower) <= 20
            and " " not in raw_input_lower
            and "\t" not in raw_input_lower
        ):
            candidates = list(self.reflex_dict.keys())
            close = get_close_matches(raw_input_lower, candidates, n=1, cutoff=0.75)
            if close:
                matched = close[0]
                return await self._trigger_reflex(
                    tensor,
                    message=self.reflex_dict[matched],
                    status="SUCCESS",
                    reason=f"Fuzzy Dictionary Hit (matched={matched})",
                    attractor_name="BG_FUZZY_DICTIONARY_REFLEX",
                )

        # Defense 2: too short input.
        if len(raw_input_lower) < 3 and raw_input_lower not in self.short_whitelist:
            return await self._trigger_reflex(
                tensor,
                message="[Aegis Ingress 拦截] 输入过短或意图不明。为保护算力，请提供更完整的上下文（至少3个字符）。",
                status="REJECTED",
                reason="Input Too Short",
                attractor_name="BG_SHORT_INPUT_BLOCK",
            )

        # Defense 3: repeated-character entropy attack.
        if re.search(r"(.)\1{3,}", raw_input_lower):
            return await self._trigger_reflex(
                tensor,
                message="[Aegis Ingress 拦截] 检测到无意义的连续重复字符。为避免逻辑幻觉，请重新整理您的指令。",
                status="REJECTED",
                reason="High Entropy Repeated Chars",
                attractor_name="BG_REPEATED_CHAR_BLOCK",
            )

        # Keep existing SOP reflex for known patterns.
        selected_sop: Optional[HabitSOP] = None
        for sop in self._sops:
            if sop.regex_pattern.match(raw_input):
                selected_sop = sop
                break
        if selected_sop:
            return await self._trigger_reflex(
                tensor,
                message=selected_sop.static_output,
                status="SUCCESS",
                reason=f"SOP Hit: {selected_sop.attractor_name}",
                attractor_name=selected_sop.attractor_name,
            )

        return False

    async def evaluate_state(self, tensor: GlobalStateTensor) -> None:
        await self.evaluate_and_intercept(tensor)

    async def _trigger_reflex(
        self,
        tensor: GlobalStateTensor,
        message: str,
        status: str,
        reason: str,
        attractor_name: str,
    ) -> bool:
        resolved = await tensor.resolve(output=message, attractor_name=attractor_name)
        await tensor.update_metadata(
            {
                "handled_by": "Basal_Ganglia_Bypass",
                "bg_status": status,
                "bg_reason": reason,
            }
        )
        return resolved
