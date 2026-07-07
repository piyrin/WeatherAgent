"""
=============================================================================
聊天请求/响应 Schema — 聊天接口的输入输出契约
=============================================================================
职责：
  1. ChatRequest：用户发送消息的请求体
  2. ChatResponse：一次完整聊天的响应体（含 Agent 思考过程）
  3. ToolCallRecord：单次工具调用的记录（前端 Agent 过程面板展示）
  4. AgentProcess：Agent 执行过程摘要

Agent 核心设计：
  - ChatResponse 不仅包含最终回答，还包含 Agent 的思考过程和工具调用记录
  - 前端可以根据 tool_calls 列表渲染"Agent 过程"面板
  - conversation_id 在首次对话时自动生成并返回，后续对话复用此 ID
=============================================================================
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# =============================================================================
# 请求体
# =============================================================================


class ChatRequest(BaseModel):
    """
    聊天请求体

    字段说明：
      - message:         用户输入的自然语言文本（必填）
      - conversation_id: 会话 ID（可选，不传则自动创建新会话）
      - stream:          是否启用流式输出（预留，当前返回 False）

    校验规则：
      - message 不能为空（min_length=1）
      - message 不能超过 2000 字符（防止恶意超长输入）

    示例：
        {
            "message": "明天北京天气怎么样？适合出门吗？",
            "conversation_id": "550e8400-e29b-41d4-a716-446655440000"
        }
    """

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
# 响应体
# =============================================================================


class ToolCallRecord(BaseModel):
    """
    单次工具调用记录

    此信息来自 tool_call_logs 表，用于前端 Agent 过程面板展示。

    字段说明：
      - tool_name:   工具名称（如 "weather", "route_planner"）
      - tool_input:  工具输入参数
      - tool_output: 工具输出（结构化 JSON 或文本）
      - status:      调用状态（success / error）
      - duration_ms: 调用耗时（毫秒）
    """

    tool_name: str = Field(..., description="工具名称")
    tool_input: Optional[dict] = Field(default=None, description="工具输入参数")
    tool_output: Optional[Any] = Field(default=None, description="工具输出")
    status: str = Field(default="success", description="调用状态")
    duration_ms: Optional[float] = Field(default=None, description="调用耗时（毫秒）")


class AgentProcess(BaseModel):
    """
    Agent 执行过程摘要

    用于前端"Agent 思考过程"面板展示：
      - 用户输入 → Agent 理解意图 → 制定计划 → 调用工具 → 观察结果 → 生成回答

    字段说明：
      - plan:       Agent 生成的执行计划（文字描述）
      - steps:      执行步骤列表（按时间顺序）
      - tool_calls: 工具调用记录列表
    """

    plan: str = Field(default="", description="Agent 执行计划")
    steps: list[str] = Field(default_factory=list, description="执行步骤描述")
    tool_calls: list[ToolCallRecord] = Field(
        default_factory=list,
        description="工具调用记录列表",
    )


class ChatResponse(BaseModel):
    """
    聊天响应体 — 一次完整聊天的返回

    字段说明：
      - conversation_id: 会话 ID（前端需要保存以便后续对话复用）
      - message:         Agent 最终回答文本
      - agent_process:   Agent 执行过程（思考过程 + 工具调用记录）
      - message_id:      回答消息的 ID（用于后续引用）
      - created_at:      回答时间

    示例：
        {
            "conversation_id": "550e8400-...",
            "message": "明天北京晴转多云，气温 18~26°C，非常适合出门...",
            "agent_process": {
                "plan": "先查天气，再给出建议",
                "steps": ["解析日期", "查询天气", "生成建议"],
                "tool_calls": [
                    {"tool_name": "date_parser", "status": "success", ...},
                    {"tool_name": "weather", "status": "success", ...}
                ]
            },
            "message_id": "660e8400-...",
            "created_at": "2026-07-07T12:00:00Z"
        }
    """

    conversation_id: str = Field(..., description="会话 ID")
    message: str = Field(..., description="Agent 最终回答")
    agent_process: AgentProcess = Field(
        default_factory=AgentProcess,
        description="Agent 执行过程",
    )
    message_id: Optional[str] = Field(default=None, description="回答消息 ID")
    created_at: Optional[str] = Field(default=None, description="创建时间（ISO 8601 格式）")
