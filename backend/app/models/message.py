"""
=============================================================================
聊天消息模型 — 会话中每一条对话记录
=============================================================================
职责：
  1. 记录每条消息的角色（用户 / 助手 / 系统 / Agent 工具调用）
  2. 关联到所属会话（多对一）
  3. 关联 Tool 调用日志（一对多）

Agent 相关设计：
  - role 字段支持四种角色：
    ① user：      用户的自然语言输入
    ② assistant： Agent 的最终回答
    ③ system：    系统提示词（首次对话时注入）
    ④ tool：      Agent 中间工具调用阶段（可选，用于调试和展示）
  - content_type 区分纯文本和结构化内容
  - metadata JSON 字段存储 Agent 执行过程元数据（如思考链、工具调用记录）
=============================================================================
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, TimestampMixin

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.tool_call_log import ToolCallLog


class Message(BaseModel, TimestampMixin):
    """
    聊天消息表

    字段说明：
      - id:              UUID 主键
      - conversation_id: 所属会话 ID（外键 → conversations.id）
      - role:            消息角色（user / assistant / system / tool）
      - content:         消息正文（纯文本）
      - content_type:    内容类型（text=纯文本, markdown=Markdown, json=结构化数据）
      - token_count:     此消息消耗的 Token 数（可选，用于成本估算）
      - metadata_json:   扩展元数据（JSON 格式，存储 Agent 思考过程等）
      - created_at:      消息创建时间
    """

    __tablename__ = "messages"

    # ---- 字段定义 ----

    conversation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,      # 按会话查询消息是高频操作，需要索引
        comment="所属会话 ID",
    )

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="消息角色：user / assistant / system / tool",
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        comment="消息内容",
    )

    content_type: Mapped[str] = mapped_column(
        String(20),
        default="text",
        nullable=False,
        comment="内容类型：text / markdown / json",
    )

    token_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        default=None,
        comment="消耗的 Token 数量（可选）",
    )

    metadata_json: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=None,
        comment="扩展元数据（JSON 格式：存储 Agent 思考链、工具调用摘要等）",
    )

    # ---- 关系定义 ----

    # 多对一：每条消息属于一个会话
    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="messages",
    )

    # 一对多：一条消息可能触发多次工具调用
    tool_calls: Mapped[list["ToolCallLog"]] = relationship(
        "ToolCallLog",
        back_populates="message",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ToolCallLog.created_at",
    )

    # ---- 辅助方法 ----

    @classmethod
    def create_user_message(
        cls,
        conversation_id: str,
        content: str,
    ) -> "Message":
        """
        工厂方法：快速创建一条用户消息

        参数：
            conversation_id: 所属会话 ID
            content: 用户输入文本

        返回值：
            Message 实例（尚未持久化到数据库）
        """
        return cls(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role="user",
            content=content,
            content_type="text",
        )

    @classmethod
    def create_assistant_message(
        cls,
        conversation_id: str,
        content: str,
        metadata_json: dict | None = None,
    ) -> "Message":
        """
        工厂方法：快速创建一条助手消息

        参数：
            conversation_id: 所属会话 ID
            content: Agent 返回的文本
            metadata_json: Agent 执行元数据（思考链等），可选

        返回值：
            Message 实例（尚未持久化到数据库）
        """
        return cls(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role="assistant",
            content=content,
            content_type="markdown",  # Agent 输出通常是 Markdown 格式
            metadata_json=metadata_json,
        )

    @classmethod
    def create_system_message(
        cls,
        conversation_id: str,
        content: str,
    ) -> "Message":
        """
        工厂方法：快速创建一条系统消息

        系统消息用于注入 Agent 的 System Prompt，
        仅在会话开始时创建一次。
        """
        return cls(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role="system",
            content=content,
            content_type="text",
        )

    def __repr__(self) -> str:
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<Message(id={self.id}, role={self.role}, content={preview!r})>"
