"""
=============================================================================
BaseMemory — 对话记忆抽象接口
=============================================================================
职责：
  1. 定义所有 Memory 实现必须遵守的契约接口
  2. 确保 ChatMemory / VectorMemory / KnowledgeMemory 可互换

设计原则：
  - 接口先行（Contract First）：先定义接口，再实现
  - 所有 Memory 实现返回统一的上下文字符串
  - Agent 层不关心 Memory 的具体实现（基于抽象而非具体）
=============================================================================
"""

from abc import ABC, abstractmethod


class BaseMemory(ABC):
    """
    对话记忆抽象基类

    所有 Memory 实现必须实现此接口，确保 ChatService 可以使用
    不同的 Memory 策略而无需修改代码。

    子类必须实现：
      - load_memory_context() → str
      - save_context()
      - clear()
    """

    @abstractmethod
    def load_memory_context(self) -> str:
        """
        加载当前对话的记忆上下文

        返回值：
            格式化后的上下文字符串，直接注入 AgentState.chat_history。
            格式示例：
                [历史对话摘要]
                用户之前咨询了北京和上海的天气，主要关注降雨情况。

                [最近对话]
                用户: 明天去深圳需要带伞吗
                助手: 明天深圳有雷阵雨，建议携带雨具...

        注意：
            返回值可能为空字符串（无历史时）或仅含摘要（无最近消息时）。
        """
        ...

    @abstractmethod
    def save_context(self, user_input: str, assistant_output: str) -> None:
        """
        保存一轮对话到记忆中

        参数：
            user_input:       用户输入文本
            assistant_output: 助手输出文本

        注意：
            ChatMemory 不直接写数据库（由 ChatService 负责持久化），
            此方法主要用于内存型 Memory（如 ConversationBufferMemory）。
        """
        ...

    @abstractmethod
    def clear(self) -> None:
        """
        清空当前记忆

        用于会话重置或切换会话时清理临时状态。
        """
        ...
