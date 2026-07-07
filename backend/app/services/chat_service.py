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

规范依据：agent_interface_spec.md 第8节
=============================================================================
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, Any, Dict, List

from sqlalchemy.orm import Session

from app.agent.executor import AgentResult, get_agent_executor
from app.middleware.exception_handler import AppException
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.tool_call_log import ToolCallLog
from app.schemas.chat import (
    AgentProcess,
    ChatResponse,
    ToolCallRecord,
    Step,
    PlanSummary,
)
from app.services.base_service import BaseService
from app.utils.logger import logger


class ChatService(BaseService):
    _TITLE_MAX_LENGTH = 50

    async def send_message(
        self,
        message: str,
        conversation_id: Optional[str] = None,
    ) -> ChatResponse:
        conversation = self._get_or_create_conversation(conversation_id)

        user_msg = Message.create_user_message(
            conversation_id=conversation.id,
            content=message,
        )
        self.db.add(user_msg)
        self.db.flush()

        chat_history = self._build_chat_history(conversation.id)

        executor = get_agent_executor()
        agent_result: AgentResult = await executor.run(
            user_message=message,
            conversation_id=conversation.id,
            chat_history=chat_history,
            current_time=datetime.now(timezone.utc).isoformat(),
        )

        assistant_msg = Message.create_assistant_message(
            conversation_id=conversation.id,
            content=agent_result.answer,
            metadata_json={
                "plan": agent_result.plan,
                "steps": agent_result.steps,
                "tool_count": len(agent_result.tools),
                "duration_ms": agent_result.total_duration_ms,
            },
        )
        self.db.add(assistant_msg)
        self.db.flush()

        self._save_tool_call_logs(assistant_msg.id, agent_result)

        if conversation.title == "新对话" or conversation.message_count <= 2:
            conversation.title = message[:self._TITLE_MAX_LENGTH]
        conversation.increment_message_count()
        conversation.increment_message_count()

        self.db.commit()

        return self._build_chat_response(conversation, assistant_msg, agent_result)

    def _get_or_create_conversation(self, conversation_id: Optional[str]) -> Conversation:
        if conversation_id:
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

        conv = Conversation(
            id=str(uuid.uuid4()),
            title="新对话",
            status="active",
            message_count=0,
        )
        self.db.add(conv)
        self.db.flush()

        logger.info(f"创建新会话 | id={conv.id}")
        return conv

    def _build_chat_history(self, conversation_id: str) -> list:
        messages = (
            self.db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
            .all()
        )

        from langchain_core.messages import AIMessage as LCAIMessage
        from langchain_core.messages import HumanMessage as LCHumanMessage

        history = []
        for msg in messages:
            if msg.role == "user":
                history.append(LCHumanMessage(content=msg.content))
            elif msg.role == "assistant":
                history.append(LCAIMessage(content=msg.content))

        return history

    def _save_tool_call_logs(
        self,
        message_id: str,
        agent_result: AgentResult,
    ) -> None:
        for tool in agent_result.tools:
            log = ToolCallLog(
                id=str(uuid.uuid4()),
                message_id=message_id,
                tool_name=tool.get("name", ""),
                tool_input_json=tool.get("input", {}),
                tool_output_text=str(tool.get("output", "")),
                status=tool.get("status", "success"),
                duration_ms=tool.get("duration_ms", 0),
            )
            self.db.add(log)

        if agent_result.tools:
            logger.debug(
                f"保存工具调用日志 | count={len(agent_result.tools)}"
            )

    def _build_chat_response(
        self,
        conversation: Conversation,
        assistant_msg: Message,
        agent_result: AgentResult,
    ) -> ChatResponse:
        plan_dict = agent_result.plan or {}
        plan_summary = PlanSummary(
            intent_category=plan_dict.get("intent_category"),
            reasoning=plan_dict.get("reasoning"),
            total_steps=plan_dict.get("total_steps"),
        )

        steps = [
            Step(**step) for step in agent_result.steps
        ]

        tool_calls = [
            ToolCallRecord(
                name=tool.get("name", ""),
                input=tool.get("input", {}),
                output=tool.get("output"),
                status=tool.get("status", "completed"),
                duration_ms=tool.get("duration_ms"),
            )
            for tool in agent_result.tools
        ]

        agent_process = AgentProcess(
            plan=plan_summary,
            steps=steps,
            tool_calls=tool_calls,
        )

        return ChatResponse(
            conversation_id=conversation.id,
            message=agent_result.answer,
            agent_process=agent_process,
            message_id=assistant_msg.id,
            created_at=assistant_msg.created_at.isoformat()
            if assistant_msg.created_at
            else None,
            tools=tool_calls,
            total_duration_ms=agent_result.total_duration_ms,
        )