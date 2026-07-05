import asyncio
import json
import os
from typing import Optional, Tuple

from openai import AsyncOpenAI

from agentos_state.global_state_tensor import CognitiveStep, GlobalStateTensor


class PFCExecutor:
    """PFC single-step executor."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        resolved_key = api_key or os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
        resolved_base_url = (
            base_url or os.getenv("DEEPSEEK_BASE_URL") or os.getenv("OPENAI_API_BASE") or "https://api.deepseek.com"
        )
        if not resolved_key:
            raise ValueError("Missing API key. Provide api_key or set DEEPSEEK_API_KEY / OPENAI_API_KEY.")
        self.request_timeout_seconds = float(os.getenv("NOESIS_LLM_TIMEOUT_SECONDS", "60"))
        self.step_timeout_seconds = float(os.getenv("NOESIS_STEP_TIMEOUT_SECONDS", str(self.request_timeout_seconds)))
        self.client = AsyncOpenAI(
            api_key=resolved_key,
            base_url=resolved_base_url,
            timeout=self.request_timeout_seconds,
        )
        self.model_name = "deepseek-chat"

    async def step(self, tensor: GlobalStateTensor):
        if tensor.budget and len(tensor.pfc_trace) >= tensor.budget.max_steps:
            await tensor.resolve(output="[系统降级] 代谢预算已耗尽。", attractor_name="SYSTEM_HALT")
            return

        current_temperature = tensor.budget.temperature_baseline if tensor.budget else 0.7
        memory_context = ""
        if tensor.working_memory:
            memory_context = "\n【系统注入的相关背景知识】：\n"
            for doc in tensor.working_memory:
                memory_context += f"- {doc['content']}\n"
        current_prompt = f"任务目标: {tensor.raw_input}{memory_context}"

        if tensor.active_damping_signals:
            latest_signal = tensor.active_damping_signals[-1]
            current_temperature = max(0.0, min(1.0, current_temperature + latest_signal.temperature_delta))
            current_prompt += f"\n\n[系统阻尼指令]: {latest_signal.correction_prompt}"

        try:
            step_content, cost = await asyncio.wait_for(
                self._real_llm_inference(current_prompt, current_temperature, tensor),
                timeout=self.step_timeout_seconds,
            )
        except asyncio.TimeoutError:
            step_content, cost = (
                (
                    "[Tool Error] PFC step timeout: "
                    f"inference exceeded {self.step_timeout_seconds:.1f}s budget."
                ),
                10,
            )
        step_id = len(tensor.pfc_trace) + 1
        new_step = CognitiveStep(step_id=step_id, action_type="thought", content=step_content, metabolic_cost=cost)
        await tensor.append_trace(new_step)

    def _try_parse_intent_json(self, text: str) -> Optional[dict]:
        raw = (text or "").strip()
        candidates = [raw]
        if "```json" in raw:
            start = raw.find("```json")
            end = raw.find("```", start + 7)
            if start != -1 and end != -1:
                candidates.append(raw[start + 7 : end].strip())
        for candidate in candidates:
            if not candidate:
                continue
            try:
                data = json.loads(candidate)
                if isinstance(data, dict):
                    return data
            except Exception:
                continue
        return None

    async def _real_llm_inference(self, prompt: str, temperature: float, tensor: GlobalStateTensor) -> Tuple[str, int]:
        messages = [
            {
                "role": "system",
                "content": (
                    "你是 Project Noesis 的执行内核 (PFC)。输出必须是 JSON 对象，字段仅限: "
                    "action_type, tool_name, parameters, final_answer, thought_summary。"
                ),
            }
        ]
        for step in tensor.pfc_trace:
            messages.append({"role": "assistant", "content": f"步骤 {step.step_id}: {step.content}"})

        recent_events = tensor.history[-20:] if hasattr(tensor, "history") else []
        for event in recent_events:
            event_type = str(event.get("type", ""))
            event_data = event.get("data", {})
            if event_type == "ACTION":
                # Expose previous model trajectory back as assistant context.
                messages.append(
                    {
                        "role": "assistant",
                        "content": f"[PREVIOUS_ACTION_TRACE] {event_data}",
                    }
                )
            elif event_type == "DAMPING":
                correction = str(event_data.get("correction_prompt", ""))
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "[SYSTEM_OVERRIDE_ALERT] 你的上一步动作被 Aegis/ACC 拦截。\n"
                            f"原因: {correction}\n请立即改变策略，避免重复违规提议。"
                        ),
                    }
                )
            elif event_type == "OBSERVATION":
                messages.append({"role": "user", "content": f"[PHYSICAL_ENVIRONMENT_FEEDBACK] 执行结果: {event_data}"})

        messages.append({"role": "user", "content": prompt})
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=tensor.budget.max_tokens if tensor.budget else 2048,
                timeout=self.request_timeout_seconds,
            )
            raw = response.choices[0].message.content
            result_content = raw if raw is not None else ""
            tokens_used = response.usage.total_tokens if response.usage else 0
            return result_content, tokens_used
        except Exception as exc:
            return f"[Tool Error] 外部神经链接异常: {str(exc)}", 10
