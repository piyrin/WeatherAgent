"""
=============================================================================
Tool 调用日志模型 — 记录 Agent 每次工具调用的完整信息
=============================================================================
职责：
  1. 记录 Agent 调用了哪个工具（tool_name）
  2. 记录工具的输入参数（tool_input_json）
  3. 记录工具的输出结果（tool_output_json）
  4. 记录调用耗时和执行状态（duration_ms, status）
  5. 关联到触发的消息（message_id）

Agent 核心价值：
  - 审计追溯：出问题时可以精确重现 Agent 的工具调用链路
  - 前端展示："Agent 过程"面板需要展示中间工具调用步骤
  - 性能监控：统计各工具的调用耗时和成功率
  - 成本分析：统计 LLM + Tool 的综合成本
=============================================================================
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, TimestampMixin

if TYPE_CHECKING:
    from app.models.message import Message


class ToolCallLog(BaseModel, TimestampMixin):
    """
    Tool 调用日志表

    字段说明：
      - id:                UUID 主键
      - message_id:        触发此工具调用的消息 ID（外键 → messages.id）
      - tool_name:         被调用的工具名称（如 "weather", "date_parser"）
      - tool_input_json:   工具入参（JSON 格式，方便前端展示和审计）
      - tool_output_json:  工具出参（JSON 格式）
      - tool_output_text:  工具输出的可读文本（用于前端直接展示）
      - status:            调用状态（success / error / timeout）
      - error_message:     错误信息（仅 status=error 时有值）
      - duration_ms:       调用耗时（毫秒）
      - retry_count:       重试次数（默认 0）

    索引策略：
      - message_id 索引：按消息查询关联的工具调用记录（高频操作）
      - tool_name + status 复合索引：工具级性能监控
      - created_at 索引：时间范围查询
    """

    __tablename__ = "tool_call_logs"

    # ---- 字段定义 ----

    message_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="触发此工具调用的消息 ID",
    )

    tool_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="工具名称（如 weather / date_parser）",
    )

    tool_input_json: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=None,
        comment="工具输入参数（JSON 格式）",
    )

    tool_output_json: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=None,
        comment="工具输出结果（JSON 格式）",
    )

    tool_output_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
        comment="工具输出的可读文本（用于前端直接展示）",
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="success",
        nullable=False,
        comment="调用状态：success / error / timeout",
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
        comment="错误信息（仅 status=error 时填充）",
    )

    duration_ms: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        default=None,
        comment="Tool 调用耗时（毫秒）",
    )

    retry_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="重试次数",
    )

    # ---- 关系定义 ----

    # 多对一：每条工具调用日志属于一条消息
    message: Mapped["Message"] = relationship(
        "Message",
        back_populates="tool_calls",
    )

    # ---- 辅助方法 ----

    @classmethod
    def create_success(
        cls,
        message_id: str,
        tool_name: str,
        tool_input: dict | None,
        tool_output: dict | None,
        output_text: str | None,
        duration_ms: float,
    ) -> "ToolCallLog":
        """
        工厂方法：快速创建一条成功的工具调用日志
        """
        return cls(
            id=str(uuid.uuid4()),
            message_id=message_id,
            tool_name=tool_name,
            tool_input_json=tool_input,
            tool_output_json=tool_output,
            tool_output_text=output_text,
            status="success",
            duration_ms=duration_ms,
        )

    @classmethod
    def create_error(
        cls,
        message_id: str,
        tool_name: str,
        tool_input: dict | None,
        error_message: str,
        duration_ms: float,
    ) -> "ToolCallLog":
        """
        工厂方法：快速创建一条失败的工具调用日志
        """
        return cls(
            id=str(uuid.uuid4()),
            message_id=message_id,
            tool_name=tool_name,
            tool_input_json=tool_input,
            status="error",
            error_message=error_message,
            duration_ms=duration_ms,
        )

    def __repr__(self) -> str:
        return (
            f"<ToolCallLog(id={self.id}, tool={self.tool_name}, "
            f"status={self.status}, duration={self.duration_ms}ms)>"
        )
