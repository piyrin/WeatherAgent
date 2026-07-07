"""
=============================================================================
历史记录服务 — 会话和消息的查询、删除
=============================================================================
职责：
  1. 获取会话列表（按时间倒序）
  2. 获取单个会话的完整消息历史
  3. 删除指定会话（级联删除关联消息和工具调用日志）
  4. 清空所有会话

设计原则：
  - 查询优化：会话列表只加载摘要信息（不含完整消息内容）
  - 安全删除：使用 CASCADE 确保删除会话时关联数据一并清除
  - 分页支持：预留分页参数，当前默认返回最近 50 条
=============================================================================
"""

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.middleware.exception_handler import AppException
from app.models.conversation import Conversation
from app.models.message import Message
from app.services.base_service import BaseService
from app.utils.logger import logger


class HistoryService(BaseService):
    """
    历史记录服务 — 管理会话和消息历史

    用法：
        db = SessionLocal()
        service = HistoryService(db)
        conversations = service.get_conversations()
    """

    # 默认每页条数
    _DEFAULT_PAGE_SIZE = 50

    # 消息预览截取长度
    _PREVIEW_MAX_LENGTH = 50

    def get_conversations(
        self,
        page: int = 1,
        page_size: int | None = None,
    ) -> list[dict]:
        """
        获取会话列表（按最后更新时间倒序）

        参数：
            page:      页码（从 1 开始）
            page_size: 每页条数（默认 50）

        返回值：
            会话摘要列表，每项包含 id、title、message_count、last_message、时间戳
        """
        page_size = page_size or self._DEFAULT_PAGE_SIZE
        offset = (page - 1) * page_size

        conversations = (
            self.db.query(Conversation)
            .filter(Conversation.status == "active")
            .order_by(Conversation.updated_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )

        result = []
        for conv in conversations:
            # 获取第一条用户消息（用于侧边栏展示）
            first_user_msg = (
                self.db.query(Message)
                .filter(Message.conversation_id == conv.id, Message.role == "user")
                .order_by(Message.created_at.asc())
                .first()
            )

            first_user_preview = None
            if first_user_msg:
                content = first_user_msg.content or ""
                first_user_preview = (
                    content[:self._PREVIEW_MAX_LENGTH] + "..."
                    if len(content) > self._PREVIEW_MAX_LENGTH
                    else content
                )

            # 获取最后一条消息预览
            last_msg = (
                self.db.query(Message)
                .filter(Message.conversation_id == conv.id)
                .order_by(Message.created_at.desc())
                .first()
            )

            last_preview = None
            if last_msg:
                content = last_msg.content or ""
                last_preview = (
                    content[:self._PREVIEW_MAX_LENGTH] + "..."
                    if len(content) > self._PREVIEW_MAX_LENGTH
                    else content
                )

            result.append({
                "id": conv.id,
                "title": conv.title,
                "message_count": conv.message_count,
                "first_user_message": first_user_preview,
                "last_message": last_preview,
                "created_at": conv.created_at.isoformat() if conv.created_at else "",
                "updated_at": conv.updated_at.isoformat() if conv.updated_at else "",
            })

        logger.debug(f"查询会话列表 | count={len(result)}")
        return result

    def get_total_conversations(self) -> int:
        """
        获取活跃会话总数

        返回值：
            会话数量
        """
        return (
            self.db.query(Conversation)
            .filter(Conversation.status == "active")
            .count()
        )

    def get_conversation_detail(self, conversation_id: str) -> dict | None:
        """
        获取单个会话的完整详情（含所有消息）

        参数：
            conversation_id: 会话 ID

        返回值：
            会话详情 dict，不存在返回 None

        异常：
            AppException：会话不存在
        """
        conv = (
            self.db.query(Conversation)
            .filter(Conversation.id == conversation_id)
            .first()
        )

        if not conv:
            raise AppException(
                message="会话不存在",
                code=404,
                detail=f"conversation_id={conversation_id}",
            )

        # 加载所有消息（按时间正序）
        messages = (
            self.db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
            .all()
        )

        message_items = [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat() if msg.created_at else "",
            }
            for msg in messages
        ]

        return {
            "id": conv.id,
            "title": conv.title,
            "messages": message_items,
            "created_at": conv.created_at.isoformat() if conv.created_at else "",
            "updated_at": conv.updated_at.isoformat() if conv.updated_at else "",
        }

    def delete_conversation(self, conversation_id: str) -> bool:
        """
        删除指定会话（级联删除关联消息和工具调用日志）

        参数：
            conversation_id: 会话 ID

        返回值：
            True 表示删除成功

        异常：
            AppException：会话不存在
        """
        conv = (
            self.db.query(Conversation)
            .filter(Conversation.id == conversation_id)
            .first()
        )

        if not conv:
            raise AppException(
                message="会话不存在",
                code=404,
                detail=f"conversation_id={conversation_id}",
            )

        # SQLAlchemy relationship 配置了 cascade="all, delete-orphan"
        # 删除会话时会自动删除关联的 messages 和 tool_call_logs
        self.db.delete(conv)
        self.db.commit()

        logger.info(f"删除会话 | id={conversation_id} | title={conv.title}")
        return True

    def delete_all_conversations(self) -> int:
        """
        删除所有会话

        返回值：
            已删除的会话数量
        """
        count = (
            self.db.query(Conversation)
            .filter(Conversation.status == "active")
            .count()
        )

        # 直接按状态批量删除
        self.db.query(Conversation).filter(
            Conversation.status == "active"
        ).delete()
        self.db.commit()

        logger.info(f"批量删除会话 | count={count}")
        return count
