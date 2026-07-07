"""
=============================================================================
Memory 模块 — 对话记忆与上下文管理
=============================================================================
职责：
  1. 管理对话历史的加载和格式化
  2. 按 Token 预算智能截断上下文
  3. 自动生成和管理对话摘要
  4. 为 Agent 提供结构化的上下文字符串

架构位置：
  Memory 模块位于 Service 层和 Agent 层之间：
    ChatService → ChatMemory（加载/摘要/格式化）
               → AgentExecutor（接收预格式化的上下文字符串）
               → LangGraph Agent（使用上下文推理）

当前实现：
  - ChatMemory：基于摘要的对话记忆（rolling summary + token 预算管理）

未来扩展：
  - VectorMemory：基于向量检索的长期记忆
  - KnowledgeMemory：知识库增强记忆
=============================================================================
"""

from app.memory.base import BaseMemory
from app.memory.chat_memory import ChatMemory

__all__ = [
    "BaseMemory",
    "ChatMemory",
]
