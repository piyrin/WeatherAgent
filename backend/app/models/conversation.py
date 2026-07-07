"""
=============================================================================
聊天会话模型 — 一次完整的对话对应一条会话记录
=============================================================================
职责：
  1. 记录每个会话的元信息（标题、状态、消息数量）
  2. 与 messages 表建立一对多关系（一个会话有多条消息）

Agent 相关设计：
  - 每个会话是一个独立的 Agent 交互上下文
  - 会话标题由 Agent 首条消息自动生成（或前端传入）
  - is_active 标记会话是否活跃（软删除的替代方案）
=============================================================================
"""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, TimestampMixin

# TYPE_CHECKING 块中的 import 只在类型检查时执行，运行时不会导致循环导入
if TYPE_CHECKING:
    from app.models.message import Message


class Conversation(BaseModel, TimestampMixin):
    """
    聊天会话表

    字段说明：
      - id:           UUID 主键（继承自 BaseModel）
      - title:        会话标题（Agent 自动生成或用户自定义）
      - status:       会话状态（active=活跃, archived=已归档）
      - message_count:会话中的消息总数（冗余字段，方便列表展示时无需 count 查询）
      - created_at:   创建时间（继承自 TimestampMixin）
      - updated_at:   最后更新时间（继承自 TimestampMixin）
    """

    __tablename__ = "conversations"

    # ---- 字段定义 ----

    title: Mapped[str] = mapped_column(
        String(200),
        default="新对话",
        nullable=False,
        comment="会话标题",
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="active",
        nullable=False,
        comment="会话状态：active（活跃）/ archived（已归档）",
    )

    message_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="消息总数（冗余字段，优化列表查询性能）",
    )

    # ---- 关系定义 ----

    # 一对多：一个会话包含多条消息
    # cascade="all, delete-orphan"：删除会话时自动删除关联消息
    # lazy="selectin"：访问 messages 属性时用一条 SQL 加载全部（避免 N+1 问题）
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Message.created_at",
    )

    # ---- 辅助方法 ----

    def increment_message_count(self) -> None:
        """
        消息数量 +1

        在添加新消息后调用，保持 message_count 与 messages 关系同步。
        SQLite 不支持行级触发器，所以用应用层方法替代。
        """
        self.message_count += 1

    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, title={self.title!r}, status={self.status})>"
