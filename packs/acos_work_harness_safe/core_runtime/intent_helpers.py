"""Thin builders for external integrators (Path A SDK)."""

from typing import Any, Dict, Optional

from protocol_schema import (
    ActionType,
    AegisDecision,
    DecisionStatus,
    NoesisActionRequest,
)


def make_tool_call_request(
    *,
    session_id: str,
    step_count: int,
    tool_name: str,
    parameters: Optional[Dict[str, Any]] = None,
    reasoning_trajectory: str = "tool proposal",
    logical_entropy: float = 0.0,
    acc_conflict_score: Optional[float] = None,
    acc_entropy_score: Optional[float] = None,
) -> NoesisActionRequest:
    """
    Build a TOOL_CALL intent for egress_gate without Noesis/internal types.

    Integrators supply session, tool, and params; ACOS owns the request shape.
    Optional ACC scores are placed in action_payload for the Risk Engine.
    """
    if not session_id or not str(session_id).strip():
        raise ValueError("session_id is required")
    if step_count < 0:
        raise ValueError("step_count must be >= 0")
    if not tool_name or not str(tool_name).strip():
        raise ValueError("tool_name is required")
    entropy = float(logical_entropy)
    if entropy < 0.0:
        raise ValueError("logical_entropy must be >= 0.0")
    trajectory = (reasoning_trajectory or "").strip() or "tool proposal"

    payload: Dict[str, Any] = {
        "tool_name": str(tool_name).strip(),
        "parameters": dict(parameters or {}),
    }
    if acc_conflict_score is not None:
        payload["acc_conflict_score"] = float(acc_conflict_score)
    if acc_entropy_score is not None:
        payload["acc_entropy_score"] = float(acc_entropy_score)

    return NoesisActionRequest(
        session_id=str(session_id).strip(),
        step_count=int(step_count),
        logical_entropy=entropy,
        proposed_action=ActionType.TOOL_CALL,
        action_payload=payload,
        reasoning_trajectory=trajectory,
    )


def is_executable(decision: AegisDecision) -> bool:
    """True only when physical dispatch via execute_approved is allowed."""
    return decision.status == DecisionStatus.APPROVED
