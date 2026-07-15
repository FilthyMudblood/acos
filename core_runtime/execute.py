"""Sole physical dispatch entry for approved Aegis decisions."""

from typing import Any, Dict, Optional, Tuple

from pydantic import ValidationError

from protocol_schema import (
    ActionType,
    AegisDecision,
    DecisionStatus,
    PhysicalExecutionResult,
    ToolCallPayload,
)

from .runtime_stack import PhysicalToolRegistry


def build_tool_call_audit(
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


async def execute_approved(
    decision: AegisDecision,
    tool_registry: PhysicalToolRegistry,
) -> Tuple[PhysicalExecutionResult, Optional[Dict[str, Any]]]:
    """
    Dispatch a physical tool action only after an explicit APPROVED decision.

    Fail-closed: non-APPROVED decisions never invoke handlers.
    Returns (result, tool_audit_row | None).
    """
    if decision.status != DecisionStatus.APPROVED:
        return (
            PhysicalExecutionResult(
                ok=False,
                error=(
                    f"Refusing execution: decision status is {decision.status.value}, "
                    "not APPROVED."
                ),
            ),
            None,
        )

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
            return result, build_tool_call_audit(decision, tool_name, params, result)

        try:
            tool_result = await tool_func(**params)
            result = PhysicalExecutionResult(ok=True, tool_result=tool_result)
            return result, build_tool_call_audit(decision, tool_name, params, result)
        except Exception as exc:
            result = PhysicalExecutionResult(
                ok=False,
                error=f"API Error ({type(exc).__name__}): {str(exc)}",
            )
            return result, build_tool_call_audit(decision, tool_name, params, result)

    if decision.executed_action == ActionType.MEMORY_WRITE:
        return PhysicalExecutionResult(ok=True, persisted=True), None
    return PhysicalExecutionResult(ok=True), None
