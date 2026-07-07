"""
=============================================================================
Memory 模块 — 对话记忆（已迁移）
=============================================================================

Memory 功能已从 agent 目录迁移到独立的 app/memory/ 模块。

请使用：
    from app.memory import ChatMemory, BaseMemory

用法示例：
    from app.memory import ChatMemory

    memory = ChatMemory(db=session, conversation_id="xxx", llm=my_llm)
    context = memory.load_memory_context()
    memory.maybe_summarize()

设计原因：
  Memory 是独立的业务模块，不属于 Agent 核心。
  将其从 agent/ 目录分离出去，保持 Agent 的纯粹性（Agent 不操作数据库）。
=============================================================================
"""

# 向后兼容：从新位置重新导出
from app.memory import BaseMemory, ChatMemory  # noqa: F401, E402

# 保留此文件是为了：
#  1. 向后兼容（如果已有代码引用此路径）
#  2. 防止未来的开发者在此处恢复旧的占位实现
__all__ = ["BaseMemory", "ChatMemory"]
