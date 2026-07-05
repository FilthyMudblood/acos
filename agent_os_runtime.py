import asyncio
from typing import Any, Awaitable, Callable, Dict, Optional, Union

from pydantic import ValidationError

from protocol_schema import (
    ActionType,
    AegisDecision,
    DecisionStatus,
    NoesisActionRequest,
    NoesisActionIntent,
    PhysicalExecutionResult,
    PulseSnapshot,
    ToolCallPayload,
    ControlAction,
)

from core_aegis.gateway_runtime import AegisGatewayRuntime
from core_noesis.noesis_kernel import NoesisRuntimeKernel
from core_runtime.runtime_stack import (
    DEFAULT_RUNTIME_CONTROL_CONFIG,
    ObjectiveEmbeddingProvider,
    PhysicalToolRegistry,
    RootObjectiveTensor,
    RuntimeStateBus,
    ToolSpec,
    build_global_tool_registry,
    prepare_sandbox_environment,
)
from core_vitals.acc_monitor import UnifiedACCMonitor
from core_vitals.metabolism_circuit_breaker import HypothalamusPulseListener
from agentos_state.global_state_tensor import DampingSignal, GlobalStateTensor
from agentos_state.topological_bus import TopologicalBus


ToolHandler = Callable[..., Awaitable[Dict[str, Any]]]


# ==========================================
# Default physical tool adapters.
# Production hosts can inject a configured PhysicalToolRegistry into run_agent_os_once.
# ==========================================
async def api_query_db(query: str) -> Dict[str, Any]:
    """Default local database-query adapter used for development and tests."""
    await asyncio.sleep(0.1)
    return {
        "status": "success",
        "rows_returned": 2,
        "data": [{"id": 1, "val": "A"}, {"id": 2, "val": "B"}],
        "query": query,
    }


async def api_refund_lookup(order_id: str) -> Dict[str, Any]:
    """Default refund lookup adapter used for development and tests."""
    await asyncio.sleep(0.2)
    if not str(order_id).startswith("ORD"):
        raise ValueError(f"Invalid order ID format: {order_id}")
    return {"status": "success", "refund_amount": 128.50, "currency": "USD", "order_id": order_id}


DEFAULT_PHYSICAL_TOOL_HANDLERS: Dict[str, ToolHandler] = {
    "query_db": api_query_db,
    "refund_lookup": api_refund_lookup,
}


def build_default_physical_tool_registry() -> PhysicalToolRegistry:
    return PhysicalToolRegistry(
        [
            ToolSpec(
                name="query_db",
                handler=api_query_db,
                capabilities={"read", "query", "lookup"},
                description="Read-only database query adapter.",
                criticality_score=0.25,
            ),
            ToolSpec(
                name="refund_lookup",
                handler=api_refund_lookup,
                capabilities={"read", "lookup", "act", "refund"},
                description="Refund lookup adapter.",
                criticality_score=0.65,
            ),
        ]
    )


# Backward-compatible handler map for tests/imports that still reference the old name.
PHYSICAL_TOOL_REGISTRY: Dict[str, ToolHandler] = DEFAULT_PHYSICAL_TOOL_HANDLERS


def _map_intent_to_action(intent: NoesisActionIntent) -> ActionType:
    if intent.action_type == ControlAction.TOOL_CALL:
        return ActionType.TOOL_CALL
    if intent.action_type == ControlAction.FINAL_ANSWER:
        return ActionType.MEMORY_WRITE
    return ActionType.YIELD


def _estimate_logical_entropy(tensor: GlobalStateTensor) -> float:
    if tensor.active_damping_signals:
        return max(0.0, min(1.0, float(tensor.active_damping_signals[-1].entropy_score)))
    if tensor.budget and tensor.budget.max_steps > 0:
        return max(0.0, min(1.0, len(tensor.pfc_trace) / tensor.budget.max_steps))
    return 0.0


def _build_noesis_request(
    session_id: str, step_count: int, intent: NoesisActionIntent, logical_entropy: float
) -> NoesisActionRequest:
    payload: Dict[str, Any] = {
        "tool_name": intent.tool_name,
        "parameters": intent.parameters,
        "final_answer": intent.final_answer,
    }
    return NoesisActionRequest(
        session_id=session_id,
        step_count=step_count,
        logical_entropy=logical_entropy,
        proposed_action=_map_intent_to_action(intent),
        action_payload=payload,
        reasoning_trajectory=intent.thought_summary or "no_reasoning",
    )


def _calculate_adaptive_threshold(base_threshold: float, drift: float) -> float:
    """Increase pruning pressure as drift rises."""
    return max(0.0, min(0.95, base_threshold + drift * 0.25))


def _resolve_root_objective_text(tensor: GlobalStateTensor, user_input: str) -> str:
    """
    Resolve root objective text across tensor schema variants.
    Keeps runtime robust when tensor implementation lacks `root_objective`.
    """
    direct = getattr(tensor, "root_objective", None)
    if isinstance(direct, str) and direct.strip():
        return direct.strip()

    meta_obj = tensor.metadata.get("root_objective") if isinstance(tensor.metadata, dict) else None
    if isinstance(meta_obj, str) and meta_obj.strip():
        return meta_obj.strip()

    raw = getattr(tensor, "raw_input", None)
    if isinstance(raw, str) and raw.strip():
        return raw.strip()

    return str(user_input or "").strip()


def _is_egress_equation_veto(decision: AegisDecision) -> bool:
    if decision.status != DecisionStatus.REJECTED:
        return False
    reason = str(decision.rejection_reason or "").lower()
    return "egress equation veto" in reason


def _classify_noesis_terminate_cause(thought_summary: str) -> str:
    summary = str(thought_summary or "").lower()
    if any(token in summary for token in ["sql", "注入", "drop table", "1=1", ";--"]):
        return "AGENT_OS_NOESIS_TERMINATE: SQL_INJECTION_HEURISTIC"
    if any(token in summary for token in ["逻辑熵", "paradox", "死胡同"]):
        return "AGENT_OS_NOESIS_TERMINATE: ENTROPY_GUARD"
    if summary in {"", "no_trace", "none"}:
        return "AGENT_OS_NOESIS_TERMINATE: EMPTY_TRACE"
    return "AGENT_OS_NOESIS_TERMINATE: NO_VALID_INTENT_EXTRACTED"


def _build_tool_call_audit(
    decision: AegisDecision,
    tool_name: str,
    params: Dict[str, Any],
    result: PhysicalExecutionResult,
) -> Dict[str, Any]:
    payload = decision.executed_payload or {}
    return {
        "tool_name": tool_name,
        "input": dict(params),
        "ok": bool(result.ok),
        "output": result.tool_result if result.ok else None,
        "error": result.error,
        "decision": {
            "status": decision.status.value,
            "executed_action": decision.executed_action.value if decision.executed_action else None,
            "remaining_budget_tokens": decision.remaining_budget_tokens,
            "rejection_reason": decision.rejection_reason,
        },
        "risk": {
            "effective_risk": float(payload.get("effective_risk", 0.0) or 0.0),
            "trust_level": float(payload.get("trust_level", 1.0) or 1.0),
            "icu_mode": bool(payload.get("icu_mode", False)),
            "acc_conflict_score": float(payload.get("acc_conflict_score", 0.0) or 0.0),
            "acc_conflict_alert": bool(payload.get("acc_conflict_alert", False)),
        },
    }


async def _execute_physical_action(
    decision: AegisDecision,
    tool_registry: PhysicalToolRegistry,
) -> tuple[PhysicalExecutionResult, Optional[Dict[str, Any]]]:
    """
    AgentOS syscall dispatcher.
    Converts Aegis decisions into real physical actions with fault isolation.
    """
    if decision.executed_action == ActionType.TOOL_CALL:
        payload = decision.executed_payload or {}
        try:
            tool_payload = ToolCallPayload.model_validate(payload)
        except ValidationError as exc:
            return (
                PhysicalExecutionResult(
                    ok=False,
                    error=f"API Error (PayloadValidation): {exc.errors()}",
                ),
                None,
            )

        tool_name = tool_payload.tool_name
        params = tool_payload.parameters

        tool_func = tool_registry.get_handler(tool_name)
        if tool_func is None:
            result = PhysicalExecutionResult(
                ok=False,
                error=(
                    f"CRITICAL: Tool '{tool_name}' authorized but missing in "
                    "PhysicalToolRegistry."
                ),
            )
            return result, _build_tool_call_audit(decision, tool_name, params, result)

        try:
            tool_result = await tool_func(**params)
            result = PhysicalExecutionResult(ok=True, tool_result=tool_result)
            return result, _build_tool_call_audit(decision, tool_name, params, result)
        except Exception as exc:
            result = PhysicalExecutionResult(
                ok=False,
                error=f"API Error ({type(exc).__name__}): {str(exc)}",
            )
            return result, _build_tool_call_audit(decision, tool_name, params, result)

    if decision.executed_action == ActionType.MEMORY_WRITE:
        return PhysicalExecutionResult(ok=True, persisted=True), None
    return PhysicalExecutionResult(ok=True), None


async def run_agent_os_once(
    user_input: str,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    return_diagnostics: bool = False,
    enable_egress: bool = True,
    enable_hypothalamus: bool = True,
    enable_acc: bool = True,
    compiled_tool_matrix: Optional[tuple[list[str], Any]] = None,
    objective_embedding: Optional[Any] = None,
    objective_embedding_provider: Optional[ObjectiveEmbeddingProvider] = None,
    physical_tool_registry: Optional[PhysicalToolRegistry] = None,
) -> Union[str, Dict[str, Any]]:
    active_tool_registry = physical_tool_registry or build_default_physical_tool_registry()
    tool_handlers = active_tool_registry.as_handler_map()
    aegis = AegisGatewayRuntime(
        default_tools=active_tool_registry.get_tool_names(),
        tool_criticality_scores=active_tool_registry.as_criticality_map(),
    )
    noesis = NoesisRuntimeKernel(api_key=api_key, base_url=base_url)
    runtime_config = DEFAULT_RUNTIME_CONTROL_CONFIG
    state_bus = RuntimeStateBus(config=runtime_config)
    global_tool_registry = build_global_tool_registry(
        tool_handlers,
        config=runtime_config,
        compiled_tool_matrix=compiled_tool_matrix,
        capability_map=active_tool_registry.as_capability_map(),
    )

    ingress = aegis.ingress_gate(user_input)
    pulse_bus = TopologicalBus()
    hypothalamus = HypothalamusPulseListener(base_budget=ingress.budget.max_tokens)
    acc_monitor = UnifiedACCMonitor(entropy_threshold=0.75, conflict_threshold=0.7)
    if enable_hypothalamus:
        pulse_bus.attach("hypothalamus", hypothalamus.on_pulse)
    if enable_acc:
        pulse_bus.attach("acc", acc_monitor.on_pulse)
    tensor = noesis.bootstrap_from_ingress(ingress)
    root_objective_text = _resolve_root_objective_text(tensor, user_input)
    objective_text = f"{user_input} {root_objective_text}".strip()
    resolved_objective_embedding = objective_embedding
    if objective_embedding_provider is not None:
        resolved_objective_embedding = objective_embedding_provider.get_objective_embedding(objective_text)
    root_objective_tensor = RootObjectiveTensor(
        objective_text,
        embedding_dim=runtime_config.embedding_dim,
        embedding_vector=resolved_objective_embedding,
    )

    step = 0
    rejected_count = 0
    actual_tokens_consumed = 0
    estimated_tokens_consumed = 0
    latest_acc_entropy_score = 0.0
    latest_acc_conflict_score = 0.0
    latest_effective_risk = 0.0
    latest_trust_level = 1.0
    latest_icu_mode = False
    latest_physical_gate_status = "NORMAL_EXECUTION"
    latest_semantic_intent_status = "UNKNOWN"
    latest_termination_cause = ""
    base_pruning_threshold = runtime_config.base_pruning_threshold
    hard_drift_threshold = runtime_config.hard_drift_threshold
    current_pruning_threshold = base_pruning_threshold
    last_trace_len = 0
    tool_invocation_audit: list[Dict[str, Any]] = []
    emitted_pulse_count = 0

    async def _emit_runtime_pulse(
        *,
        pulse_step: int,
        logical_entropy_value: float,
        retries: int,
        step_payload: Dict[str, Any],
        terminal: bool = False,
        terminal_cause: str = "",
    ) -> None:
        nonlocal emitted_pulse_count
        pulse_step_data = dict(step_payload)
        pulse_step_data["terminal"] = bool(terminal)
        if terminal_cause:
            pulse_step_data["terminal_cause"] = terminal_cause
        pulse_snapshot = PulseSnapshot(
            step=pulse_step,
            current_tokens=actual_tokens_consumed,
            logical_entropy=logical_entropy_value,
            retries=retries,
            tci_score=ingress.budget.tci_score,
            last_step_data=pulse_step_data,
        )
        emitted_pulse_count += 1
        await tensor.update_metadata(
            {
                "last_pulse_snapshot": pulse_snapshot.model_dump(),
                "pulse_count": emitted_pulse_count,
            }
        )
        await pulse_bus.broadcast_pulse(
            tensor=tensor,
            snapshot=pulse_snapshot,
        )

    while not tensor.is_resolved:
        step += 1
        if step > ingress.budget.max_steps:
            latest_termination_cause = "AGENT_OS_TIMEOUT: MAX_STEP_REACHED"
            latest_physical_gate_status = "SYSTEM_TIMEOUT"
            await _emit_runtime_pulse(
                pulse_step=step,
                logical_entropy_value=_estimate_logical_entropy(tensor),
                retries=rejected_count,
                step_payload={
                    "logical_entropy": _estimate_logical_entropy(tensor),
                    "proposed_action": ActionType.YIELD.value,
                    "action_payload": {},
                    "reasoning_trajectory": "max step reached before Noesis step",
                    "allowed_tools": list(ingress.allowed_tools),
                },
                terminal=True,
                terminal_cause=latest_termination_cause,
            )
            await tensor.resolve(
                output="[REJECTED][终止][SYSTEM_TIMEOUT] Max step reached.",
                attractor_name="AGENT_OS_TIMEOUT",
            )
            break

        logical_entropy = _estimate_logical_entropy(tensor)
        current_phase_caps = state_bus.get_current_phase_capabilities(
            logical_entropy=logical_entropy,
            conflict_score=latest_acc_conflict_score,
        )
        sandbox_tools = prepare_sandbox_environment(
            dynamic_threshold=current_pruning_threshold,
            current_phase_caps=current_phase_caps,
            root_objective_tensor=root_objective_tensor,
            global_tool_registry=global_tool_registry,
            max_context_tools=runtime_config.max_context_tools,
        )
        ingress.allowed_tools = sandbox_tools or global_tool_registry.get_tool_names()
        await tensor.update_metadata(
            {
                "allowed_tools": list(ingress.allowed_tools),
                "current_phase": str(state_bus.current_phase),
            }
        )
        intent = await noesis.run_step(tensor)
        latest_semantic_intent_status = str(intent.action_type.value or "unknown").upper()
        if len(tensor.pfc_trace) > last_trace_len:
            latest_step = tensor.pfc_trace[-1]
            actual_tokens_consumed += max(0, int(latest_step.metabolic_cost))
            last_trace_len = len(tensor.pfc_trace)
        request = _build_noesis_request(ingress.session_id, step, intent, logical_entropy)
        step_data = {
            "logical_entropy": logical_entropy,
            "proposed_action": request.proposed_action.value,
            "action_payload": request.action_payload,
            "reasoning_trajectory": request.reasoning_trajectory,
            "allowed_tools": ingress.allowed_tools,
        }
        if enable_acc:
            _, conflict_score = acc_monitor.evaluate_scores(step_data)
        else:
            conflict_score = 0.0
        latest_acc_entropy_score = logical_entropy
        latest_acc_conflict_score = conflict_score

        # Closed-loop PFC correction: tighten sandbox on drift.
        drift_value = max(logical_entropy, conflict_score)
        if drift_value > hard_drift_threshold:
            latest_physical_gate_status = "PFC_PRUNING_LOCK"
            latest_termination_cause = "AGENT_OS_PFC_MELTDOWN: UNRECOVERABLE_DRIFT"
            await _emit_runtime_pulse(
                pulse_step=step,
                logical_entropy_value=request.logical_entropy,
                retries=rejected_count,
                step_payload=step_data,
                terminal=True,
                terminal_cause=latest_termination_cause,
            )
            await tensor.resolve(
                output="[PFC_MELTDOWN] Unrecoverable drift. Runtime halted.",
                attractor_name="AGENT_OS_PFC_MELTDOWN",
            )
            break
        if drift_value > acc_monitor.conflict_threshold:
            latest_physical_gate_status = "ACC_SOFT_DAMPING"
            current_pruning_threshold = _calculate_adaptive_threshold(
                base_threshold=base_pruning_threshold,
                drift=drift_value,
            )
            await tensor.inject_damping(
                DampingSignal(
                    entropy_score=min(1.0, drift_value),
                    correction_prompt=(
                        "Goal drift detected by ACC/PFC loop. "
                        "Sandbox tightened and current intent discarded."
                    ),
                    temperature_delta=-0.12,
                )
            )
            continue
        current_pruning_threshold = base_pruning_threshold

        # ACC pre-egress scan: tag risk before Aegis arbitration.
        if enable_acc and conflict_score > acc_monitor.conflict_threshold:
            await tensor.update_metadata(
                {
                    "acc_conflict_alert": True,
                    "s_score": conflict_score,
                }
            )
            request.logical_entropy = max(request.logical_entropy, 0.99)
            latest_acc_entropy_score = request.logical_entropy
        else:
            await tensor.update_metadata(
                {
                    "acc_conflict_alert": False,
                    "s_score": conflict_score,
                }
            )

        request.action_payload["acc_conflict_score"] = conflict_score
        request.action_payload["acc_conflict_alert"] = bool(tensor.metadata.get("acc_conflict_alert", False))
        request.action_payload["acc_s_score"] = float(tensor.metadata.get("s_score", conflict_score) or conflict_score)
        step_data["logical_entropy"] = request.logical_entropy
        # Block 4: Egress collapse arbitration.
        # Only intents that survive this stage can reach physical execution.
        if enable_egress:
            decision = aegis.egress_gate(request, ingress)
        else:
            remaining_budget_tokens = max(0, ingress.budget.max_tokens - step * 100)
            decision = AegisDecision(
                session_id=ingress.session_id,
                status=DecisionStatus.APPROVED,
                executed_action=request.proposed_action,
                executed_payload=request.action_payload,
                remaining_budget_tokens=remaining_budget_tokens,
            )
        estimated_tokens_consumed = max(0, ingress.budget.max_tokens - decision.remaining_budget_tokens)
        policy_snapshot = aegis.get_session_state(ingress.session_id) if enable_egress else {}
        latest_effective_risk = float(policy_snapshot.get("effective_risk", latest_effective_risk) or 0.0)
        latest_trust_level = float(policy_snapshot.get("trust_level", latest_trust_level) or latest_trust_level)
        latest_icu_mode = bool(policy_snapshot.get("icu_mode", latest_icu_mode))

        if decision.status == DecisionStatus.HARD_MELTDOWN:
            latest_physical_gate_status = "HYPOTHALAMUS_MELTDOWN"
            latest_termination_cause = "AGENT_OS_HARD_MELTDOWN: SAFETY_BUDGET_OVERFLOW"
            await _emit_runtime_pulse(
                pulse_step=step,
                logical_entropy_value=request.logical_entropy,
                retries=rejected_count,
                step_payload=step_data,
                terminal=True,
                terminal_cause=latest_termination_cause,
            )
            await tensor.resolve(
                output="[HARD_MELTDOWN][REJECTED][拦截] Runtime terminated due to safety budget overflow.",
                attractor_name="AGENT_OS_HARD_MELTDOWN",
            )
            break

        if _is_egress_equation_veto(decision):
            latest_physical_gate_status = "EGRESS_VETO"
            latest_termination_cause = "AGENT_OS_EGRESS: R_EFFECTIVE_EXCEEDED"
            await _emit_runtime_pulse(
                pulse_step=step,
                logical_entropy_value=request.logical_entropy,
                retries=rejected_count,
                step_payload=step_data,
                terminal=True,
                terminal_cause=latest_termination_cause,
            )
            await tensor.resolve(
                output="[HARD_MELTDOWN][EGRESS_VETO] Egress Gateway vetoed execution.",
                attractor_name="AGENT_OS_EGRESS_VETO_MELTDOWN",
            )
            break

        if decision.status == DecisionStatus.REJECTED:
            latest_physical_gate_status = "EGRESS_VETO"
            latest_termination_cause = "AGENT_OS_EGRESS: TOOL_GUARD_REJECTION"
            rejected_count += 1
            await tensor.inject_damping(
                DampingSignal(
                    entropy_score=request.logical_entropy,
                    correction_prompt=decision.penalty_log or "Action rejected by Aegis.",
                    temperature_delta=-0.1,
                )
            )
            if rejected_count >= 3:
                latest_termination_cause = "AGENT_OS_POLICY_REJECT: RETRY_LIMIT_EXCEEDED"
                await _emit_runtime_pulse(
                    pulse_step=step,
                    logical_entropy_value=request.logical_entropy,
                    retries=rejected_count,
                    step_payload=step_data,
                    terminal=True,
                    terminal_cause=latest_termination_cause,
                )
                await tensor.resolve(
                    output=f"[REJECTED] {decision.penalty_log or decision.rejection_reason or 'Action rejected by Aegis.'}",
                    attractor_name="AGENT_OS_POLICY_REJECT",
                )
                break
            await _emit_runtime_pulse(
                pulse_step=step,
                logical_entropy_value=request.logical_entropy,
                retries=rejected_count,
                step_payload=step_data,
            )
            continue

        execution_result, tool_audit = await _execute_physical_action(decision, active_tool_registry)
        if tool_audit is not None:
            tool_invocation_audit.append(tool_audit)
            await tensor.update_metadata({"tool_invocation_audit": list(tool_invocation_audit)})

        if decision.executed_action == ActionType.TOOL_CALL:
            tool_name = str(request.action_payload.get("tool_name") or "unknown")
            if execution_result.ok:
                obs_data = execution_result.tool_result
                observation_payload = f"[TOOL_SUCCESS] {obs_data}"
                state_bus.on_tool_observation(tool_name=tool_name, succeeded=True)
            else:
                error_message = str(execution_result.error or "tool execution failed")
                observation_payload = (
                    f"[TOOL_EXECUTION_FAILED] {error_message}. Please adjust your strategy."
                )
                state_bus.on_tool_observation(tool_name=tool_name, succeeded=False)
                rejected_count += 1
                await tensor.inject_damping(
                    DampingSignal(
                        entropy_score=min(1.0, request.logical_entropy + 0.2),
                        correction_prompt=f"Tool `{tool_name}` failed: {error_message}. Fix params and retry.",
                        temperature_delta=-0.15,
                    )
                )
                # Deterministic fallback for timeout-like physical faults.
                # This avoids repeated unsafe retries for infrastructure failures.
                if "timeout" in error_message.lower():
                    latest_physical_gate_status = "HYPOTHALAMUS_MELTDOWN"
                    latest_termination_cause = "AGENT_OS_TIMEOUT_FALLBACK: TOOL_TIMEOUT"
                    await _emit_runtime_pulse(
                        pulse_step=step,
                        logical_entropy_value=request.logical_entropy,
                        retries=rejected_count,
                        step_payload=step_data,
                        terminal=True,
                        terminal_cause=latest_termination_cause,
                    )
                    await tensor.resolve(
                        output="系统繁忙，请稍后再试。",
                        attractor_name="AGENT_OS_TIMEOUT_FALLBACK",
                    )
                    break

            if hasattr(tensor, "inject_observation"):
                await tensor.inject_observation(
                    tool_name=tool_name,
                    observation_data=observation_payload,
                )
            else:
                await tensor.inject_memory(
                    [{"source": f"tool::{tool_name}", "content": observation_payload, "type": "observation"}]
                )

        if request.action_payload.get("final_answer"):
            await _emit_runtime_pulse(
                pulse_step=step,
                logical_entropy_value=request.logical_entropy,
                retries=rejected_count,
                step_payload=step_data,
                terminal=True,
                terminal_cause="AGENT_OS_APPROVED_FINAL_ANSWER",
            )
            await tensor.resolve(
                output=str(request.action_payload["final_answer"]),
                attractor_name="AGENT_OS_APPROVED_FINAL_ANSWER",
            )
            break

        if intent.action_type == ControlAction.TERMINATE:
            latest_termination_cause = _classify_noesis_terminate_cause(request.reasoning_trajectory)
            await _emit_runtime_pulse(
                pulse_step=step,
                logical_entropy_value=request.logical_entropy,
                retries=rejected_count,
                step_payload=step_data,
                terminal=True,
                terminal_cause=latest_termination_cause,
            )
            await tensor.resolve(
                output=f"[REJECTED][拦截][终止][TERMINATE] {request.reasoning_trajectory}",
                attractor_name="AGENT_OS_NOESIS_TERMINATE",
            )
            break

        if decision.executed_action == ActionType.YIELD and tensor.pfc_trace:
            latest_thought = str(tensor.pfc_trace[-1].content)
            if "final_answer" in latest_thought.lower():
                await _emit_runtime_pulse(
                    pulse_step=step,
                    logical_entropy_value=request.logical_entropy,
                    retries=rejected_count,
                    step_payload=step_data,
                    terminal=True,
                    terminal_cause="AGENT_OS_YIELD_FINALIZE",
                )
                await tensor.resolve(
                    output=latest_thought,
                    attractor_name="AGENT_OS_YIELD_FINALIZE",
                )
                break

        await _emit_runtime_pulse(
            pulse_step=step,
            logical_entropy_value=request.logical_entropy,
            retries=rejected_count,
            step_payload=step_data,
        )

    final_output = tensor.final_output or "[AgentOS] Loop ended without final_output."
    if return_diagnostics:
        return {
            "final_output": final_output,
            "session_id": ingress.session_id,
            "token_usage": actual_tokens_consumed,
            "actual_token_usage": actual_tokens_consumed,
            "estimated_token_usage": estimated_tokens_consumed,
            "acc_entropy_score": latest_acc_entropy_score,
            "acc_conflict_score": latest_acc_conflict_score,
            "effective_risk": latest_effective_risk,
            "trust_level": latest_trust_level,
            "icu_mode": latest_icu_mode,
            "physical_gate_status": latest_physical_gate_status,
            "semantic_intent_status": latest_semantic_intent_status,
            "termination_cause": latest_termination_cause,
            "runtime_controls": {
                "enable_egress": bool(enable_egress),
                "enable_hypothalamus": bool(enable_hypothalamus),
                "enable_acc": bool(enable_acc),
                "base_pruning_threshold": float(runtime_config.base_pruning_threshold),
                "hard_drift_threshold": float(runtime_config.hard_drift_threshold),
                "max_context_tools": int(runtime_config.max_context_tools),
                "compiled_tool_matrix_injected": bool(compiled_tool_matrix is not None),
                "objective_embedding_injected": bool(resolved_objective_embedding is not None),
                "objective_embedding_provider_injected": bool(objective_embedding_provider is not None),
                "current_phase": str(state_bus.current_phase),
            },
            "tool_invocations": tool_invocation_audit,
            "pulse_count": emitted_pulse_count,
            "last_pulse_snapshot": tensor.metadata.get("last_pulse_snapshot", {}),
            "steps": step,
            "resolved": tensor.is_resolved,
        }
    return final_output


if __name__ == "__main__":
    demo_input = "请帮我查询并退还昨天的云服务器扣费。"
    output = asyncio.run(run_agent_os_once(demo_input))
    print(output)
