"""
=============================================================================
聊天服务 — Agent 聊天的核心业务编排
=============================================================================
职责：
  1. 管理会话生命周期（创建/查找/激活）
  2. 持久化用户消息和 Agent 回答
  3. 调用 Agent 执行器处理用户输入
  4. 记录工具调用日志
  5. 组装 ChatResponse 返回给前端
  6. 使用 ChatMemory 管理对话上下文（摘要 + Token 预算）

Agent 核心流程：
  用户输入 → 创建/查找会话 → 保存用户消息
  → ChatMemory 加载上下文（摘要 + 最近消息 + Token 预算截断）
  → Agent 执行（理解→计划→调用工具→生成回答）
  → 保存助手消息 → 保存工具调用日志 → 返回结果
  → ChatMemory 检查并生成摘要（消息超过阈值时）

设计原则：
  - 事务边界：整个 chat 流程在一个 DB 事务中完成
  - Agent 调用与数据库操作分离：Agent 先执行，结果再持久化
  - 工具调用日志批量写入：减少数据库 IO
  - Memory 管理独立：ChatMemory 封装上下文加载和摘要逻辑
=============================================================================
"""

import uuid
from datetime import datetime, timezone
from pprint import pformat
from typing import Optional

from sqlalchemy.orm import Session

from app.agent.executor import AgentResult, get_agent_executor
from app.memory.chat_memory import ChatMemory
from app.middleware.exception_handler import AppException
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.tool_call_log import ToolCallLog
from app.schemas.chat import (
    AgentProcess,
    ChatResponse,
    ToolCallRecord,
)
from app.services.base_service import BaseService
from app.utils.logger import logger


class ChatService(BaseService):
    """
    聊天服务 — 处理用户输入并返回 Agent 回答

    用法：
        db = SessionLocal()
        service = ChatService(db)
        response = await service.send_message(
            message="明天北京天气怎么样？",
            conversation_id="xxx",  # 可选
        )
    """

    # 自动生成会话标题时截取的长度
    _TITLE_MAX_LENGTH = 50

    async def send_message(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        client_ip: str = "",
    ) -> ChatResponse:
        """
        处理用户消息并返回 Agent 回答

        参数：
            message:         用户输入文本
            conversation_id: 会话 ID（可选，不传则新建会话）
            client_ip:       客户端真实 IP（从 HTTP 请求中提取，用于 IP 定位）

        返回值：
            ChatResponse（含 Agent 回答 + 执行过程）

        异常：
            AppException：会话不存在、Agent 执行失败等
        """
        # =====================================================================
        # Step 1: 获取或创建会话
        # =====================================================================
        conversation = self._get_or_create_conversation(conversation_id)

        # =====================================================================
        # Step 2: 保存用户消息
        # =====================================================================
        user_msg = Message.create_user_message(
            conversation_id=conversation.id,
            content=message,
        )
        self.db.add(user_msg)
        self.db.flush()  # 确保 user_msg 获得 ID（后续 ToolCallLog 需要）

        # =====================================================================
        # Step 3: 构建对话记忆上下文
        # =====================================================================
        # ChatMemory 负责：
        #   - 加载对话历史（含摘要 + 最近消息）
        #   - 按 Token 预算智能截断（不再硬编码"最近 6 条"）
        #   - 格式化上下文为预处理的纯文本字符串
        memory = ChatMemory(
            db=self.db,
            conversation_id=conversation.id,
            llm=self._get_llm(),
        )
        memory_context = memory.load_memory_context()

        # =====================================================================
        # Step 4: 调用 Agent 执行
        # =====================================================================
        # 传入预格式化的上下文字符串（而非 LangChain 消息列表）
        # AgentExecutor 直接使用此字符串注入 AgentState.chat_history
        executor = get_agent_executor()
        agent_result: AgentResult = await executor.run(
            user_input=message,
            chat_history=memory_context,
            client_ip=client_ip,
        )

        # =====================================================================
        # Step 5: 保存 Agent 回答
        # =====================================================================
        assistant_msg = Message.create_assistant_message(
            conversation_id=conversation.id,
            content=agent_result.answer,
            metadata_json={
                "plan": agent_result.plan,
                "steps": agent_result.steps,
                "tool_count": len(agent_result.tool_calls),
                "duration_ms": agent_result.total_duration_ms,
            },
        )
        self.db.add(assistant_msg)
        self.db.flush()  # 确保 assistant_msg 获得 ID

        # =====================================================================
        # Step 6: 保存工具调用日志
        # =====================================================================
        self._save_tool_call_logs(assistant_msg.id, agent_result)

        # =====================================================================
        # Step 7: 更新会话信息
        # =====================================================================
        # 自动生成会话标题（首次对话时使用用户消息的前 N 个字符）
        if conversation.title == "新对话" or conversation.message_count <= 2:
            conversation.title = message[:_get_title_max_length()]
        # user_msg + assistant_msg 共 2 条消息
        conversation.increment_message_count()
        conversation.increment_message_count()

        # =====================================================================
        # Step 8: 提交事务
        # =====================================================================
        self.db.commit()

        # =====================================================================
        # Step 8.5: 检查并生成对话摘要（非阻塞，消息超过阈值时触发）
        # =====================================================================
        # maybe_summarize 在提交后调用，此时新一轮消息已持久化
        # 如果消息总数超过阈值，调用 LLM 生成摘要并存储到 conversation_summaries 表
        try:
            summary = memory.maybe_summarize()
            if summary:
                self.db.commit()  # 提交摘要写入
        except Exception as summary_err:
            # 摘要生成失败不影响主流程
            logger.warning(f"摘要生成失败（不影响主流程）| error={summary_err}")

        # =====================================================================
        # Step 9: 组装响应
        # =====================================================================
        return self._build_chat_response(conversation, assistant_msg, agent_result)

    def _get_or_create_conversation(self, conversation_id: Optional[str]) -> Conversation:
        """
        获取已有会话或创建新会话

        参数：
            conversation_id: 会话 ID（None 则创建新的）

        返回值：
            Conversation 实例

        异常：
            AppException：指定 ID 的会话不存在
        """
        if conversation_id:
            # 查找已有会话
            conv = self.db.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()

            if not conv:
                raise AppException(
                    message="会话不存在",
                    code=404,
                    detail=f"conversation_id={conversation_id} 未找到",
                )

            logger.debug(f"使用已有会话 | id={conversation_id}")
            return conv

        # 创建新会话
        conv = Conversation(
            id=str(uuid.uuid4()),
            title="新对话",
            status="active",
            message_count=0,
        )
        self.db.add(conv)
        self.db.flush()  # 立即刷新以获取 ID

        logger.info(f"创建新会话 | id={conv.id}")
        return conv

    # ---- LLM 懒加载（类级别单例，所有 ChatService 实例共享） ----

    _llm = None

    @classmethod
    def _get_llm(cls):
        """
        获取 LLM 实例（懒加载，只创建一次）

        ChatMemory 需要 LLM 来生成对话摘要。
        使用类级别单例避免每次请求都创建新的 LLM 连接。
        """
        if cls._llm is None:
            from app.agent.agent import create_llm
            cls._llm = create_llm()
            logger.info("ChatService: LLM 懒加载完成（用于摘要生成）")
        return cls._llm

    def _save_tool_call_logs(
        self,
        message_id: str,
        agent_result: AgentResult,
    ) -> None:
        """
        将 Agent 的工具调用记录持久化到数据库

        参数：
            message_id:   助手消息 ID
            agent_result: Agent 执行结果
        """
        for step in agent_result.tool_calls:
            output_json = step.tool_output if isinstance(step.tool_output, dict) else None
            log = ToolCallLog(
                id=str(uuid.uuid4()),
                message_id=message_id,
                tool_name=step.tool_name,
                tool_input_json=step.tool_input,
                tool_output_json=output_json,
                tool_output_text=pformat(step.tool_output, width=120)
                if step.tool_output is not None
                else None,
                status=step.status,
                duration_ms=step.duration_ms,
            )
            self.db.add(log)

        if agent_result.tool_calls:
            logger.debug(
                f"保存工具调用日志 | count={len(agent_result.tool_calls)}"
            )

    def _build_chat_response(
        self,
        conversation: Conversation,
        assistant_msg: Message,
        agent_result: AgentResult,
    ) -> ChatResponse:
        """
        组装 ChatResponse 对象

        参数：
            conversation:  会话实例
            assistant_msg: 助手消息实例
            agent_result:  Agent 执行结果

        返回值：
            ChatResponse
        """
        # 工具调用记录
        tool_call_records = [
            ToolCallRecord(
                tool_name=step.tool_name,
                tool_input=step.tool_input,
                tool_output=step.tool_output,
                status=step.status,
                duration_ms=step.duration_ms,
            )
            for step in agent_result.tool_calls
        ]

        # Agent 执行过程
        agent_process = AgentProcess(
            plan=agent_result.plan,
            steps=agent_result.steps,
            tool_calls=tool_call_records,
        )

        return ChatResponse(
            conversation_id=conversation.id,
            message=agent_result.answer,
            agent_process=agent_process,
            message_id=assistant_msg.id,
            created_at=assistant_msg.created_at.isoformat()
            if assistant_msg.created_at
            else None,
        )


def _get_title_max_length() -> int:
    """获取会话标题截取长度"""
    return ChatService._TITLE_MAX_LENGTH
