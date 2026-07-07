"""
=============================================================================
Pydantic Schema 层 — API 请求/响应的类型契约
=============================================================================
导入顺序：先导入 common（基础模型），再导入具体业务 Schema。
=============================================================================
"""

from app.schemas.common import BaseResponse, ErrorDetail, PaginationMeta
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ToolCallRecord,
    AgentProcess,
)
from app.schemas.history import (
    ConversationListItem,
    ConversationListResponse,
    ConversationDetailResponse,
    MessageItem,
    DeleteHistoryResponse,
)

__all__ = [
    # common
    "BaseResponse",
    "ErrorDetail",
    "PaginationMeta",
    # chat
    "ChatRequest",
    "ChatResponse",
    "ToolCallRecord",
    "AgentProcess",
    # history
    "ConversationListItem",
    "ConversationListResponse",
    "ConversationDetailResponse",
    "MessageItem",
    "DeleteHistoryResponse",
]
