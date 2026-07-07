"""
=============================================================================
历史记录接口 — GET/DELETE /api/v1/history
=============================================================================
职责：
  1. GET  /api/v1/history     — 获取会话列表
  2. GET  /api/v1/history/{id} — 获取会话详情（含消息列表）
  3. DELETE /api/v1/history/{id} — 删除指定会话
  4. DELETE /api/v1/history     — 清空所有会话
=============================================================================
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import PaginationParams, get_db
from app.services.history_service import HistoryService
from app.utils.logger import logger
from app.utils.response import success

router = APIRouter(tags=["历史记录"])


@router.get(
    "/history",
    summary="获取会话列表",
    description="获取所有活跃会话的列表，按最后更新时间倒序排列。",
)
async def get_conversations(
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
) -> dict:
    """
    获取会话列表

    Query 参数：
        page:      页码（默认 1）
        page_size: 每页条数（默认 20，最大 100）

    响应：
        {
            "code": 200,
            "data": {
                "conversations": [...],
                "total": 42
            }
        }
    """
    logger.debug(f"查询会话列表 | page={pagination.page} | page_size={pagination.page_size}")

    service = HistoryService(db)
    conversations = service.get_conversations(
        page=pagination.page,
        page_size=pagination.page_size,
    )
    total = service.get_total_conversations()

    return success(data={
        "conversations": conversations,
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
    })


@router.get(
    "/history/{conversation_id}",
    summary="获取会话详情",
    description="获取指定会话的完整信息，包含所有消息列表。",
)
async def get_conversation_detail(
    conversation_id: str,
    db: Session = Depends(get_db),
) -> dict:
    """
    获取会话详情（含完整消息列表）

    路径参数：
        conversation_id: 会话 ID

    响应：
        {
            "code": 200,
            "data": {
                "id": "...",
                "title": "明天北京天气...",
                "messages": [
                    {"id": "...", "role": "user", "content": "...", "created_at": "..."},
                    {"id": "...", "role": "assistant", "content": "...", "created_at": "..."}
                ]
            }
        }
    """
    logger.debug(f"查询会话详情 | id={conversation_id}")

    service = HistoryService(db)
    detail = service.get_conversation_detail(conversation_id)

    return success(data=detail)


@router.delete(
    "/history/{conversation_id}",
    summary="删除指定会话",
    description="删除指定会话及其所有关联消息和工具调用日志。",
)
async def delete_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
) -> dict:
    """
    删除指定会话

    路径参数：
        conversation_id: 会话 ID

    注意：
        此操作不可逆，删除后无法恢复。
        关联的消息和工具调用日志会级联删除。
    """
    logger.info(f"删除会话 | id={conversation_id}")

    service = HistoryService(db)
    service.delete_conversation(conversation_id)

    return success(
        data={"deleted_id": conversation_id},
        message="会话已删除",
    )


@router.delete(
    "/history",
    summary="清空所有会话",
    description="删除所有活跃会话及其关联数据。此操作不可逆！",
)
async def delete_all_conversations(
    db: Session = Depends(get_db),
) -> dict:
    """
    清空所有会话

    警告：
        此操作不可逆，将删除所有会话、消息和工具调用日志。
    """
    logger.warning("清空所有会话")

    service = HistoryService(db)
    deleted_count = service.delete_all_conversations()

    return success(
        data={"deleted_count": deleted_count},
        message=f"已删除 {deleted_count} 个会话",
    )
