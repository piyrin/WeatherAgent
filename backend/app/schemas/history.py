"""
=============================================================================
历史记录请求/响应 Schema — 历史记录接口的输入输出契约
=============================================================================
职责：
  1. ConversationListItem：会话列表项（用于侧边栏展示）
  2. ConversationListResponse：会话列表响应
  3. ConversationDetailResponse：单个会话的完整消息列表
  4. MessageItem：消息项（包含角色、内容、时间戳）
=============================================================================
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# =============================================================================
# 消息项
# =============================================================================


class MessageItem(BaseModel):
    """
    消息列表中的单条消息

    字段说明：
      - id:         消息 ID
      - role:       角色（user / assistant / system / tool）
      - content:    消息内容
      - created_at: 消息时间（ISO 8601 格式字符串）
    """

    id: str = Field(..., description="消息 ID")
    role: str = Field(..., description="角色：user / assistant / system / tool")
    content: str = Field(..., description="消息内容")
    created_at: str = Field(..., description="消息时间（ISO 8601）")


# =============================================================================
# 会话列表项
# =============================================================================


class ConversationListItem(BaseModel):
    """
    会话列表中的单个会话摘要

    用于前端侧边栏展示历史对话列表。

    字段说明：
      - id:            会话 ID
      - title:         会话标题
      - message_count: 消息总数
      - last_message:  最后一条消息预览（截取前 50 字符）
      - created_at:    创建时间
      - updated_at:    最后活跃时间
    """

    id: str = Field(..., description="会话 ID")
    title: str = Field(..., description="会话标题")
    message_count: int = Field(default=0, description="消息总数")
    last_message: Optional[str] = Field(default=None, description="最后一条消息预览")
    created_at: str = Field(..., description="创建时间（ISO 8601）")
    updated_at: str = Field(..., description="最后活跃时间（ISO 8601）")


class ConversationListResponse(BaseModel):
    """
    会话列表响应

    字段说明：
      - conversations: 会话摘要列表（按更新时间倒序排列）
      - total: 总会话数
    """

    conversations: list[ConversationListItem] = Field(
        default_factory=list,
        description="会话列表",
    )
    total: int = Field(default=0, description="总会话数")


# =============================================================================
# 会话详情（含完整消息列表）
# =============================================================================


class ConversationDetailResponse(BaseModel):
    """
    单个会话的完整详情

    字段说明：
      - id:       会话 ID
      - title:    会话标题
      - messages: 完整消息列表（按时间正序排列）
      - created_at: 创建时间
      - updated_at: 最后更新时间
    """

    id: str = Field(..., description="会话 ID")
    title: str = Field(..., description="会话标题")
    messages: list[MessageItem] = Field(
        default_factory=list,
        description="消息列表",
    )
    created_at: str = Field(..., description="创建时间（ISO 8601）")
    updated_at: str = Field(..., description="最后更新时间（ISO 8601）")


# =============================================================================
# 删除响应
# =============================================================================


class DeleteHistoryResponse(BaseModel):
    """
    删除历史记录响应

    字段说明：
      - deleted_count: 已删除的会话数量
    """

    deleted_count: int = Field(..., description="已删除的会话数量")
