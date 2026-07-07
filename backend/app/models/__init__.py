"""
=============================================================================
数据层 — ORM 模型定义
=============================================================================
导入顺序很重要：先导入 base（定义 Base 和 Mixin），再导入具体模型。
这样 app/core/database.py 中的 init_db() 才能发现所有模型并自动建表。
=============================================================================
"""

from app.models.base import BaseModel, TimestampMixin
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.tool_call_log import ToolCallLog

# 导出所有模型，方便外部通过 `from app.models import Conversation` 使用
__all__ = [
    "BaseModel",
    "TimestampMixin",
    "Conversation",
    "Message",
    "ToolCallLog",
]
