from typing import Any, Dict, Optional, Tuple

from pydantic import ValidationError

from core_aegis.aegis_egress import ACCSignal, IntentSignal, ToolRiskProfile, AegisEgressGateway
from core_aegis.config import DEFAULT_EGRESS_EQUATION_CONFIG, TOOL_CRITICALITY_SCORES, EgressEquationConfig
from protocol_schema import ActionType, AegisDecision, AegisIngressPayload, DecisionStatus, NoesisActionRequest, ToolCallPayload


class EgressGate:
    """Aegis egress arbiter: equation-only risk verdict + hard guards."""

    def __init__(
        self,
        safe_tools: Optional[list[str]] = None,
        equation_config: Optional[EgressEquationConfig] = None,
        tool_criticality_scores: Optional[Dict[str, float]] = None,
    ) -> None:
        self._safe_tools = list(safe_tools or ["query_db"])
        self._equation_config = equation_config or DEFAULT_EGRESS_EQUATION_CONFIG
        self._tool_criticality_scores = dict(TOOL_CRITICALITY_SCORES)
        if tool_criticality_scores:
            self._tool_criticality_scores.update(
                {name: float(score) for name, score in tool_criticality_scores.items()}
            )
        self._equation_gateway = AegisEgressGateway(
            r_max=self._equation_config.r_max,
            decay_factor=self._equation_config.decay_factor,
            kappa=self._equation_config.kappa,
            momentum_tau=self._equation_config.momentum_tau,
        )

    def _build_acc_signal(self, request: NoesisActionRequest) -> ACCSignal:
        drift = float(request.action_payload.get("acc_s_score", request.action_payload.get("acc_conflict_score", 0.0)) or 0.0)
        entropy = float(request.action_payload.get("acc_entropy_score", request.logical_entropy) or request.logical_entropy)
        return ACCSignal(drift=drift, entropy=entropy)

    def _tool_criticality_score(self, request: NoesisActionRequest) -> float:
        if request.proposed_action != ActionType.TOOL_CALL:
            return 0.15
        tool_name = str(request.action_payload.get("tool_name") or "")
        if tool_name in self._tool_criticality_scores:
            return float(self._tool_criticality_scores[tool_name])
        if "refund" in tool_name or "write" in tool_name or "delete" in tool_name:
            return 0.75
        return 0.45

    def _build_intent_signal(self, request: NoesisActionRequest) -> IntentSignal:
        return IntentSignal(
            action=request.proposed_action.value,
            tool=ToolRiskProfile(criticality_score=self._tool_criticality_score(request)),
        )

    def _reject(
        self,
        request: NoesisActionRequest,
        *,
        reason: str,
        penalty_log: str,
        remaining_tokens: int,
    ) -> AegisDecision:
        return AegisDecision(
            session_id=request.session_id,
            status=DecisionStatus.REJECTED,
            rejection_reason=reason,
            penalty_log=penalty_log,
            remaining_budget_tokens=remaining_tokens,
        )

    def decide(
        self,
        request: NoesisActionRequest,
        ingress: AegisIngressPayload,
        session_policy_state: Dict[str, Any],
    ) -> Tuple[AegisDecision, Dict[str, Any]]:
        budget = ingress.budget
        remaining_tokens = max(0, budget.max_tokens - request.step_count * 100)

        if request.step_count > budget.max_steps:
            return (
                AegisDecision(
                    session_id=request.session_id,
                    status=DecisionStatus.HARD_MELTDOWN,
                    rejection_reason="step_count exceeds max_steps budget",
                    penalty_log="Budget meltdown: runtime cut power due to step overflow.",
                    remaining_budget_tokens=0,
                ),
                session_policy_state,
            )

        if session_policy_state.get("hijack_flag", False):
            return (
                AegisDecision(
                    session_id=request.session_id,
                    status=DecisionStatus.HARD_MELTDOWN,
                    rejection_reason="ingress detected control-hijack attempt",
                    penalty_log="Aegis hard block: hijack flag raised at ingress gate.",
                    remaining_budget_tokens=remaining_tokens,
                ),
                session_policy_state,
            )

        if request.proposed_action == ActionType.TOOL_CALL:
            try:
                tool_payload = ToolCallPayload.model_validate(request.action_payload)
            except ValidationError as exc:
                return (
                    self._reject(
                        request,
                        reason=f"invalid tool payload: {exc.errors()}",
                        penalty_log="Malformed tool payload blocked by schema guard.",
                        remaining_tokens=remaining_tokens,
                    ),
                    session_policy_state,
                )
            if tool_payload.tool_name not in ingress.allowed_tools:
                return (
                    self._reject(
                        request,
                        reason=f"tool '{tool_payload.tool_name}' blocked: tool not in allowed_tools whitelist",
                        penalty_log="Unauthorized tool request blocked. Re-plan with allowed_tools.",
                        remaining_tokens=remaining_tokens,
                    ),
                    session_policy_state,
                )

        acc_signal = self._build_acc_signal(request)
        intent_signal = self._build_intent_signal(request)
        approved = self._equation_gateway.arbitrate(intent=intent_signal, acc_signal=acc_signal)
        effective_risk = float(self._equation_gateway.last_effective_risk)
        trust_level = max(0.0, min(1.0, 1.0 - (effective_risk / max(self._equation_gateway.R_MAX, 1e-9))))
        icu_mode = effective_risk >= (self._equation_gateway.R_MAX * self._equation_config.icu_ratio)

        session_policy_state["effective_risk"] = effective_risk
        session_policy_state["trust_level"] = trust_level
        session_policy_state["icu_mode"] = icu_mode

        request.action_payload["effective_risk"] = effective_risk
        request.action_payload["trust_level"] = trust_level
        request.action_payload["icu_mode"] = icu_mode

        if not approved:
            return (
                self._reject(
                    request,
                    reason=(
                        "egress equation veto: "
                        f"effective_risk={effective_risk:.4f} >= R_MAX={self._equation_gateway.R_MAX:.4f}"
                    ),
                    penalty_log=(
                        "[EGRESS_VETO] Non-linear risk equation blocked this intent. "
                        "Reduce drift/entropy and propose a lower-criticality action."
                    ),
                    remaining_tokens=remaining_tokens,
                ),
                session_policy_state,
            )

        return (
            AegisDecision(
                session_id=request.session_id,
                status=DecisionStatus.APPROVED,
                executed_action=request.proposed_action,
                executed_payload=request.action_payload,
                remaining_budget_tokens=remaining_tokens,
            ),
            session_policy_state,
        )
