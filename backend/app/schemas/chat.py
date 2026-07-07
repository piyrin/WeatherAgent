"""
=============================================================================
聊天请求/响应 Schema — 对齐规范第8节
=============================================================================
规范依据：agent_interface_spec.md 第8节（Agent → FastAPI 返回格式）

字段对照：
  - Step 对象：id/name/status/type/toolName/toolInput/toolOutput/error/retryCount
  - tools[]：独立的工具调用记录数组
  - plan：结构化计划对象（intent_category/reasoning/total_steps）
=============================================================================
"""

from datetime import datetime
from typing import Optional, Literal, List, Dict, Any

from pydantic import BaseModel, Field


# =============================================================================
# 请求体
# =============================================================================


class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="用户输入的自然语言文本",
        examples=["明天北京天气怎么样？适合出门吗？"],
    )
    conversation_id: Optional[str] = Field(
        default=None,
        description="会话 ID（可选，不传则自动创建新会话）",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    stream: bool = Field(
        default=False,
        description="是否启用流式输出（预留功能）",
    )


# =============================================================================
# 响应体 — 对齐规范第8节
# =============================================================================


class Step(BaseModel):
    """
    执行步骤（规范第8节 steps[] 中每个 Step 对象的完整字段）
    """
    id: Optional[str] = Field(default=None, description="步骤唯一ID")
    name: str = Field(..., description="步骤显示名称")
    status: Literal["pending", "running", "completed", "failed", "retrying"] = Field(..., description="步骤状态")
    type: Optional[Literal["understand", "plan", "tool_call", "observe", "answer"]] = Field(default=None, description="步骤类型")
    toolName: Optional[str] = Field(default=None, description="工具名称（type=tool_call 时）")
    toolInput: Optional[Dict[str, Any]] = Field(default=None, description="工具输入参数")
    toolOutput: Optional[Dict[str, Any]] = Field(default=None, description="工具返回结果")
    error: Optional[str] = Field(default=None, description="错误信息（status=failed 时）")
    retryCount: Optional[int] = Field(default=0, description="重试次数")


class ToolCallRecord(BaseModel):
    """
    工具调用记录（规范第8节 tools[] 中的对象）
    """
    name: str = Field(..., description="工具名称")
    input: Dict[str, Any] = Field(default_factory=dict, description="工具输入参数")
    output: Optional[Dict[str, Any]] = Field(default=None, description="工具输出结果")
    status: Literal["completed", "failed", "retrying"] = Field(default="completed", description="调用状态")
    duration_ms: Optional[float] = Field(default=None, description="调用耗时（毫秒）")


class PlanSummary(BaseModel):
    """
    执行计划摘要（规范第8节 plan 对象）
    """
    intent_category: Optional[str] = Field(default=None, description="意图分类")
    reasoning: Optional[str] = Field(default=None, description="规划推理过程")
    total_steps: Optional[int] = Field(default=None, description="总步骤数")


class AgentProcess(BaseModel):
    """
    Agent 执行过程摘要（规范第8节 agent_process）
    """
    plan: PlanSummary = Field(default_factory=PlanSummary, description="执行计划摘要")
    steps: List[Step] = Field(default_factory=list, description="执行步骤列表")
    tool_calls: List[ToolCallRecord] = Field(default_factory=list, description="工具调用记录列表")


class ChatResponse(BaseModel):
    """
    聊天响应体 — 对齐规范第8节

    字段说明：
      - conversation_id: 会话 ID
      - message:         Agent 最终回答文本
      - agent_process:   Agent 执行过程（思考过程 + 工具调用记录）
      - message_id:      回答消息的 ID
      - created_at:      回答时间
      - tools:           工具调用记录列表（独立字段，供前端 ToolPanel 使用）
      - total_duration_ms: 总耗时
    """
    conversation_id: str = Field(..., description="会话 ID")
    message: str = Field(..., description="Agent 最终回答")
    agent_process: AgentProcess = Field(default_factory=AgentProcess, description="Agent 执行过程")
    message_id: Optional[str] = Field(default=None, description="回答消息 ID")
    created_at: Optional[str] = Field(default=None, description="创建时间（ISO 8601 格式）")
    tools: List[ToolCallRecord] = Field(default_factory=list, description="工具调用记录列表")
    total_duration_ms: Optional[float] = Field(default=None, description="总耗时（毫秒）")