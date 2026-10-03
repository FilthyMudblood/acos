from enum import Enum
from typing import Annotated, Any, Dict, List, Optional, TypedDict

from pydantic import BaseModel, Field, model_validator


# ==========================================
# Enums: 定义系统级的状态与动作常量
# ==========================================
class ActionType(str, Enum):
    TOOL_CALL = "TOOL_CALL"  # 调用外部物理 API
    MEMORY_READ = "MEMORY_READ"  # 检索记忆
    MEMORY_WRITE = "MEMORY_WRITE"  # 写入记忆
    YIELD = "YIELD"  # 认知挂起/结束当前循环


class ControlAction(str, Enum):
    TOOL_CALL = "tool_call"
    FINAL_ANSWER = "final_answer"
    TERMINATE = "terminate"


class DecisionStatus(str, Enum):
    APPROVED = "APPROVED"  # 允许物理执行
    REJECTED = "REJECTED"  # 驳回并注入惩罚
    OVERRIDE = "OVERRIDE"  # 强制篡改提议动作
    HARD_MELTDOWN = "HARD_MELTDOWN"  # 系统级物理断电


# ==========================================
# Schema 1: Aegis Ingress Payload (入站闸机分配)
# 作用: 远端或本地网关清洗完毕后，带上“预算”和“环境上下文”发给 Noesis。
# ==========================================
class ComputeBudget(BaseModel):
    max_tokens: int = Field(..., gt=0, description="本次生命周期的硬性 Token 预算上限")
    max_steps: int = Field(..., gt=0, description="最大允许推演步数")
    tci_score: float = Field(..., ge=0.0, le=1.0, description="初始威胁情报评分 (0.0-1.0)")


class AegisIngressPayload(BaseModel):
    session_id: str = Field(..., min_length=1, description="全局唯一会话 ID")
    sanitized_input: str = Field(..., description="经过正则与注入检测清洗后的安全输入")
    budget: ComputeBudget = Field(..., description="由中央银行 (Aegis) 分配的算力预算")
    allowed_tools: List[str] = Field(default_factory=list, description="当前上下文动态白名单工具")


# ==========================================
# Schema 2: Noesis Action Request (认知提议)
# 作用: PFC 推演后，失去物理执行权，只能向外发出带审计数据的“提议”。
# ==========================================
class NoesisActionRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    step_count: int = Field(..., ge=0, description="当前所处推演步数，用于与预算校验")
    logical_entropy: float = Field(..., ge=0.0, description="ACC 评估出的当前逻辑熵值")
    proposed_action: ActionType = Field(..., description="提议执行的动作类型")
    action_payload: Dict[str, Any] = Field(default_factory=dict, description="提议动作的具体参数")
    reasoning_trajectory: str = Field(..., min_length=1, description="导致此提议的内在推理轨迹 (CoT)，供审计")


# ==========================================
# Schema 3: Aegis Decision (出站仲裁与制裁)
# 作用: 拦截提议后，返回决定。如果拒绝，必须提供惩罚日志迫使模型重新思考。
# ==========================================
class AegisDecision(BaseModel):
    session_id: str = Field(...)
    status: DecisionStatus = Field(..., description="最终仲裁结果")
    executed_action: Optional[ActionType] = Field(
        None, description="实际被 Aegis 执行的动作 (如果是 OVERRIDE 状态)"
    )
    executed_payload: Optional[Dict[str, Any]] = Field(None, description="实际执行的参数")

    # 认知阻尼与惩罚机制
    rejection_reason: Optional[str] = Field(None, description="如果拒绝，必须提供具体规则违反说明")
    penalty_log: Optional[str] = Field(
        None,
        description="强制塞入 GlobalStateTensor 的反馈信息，包含逻辑指导以纠偏 PFC",
    )
    remaining_budget_tokens: int = Field(..., ge=0, description="当前剩余预算，用于下丘脑本地对账")


# ==========================================
# Schema 4: Tool Call Payload (工具调用载荷)
# 作用: 物理工具执行载荷的强类型约束，锁定 tool_name 与 parameters。
# ==========================================
class ToolCallPayload(BaseModel):
    tool_name: str = Field(..., min_length=1, description="工具名称，必须命中物理注册表")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="工具参数")


# ==========================================
# Schema 5: Physical Execution Result (系统调用回执)
# 作用: Runtime 物理执行后的标准结果结构，避免裸字典键分支。
# ==========================================
class PhysicalExecutionResult(BaseModel):
    ok: bool = Field(..., description="物理执行是否成功")
    tool_result: Optional[Dict[str, Any]] = Field(
        None, description="工具执行成功时的观测数据"
    )
    error: Optional[str] = Field(None, description="工具执行失败时的错误信息")
    persisted: Optional[bool] = Field(None, description="内存写入动作是否成功")


# ==========================================
# Schema 6: Pulse Snapshot (心跳快照)
# 作用: Runtime 在每个循环末尾广播的代谢观测快照。
# ==========================================
class PulseSnapshot(BaseModel):
    step: int = Field(..., ge=0, description="当前循环步数")
    current_tokens: int = Field(..., ge=0, description="累计已消耗 token")
    logical_entropy: float = Field(..., ge=0.0, description="当前逻辑熵")
    retries: int = Field(..., ge=0, description="当前失败重试计数")
    tci_score: float = Field(..., ge=0.0, le=1.0, description="当前 TCI 风险评分")
    last_step_data: Dict[str, Any] = Field(default_factory=dict, description="最近一步认知与动作快照")


class NoesisActionIntent(BaseModel):
    """
    Step-level intent emitted by Noesis cognition.
    Kept in unified protocol schema to avoid dual protocol definitions.
    """

    action_type: ControlAction = Field(..., description="tool_call/final_answer/terminate")
    tool_name: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    final_answer: Optional[str] = None
    thought_summary: str = Field(..., min_length=1, description="Noesis reasoning summary")

    @model_validator(mode="after")
    def validate_action_fields(self) -> "NoesisActionIntent":
        if self.action_type == ControlAction.TOOL_CALL:
            if not self.tool_name:
                raise ValueError("tool_call requires tool_name")
            if self.final_answer is not None:
                raise ValueError("tool_call must not include final_answer")
        elif self.action_type == ControlAction.FINAL_ANSWER:
            if not self.final_answer:
                raise ValueError("final_answer requires final_answer content")
            if self.tool_name is not None:
                raise ValueError("final_answer must not include tool_name")
        elif self.action_type == ControlAction.TERMINATE:
            if self.tool_name is not None or self.final_answer is not None:
                raise ValueError("terminate must not include tool_name/final_answer")
        return self


def override(_: Any, b: Any) -> Any:
    return b


def merge_dicts(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    merged = a.copy() if a else {}
    if b:
        for key, value in b.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = merge_dicts(merged[key], value)
            else:
                merged[key] = value
    return merged


class AegisState(TypedDict, total=False):
    instruction: Annotated[str, override]
    module_name: Annotated[str, override]
    rag_context: Annotated[str, override]
    draft_output: Annotated[str, override]
    final_output: Annotated[str, override]

    api_key: Annotated[str, override]
    base_url: Annotated[str, override]
    temperature: Annotated[float, override]
    enable_kernel: Annotated[bool, override]
    enable_hypo: Annotated[bool, override]
    enable_egress_policy_arbitration: Annotated[bool, override]

    tci: Annotated[float, override]
    tci_score: Annotated[float, override]
    s_score: Annotated[float, override]
    egress_policy_latency: Annotated[float, override]
    acc_arbitration_latency: Annotated[float, override]
    token_usage: Annotated[int, override]
    predicted_tokens: Annotated[int, override]

    hijack_flag: Annotated[bool, override]
    auth_status: Annotated[str, override]
    resolution: Annotated[str, override]
    correction_prompt: Annotated[str, override]
    decision_path: Annotated[List[str], override]

    signals: Annotated[Dict[str, Any], merge_dicts]
    metadata: Annotated[Dict[str, Any], merge_dicts]
