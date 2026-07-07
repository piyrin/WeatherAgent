"""
=============================================================================
AgentState 定义 — LangGraph 的状态结构
=============================================================================
职责：
  1. 定义 AgentState TypedDict，包含所有层的字段
  2. 定义子结构类型（Plan、ToolCallRecord、Observation、AgentStep）
  3. 提供状态初始化函数

规范依据：agent_interface_spec.md 第2节
=============================================================================
"""

from typing import TypedDict, List, Dict, Any, Optional, Literal

from langchain_core.messages import BaseMessage


# =============================================================================
# 子结构类型定义
# =============================================================================


class PlanStep(TypedDict):
    """规划中的单个步骤"""
    step_id: int
    action: Literal["call_tool", "observe", "answer"]
    tool_name: Optional[str]
    tool_input: Optional[Dict[str, Any]]
    reason: str
    depends_on: List[int]
    on_failure: Literal["retry_once", "skip_and_notify", "abort"]


class Plan(TypedDict):
    """完整的执行计划（Planner 节点输出）"""
    user_intent: str
    intent_category: Literal["weather_check", "travel_advice", "date_query", "calculation", "general_chat"]
    reasoning: str
    plan: List[PlanStep]
    total_steps: int
    estimated_tools: List[str]


class ToolCallRecord(TypedDict):
    """工具调用记录"""
    step_id: int
    tool_name: str
    tool_input: Dict[str, Any]
    tool_output: Dict[str, Any]
    status: Literal["success", "error", "retrying"]
    retry_count: int
    duration_ms: float


class Observation(TypedDict):
    """观察结果（Observe 节点输出）"""
    step_id: int
    tool_name: str
    observation: str
    extracted_facts: Dict[str, Any]
    need_replan: bool
    replan_reason: Optional[str]
    confidence: float


class AgentStep(TypedDict):
    """给前端的执行步骤（规范第8节）"""
    id: str
    name: str
    status: Literal["pending", "running", "completed", "failed", "retrying"]
    type: Literal["understand", "plan", "tool_call", "observe", "answer"]
    toolName: Optional[str]
    toolInput: Optional[Dict[str, Any]]
    toolOutput: Optional[Dict[str, Any]]
    error: Optional[str]
    retryCount: int


class AgentState(TypedDict):
    """
    LangGraph 中每个 Node 共享的 State 结构

    规范依据：agent_interface_spec.md 第2节
    """
    # -------------------------- 输入层（初始化后只读） --------------------------
    user_message: str
    conversation_id: str
    chat_history: List[BaseMessage]
    current_time: str

    # -------------------------- 推理层（Planner/ReAct 持续更新） --------------------------
    understanding: str
    plan: Optional[Plan]
    plan_revision: int
    messages: List[BaseMessage]
    iteration_count: int

    # -------------------------- 执行层（Tool 调用后写入） --------------------------
    tool_calls: List[ToolCallRecord]
    observations: List[Observation]
    current_action: Optional[str]

    # -------------------------- 控制层（Router/流程控制） --------------------------
    next_action: Literal["plan", "call_tool", "observe", "replan", "answer", "end"]
    should_continue: bool

    # -------------------------- 输出层（最终组装） --------------------------
    final_answer: Optional[str]
    steps: List[AgentStep]
    errors: List[str]


# =============================================================================
# 常量定义
# =============================================================================

MAX_ITERATIONS = 10
MAX_REVISIONS = 3


# =============================================================================
# 状态初始化函数
# =============================================================================


def create_initial_state(
    user_message: str,
    conversation_id: str,
    chat_history: List[BaseMessage],
    current_time: str,
) -> AgentState:
    """
    创建初始 AgentState

    参数：
        user_message:   用户输入消息
        conversation_id:会话 ID
        chat_history:   对话历史
        current_time:   当前时间（ISO 8601 格式）

    返回值：
        初始化后的 AgentState
    """
    return AgentState(
        # 输入层
        user_message=user_message,
        conversation_id=conversation_id,
        chat_history=chat_history,
        current_time=current_time,

        # 推理层
        understanding="",
        plan=None,
        plan_revision=0,
        messages=[],
        iteration_count=0,

        # 执行层
        tool_calls=[],
        observations=[],
        current_action=None,

        # 控制层
        next_action="plan",
        should_continue=True,

        # 输出层
        final_answer=None,
        steps=[],
        errors=[],
    )