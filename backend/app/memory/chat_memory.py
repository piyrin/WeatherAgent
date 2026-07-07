"""
=============================================================================
ChatMemory — 基于摘要的对话记忆实现
=============================================================================
职责：
  1. 从数据库加载对话历史
  2. 按 Token 预算智能截断（保留最近 N 条消息 + 历史摘要）
  3. 自动触发 LLM 生成对话摘要（消息量超过阈值时）
  4. 格式化上下文为 Agent 可直接使用的文本

核心策略 — 滑动窗口 + 摘要：
  当对话消息超过 WINDOW_SIZE 时，将早期消息压缩为摘要文本。
  上下文 = 最新摘要 + 最近 WINDOW_SIZE 条消息。

  示例（WINDOW_SIZE=6，共20条消息）：
    上下文 =
      "[历史对话摘要] 用户前面问了北京、上海、广州三地天气..."
      + 最近6条消息的格式化文本

Token 估算策略：
  中文 ≈ 2 字符/Token，英文 ≈ 4 字符/Token（粗略估算）
  后续可替换为 tiktoken 精确计算。

设计原则：
  - 数据库读取由 ChatMemory 内部完成（封装 DB 访问）
  - 摘要生成通过注入的 summary_fn 回调（解耦 LLM 依赖）
  - 不修改 AgentState 结构（chat_history 字段保持 str 类型）
=============================================================================
"""

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.conversation_summary import ConversationSummary
from app.models.message import Message
from app.memory.base import BaseMemory
from app.utils.logger import logger


class ChatMemory(BaseMemory):
    """
    基于摘要的对话记忆

    用法：
        db = SessionLocal()
        memory = ChatMemory(
            db=db,
            conversation_id="xxx",
            llm=my_llm,                 # 可选，用于生成摘要
            window_size=8,              # 滑动窗口中保留的最近消息条数
            max_context_tokens=4000,    # Agent 上下文总 Token 预算
        )
        context = memory.load_memory_context()
        # → "[历史对话摘要] ...\n\n[最近对话]\n用户: ..."

    参数说明：
      - db:                  SQLAlchemy 数据库会话
      - conversation_id:     当前会话 ID
      - llm:                 LangChain LLM 实例（用于生成摘要，可选）
      - window_size:         滑动窗口大小（保留最近 N 条消息不摘要）
      - max_context_tokens:  上下文总 Token 预算上限
    """

    # ---- 默认配置 ----

    DEFAULT_WINDOW_SIZE = 8
    """滑动窗口默认大小：保留最近 8 条消息不摘要"""

    DEFAULT_MAX_CONTEXT_TOKENS = 4000
    """默认上下文 Token 预算上限（为 Agent 回答留出 2000+ tokens）"""

    DEFAULT_SUMMARY_THRESHOLD = 16
    """消息总数超过此阈值时触发摘要生成（为 window_size 的 2 倍）"""

    CHARS_PER_TOKEN_CN = 2.0
    """中文每 Token 约 2 字符（ERNIE/GLM 等中文模型）"""

    CHARS_PER_TOKEN_EN = 4.0
    """英文每 Token 约 4 字符（GPT 系列）"""

    # ---- 构造 ----

    def __init__(
        self,
        db: Session,
        conversation_id: str,
        llm=None,
        window_size: int | None = None,
        max_context_tokens: int | None = None,
    ):
        self.db = db
        self.conversation_id = conversation_id
        self.llm = llm
        self.window_size = window_size or self.DEFAULT_WINDOW_SIZE
        self.max_context_tokens = max_context_tokens or self.DEFAULT_MAX_CONTEXT_TOKENS

    # =====================================================================
    # 核心接口实现
    # =====================================================================

    def load_memory_context(self) -> str:
        """
        加载对话记忆上下文

        流程：
          1. 加载所有消息（按时间正序）
          2. 加载最新摘要（如果存在）
          3. 计算 Token 预算 → 动态调整 window_size
          4. 格式化：摘要 + 最近消息

        返回值：
            格式化后的上下文字符串，可直接注入 AgentState.chat_history
        """
        # -----------------------------------------------------------------
        # Step 1: 加载所有消息
        # -----------------------------------------------------------------
        all_messages = self._load_all_messages()

        if not all_messages:
            logger.debug(f"ChatMemory: 会话 {self.conversation_id} 无历史消息")
            return "（无历史对话）"

        # -----------------------------------------------------------------
        # Step 2: 加载最新摘要
        # -----------------------------------------------------------------
        latest_summary = self._load_latest_summary()

        # -----------------------------------------------------------------
        # Step 3: 计算 Token 预算 → 实际保留的消息数
        # -----------------------------------------------------------------
        effective_window = self._calculate_effective_window(
            all_messages=all_messages,
            summary_text=latest_summary,
        )

        # -----------------------------------------------------------------
        # Step 4: 切分消息 → 需要摘要的部分 + 窗口内部分
        # -----------------------------------------------------------------
        total_count = len(all_messages)
        recent_messages = all_messages[-effective_window:]
        summarized_count = total_count - effective_window

        # -----------------------------------------------------------------
        # Step 5: 格式化上下文
        # -----------------------------------------------------------------
        parts = []

        # 摘要部分
        if summarized_count > 0 and latest_summary:
            parts.append(
                f"[历史对话摘要（前 {summarized_count} 条消息）]\n"
                f"{latest_summary}"
            )
        elif summarized_count > 0:
            # 没有摘要但有超出的消息 → 简单提示
            parts.append(
                f"[历史对话]\n"
                f"（前面 {summarized_count} 条消息因上下文限制被省略）"
            )

        # 最近消息部分
        if recent_messages:
            recent_text = self._format_messages(recent_messages)
            if summarized_count > 0:
                parts.append(f"[最近对话（{effective_window} 条消息）]\n{recent_text}")
            else:
                parts.append(f"[对话记录]\n{recent_text}")

        context = "\n\n".join(parts) if parts else "（无历史对话）"

        logger.debug(
            f"ChatMemory: 会话 {self.conversation_id} | "
            f"总消息={total_count} | 窗口={effective_window} | "
            f"摘要={'有' if latest_summary else '无'} | "
            f"上下文≈{self._estimate_tokens(context)} tokens"
        )

        return context

    def save_context(self, user_input: str, assistant_output: str) -> None:
        """
        保存一轮对话

        注意：ChatMemory 不直接写数据库。
              消息持久化由 ChatService 在调用 Agent 前后完成。
              此方法保留用于未来扩展（如内存缓存）。
        """
        pass

    def clear(self) -> None:
        """
        清空当前记忆（无操作 — 数据存储在 DB 中，不维护内存状态）
        """
        pass

    # =====================================================================
    # 摘要管理
    # =====================================================================

    def maybe_summarize(self) -> str | None:
        """
        检查并生成对话摘要

        触发条件：消息总数 > DEFAULT_SUMMARY_THRESHOLD

        流程：
          1. 加载所有消息 → 判断是否需要摘要
          2. 将超出 window_size 的消息传给 LLM 生成摘要
          3. 持久化摘要到 conversation_summaries 表

        返回值：
            生成的摘要文本（无需摘要时返回 None）

        注意：
            如果未注入 llm，跳过摘要生成（回退到简单截断）。
        """
        all_messages = self._load_all_messages()
        total_count = len(all_messages)

        if total_count <= self.DEFAULT_SUMMARY_THRESHOLD:
            return None

        if self.llm is None:
            logger.warning(
                f"ChatMemory: 会话 {self.conversation_id} 消息数={total_count} "
                f"超过阈值={self.DEFAULT_SUMMARY_THRESHOLD}，但未注入 LLM，跳过摘要生成"
            )
            return None

        # 计算摘要覆盖的消息范围
        summary_count = total_count - self.window_size
        messages_to_summarize = all_messages[:summary_count]

        start_msg_id = messages_to_summarize[0].id
        end_msg_id = messages_to_summarize[-1].id

        logger.info(
            f"ChatMemory: 开始生成摘要 | 会话={self.conversation_id} | "
            f"摘要范围=消息 1-{summary_count}（共{summary_count}条）"
        )

        # 调用 LLM 生成摘要
        summary_text = self._generate_summary(messages_to_summarize)

        # 持久化
        self._save_summary(
            summary_text=summary_text,
            summary_type="rolling",
            start_message_id=start_msg_id,
            end_message_id=end_msg_id,
            message_count=summary_count,
        )

        logger.info(
            f"ChatMemory: 摘要已保存 | 会话={self.conversation_id} | "
            f"覆盖{summary_count}条消息 | 摘要长度={len(summary_text)}字符"
        )

        return summary_text

    # =====================================================================
    # 内部方法 — 数据加载
    # =====================================================================

    def _load_all_messages(self) -> list[Message]:
        """
        加载会话的所有消息（按时间正序）

        返回值：
            Message ORM 实例列表（user + assistant 角色）
        """
        return (
            self.db.query(Message)
            .filter(
                Message.conversation_id == self.conversation_id,
                Message.role.in_(["user", "assistant"]),
            )
            .order_by(Message.created_at)
            .all()
        )

    def _load_latest_summary(self) -> str | None:
        """
        加载最新的一条对话摘要

        返回值：
            摘要文本（无摘要时返回 None）
        """
        summary = (
            self.db.query(ConversationSummary)
            .filter(ConversationSummary.conversation_id == self.conversation_id)
            .order_by(ConversationSummary.created_at.desc())
            .first()
        )

        if summary:
            logger.debug(
                f"ChatMemory: 加载摘要 | 类型={summary.summary_type} | "
                f"覆盖{summary.message_count}条消息 | "
                f"token={summary.token_count}"
            )
            return summary.summary_text

        return None

    # =====================================================================
    # 内部方法 — Token 估算与窗口计算
    # =====================================================================

    def _estimate_tokens(self, text: str) -> int:
        """
        估算文本的 Token 数量

        使用字符比例法（简单但快速）：
          中文 ≈ 2 字符/Token，英文/数字 ≈ 4 字符/Token

        参数：
            text: 待估算文本

        返回值：
            估算的 Token 数量
        """
        if not text:
            return 0

        cn_chars = 0
        en_chars = 0

        for ch in text:
            if '\u4e00' <= ch <= '\u9fff' or '\u3000' <= ch <= '\u303f':
                cn_chars += 1
            elif ch.isascii() and not ch.isspace():
                en_chars += 1

        # 其他字符按英文比例估算
        other_chars = len(text) - cn_chars - en_chars
        en_chars += other_chars

        return int(cn_chars / self.CHARS_PER_TOKEN_CN) + int(en_chars / self.CHARS_PER_TOKEN_EN)

    def _calculate_effective_window(
        self,
        all_messages: list[Message],
        summary_text: str | None,
    ) -> int:
        """
        根据 Token 预算计算实际可保留的最近消息条数

        算法：
          1. 先扣除摘要的 token 消耗
          2. 剩余 token 预算分配给最近消息
          3. 从最新消息向旧消息方向累加 token，直到超出预算

        参数：
            all_messages: 全部消息列表
            summary_text: 最新摘要文本（可为 None）

        返回值：
            实际可保留的消息条数（不超过 window_size）
        """
        # 扣除摘要占用的 token
        available_budget = self.max_context_tokens
        if summary_text:
            summary_tokens = self._estimate_tokens(summary_text)
            available_budget -= summary_tokens

        # 从最新消息开始向旧方向累加，确保总 token 不超出预算
        token_count = 0
        count = 0

        for msg in reversed(all_messages):
            msg_tokens = self._estimate_tokens(msg.content or "")
            if token_count + msg_tokens > available_budget:
                break
            token_count += msg_tokens
            count += 1
            if count >= self.window_size:
                break

        # 至少保留 2 条消息（1 轮完整对话）
        return max(count, 2) if all_messages else 0

    # =====================================================================
    # 内部方法 — 格式化
    # =====================================================================

    def _format_messages(self, messages: list[Message]) -> str:
        """
        将消息列表格式化为纯文本

        格式：
            用户: <内容>
            助手: <内容>

        参数：
            messages: Message ORM 实例列表

        返回值：
            格式化后的文本
        """
        parts = []
        for msg in messages:
            content = (msg.content or "").strip()
            if not content:
                continue
            if msg.role == "user":
                parts.append(f"用户: {content}")
            elif msg.role == "assistant":
                parts.append(f"助手: {content}")

        return "\n".join(parts)

    # =====================================================================
    # 内部方法 — 摘要生成
    # =====================================================================

    def _generate_summary(self, messages: list[Message]) -> str:
        """
        调用 LLM 为消息列表生成摘要

        参数：
            messages: 需要摘要的消息列表

        返回值：
            生成的摘要文本
        """
        if not messages:
            return ""

        # 构建对话文本
        dialogue_text = self._format_messages(messages)

        # 摘要 Prompt
        prompt = (
            "请将以下对话历史压缩为一段简洁的摘要（不超过200字），"
            "保留关键信息：用户问了什么、得到了什么答案、关注的城市/日期/天气/出行建议等。\n\n"
            f"{dialogue_text}\n\n"
            "摘要："
        )

        try:
            from langchain_core.messages import HumanMessage
            response = self.llm.invoke([HumanMessage(content=prompt)])
            summary = response.content.strip() if hasattr(response, 'content') else str(response).strip()
            return summary[:500]  # 安全截断
        except Exception as exc:
            logger.error(f"ChatMemory: 摘要生成失败 | error={exc}")
            # 降级：返回首尾各一条消息的片段
            first = messages[0].content[:50] if messages else ""
            last = messages[-1].content[:50] if messages else ""
            return f"用户询问了关于{first}...等问题。最后讨论了{last}..."

    def _save_summary(
        self,
        summary_text: str,
        summary_type: str,
        start_message_id: str,
        end_message_id: str,
        message_count: int,
    ) -> None:
        """
        持久化对话摘要

        参数：
            summary_text:     摘要文本
            summary_type:     摘要类型（rolling / incremental / final）
            start_message_id: 起始消息 ID
            end_message_id:   结束消息 ID
            message_count:    覆盖消息数
        """
        summary = ConversationSummary(
            id=str(uuid.uuid4()),
            conversation_id=self.conversation_id,
            summary_text=summary_text,
            summary_type=summary_type,
            start_message_id=start_message_id,
            end_message_id=end_message_id,
            message_count=message_count,
            token_count=self._estimate_tokens(summary_text),
        )
        self.db.add(summary)
        self.db.flush()

        logger.debug(
            f"ChatMemory: 摘要已持久化 | 类型={summary_type} | "
            f"覆盖={message_count}条 | token={summary.token_count}"
        )
