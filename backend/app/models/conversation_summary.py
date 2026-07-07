"""
=============================================================================
对话摘要模型 — 存储长对话的周期性摘要快照
=============================================================================
职责：
  1. 存储对话摘要文本（由 ChatMemory 定期生成）
  2. 标记摘要覆盖的消息范围（start_message_id → end_message_id）
  3. 支持增量摘要（rolling summary）：新摘要叠加旧摘要

Memory 模块使用方式：
  - ChatMemory 检测到消息超过阈值时，调用 LLM 生成摘要
  - 摘要持久化到此表，后续轮次直接读取（避免重复生成）
  - 查询时按 created_at 排序，取最新摘要作为上下文前缀
=============================================================================
"""

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel, TimestampMixin


class ConversationSummary(BaseModel, TimestampMixin):
    """
    对话摘要快照表

    字段说明：
      - id:               UUID 主键
      - conversation_id:  所属会话 ID（外键 → conversations.id）
      - summary_text:     摘要文本（由 LLM 生成的自然语言描述）
      - summary_type:     摘要类型（见下方枚举说明）
      - start_message_id: 摘要覆盖的起始消息 ID
      - end_message_id:   摘要覆盖的结束消息 ID
      - message_count:    被摘要覆盖的消息条数
      - token_count:      摘要文本的 token 估算值（用于 Token 预算计算）

    摘要类型说明：
      - "rolling":    滚动摘要，每次新消息达到阈值时更新（覆盖全部历史）
      - "incremental": 增量摘要，只摘要新增的消息段（不覆盖已有摘要）
      - "final":      会话结束时的最终摘要（归档用）

    索引策略：
      - conversation_id 索引：按会话查询摘要（高频操作）
    """

    __tablename__ = "conversation_summaries"

    # ---- 字段定义 ----

    conversation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属会话 ID",
    )

    summary_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        comment="摘要文本",
    )

    summary_type: Mapped[str] = mapped_column(
        String(20),
        default="rolling",
        nullable=False,
        comment="摘要类型：rolling / incremental / final",
    )

    start_message_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        default=None,
        comment="摘要覆盖的起始消息 ID",
    )

    end_message_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        default=None,
        comment="摘要覆盖的结束消息 ID",
    )

    message_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="被摘要覆盖的消息条数",
    )

    token_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="摘要文本的 Token 估算值",
    )

    # ---- 辅助方法 ----

    def __repr__(self) -> str:
        return (
            f"<ConversationSummary(id={self.id}, type={self.summary_type}, "
            f"messages={self.message_count}, tokens={self.token_count})>"
        )
