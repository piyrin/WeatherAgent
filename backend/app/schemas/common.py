"""
=============================================================================
统一响应格式 — 所有 API 返回的 JSON 结构
=============================================================================
职责：
  1. BaseResponse[T]：泛型成功响应，data 字段类型由业务决定
  2. ErrorDetail：错误详情结构（用于 422 等参数校验错误）
  3. PaginationMeta：分页元数据

设计原则：
  - 统一输出格式：前端只需解析一种 JSON 结构
  - 泛型支持：BaseResponse[ChatData] 在 Swagger 中自动展示正确类型
  - 不依赖 FastAPI 的 response_model 自动包装：所有响应由 utils/response.py 显式构建

统一格式示例：
  // 成功
  {
    "code": 200,
    "message": "ok",
    "data": { ... }
  }

  // 失败
  {
    "code": 500,
    "message": "Agent 执行失败",
    "detail": "LLM API 超时，请稍后重试"
  }
=============================================================================
"""

from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, Field

# 泛型变量 T：用于 BaseResponse 的 data 字段类型
T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    """
    统一成功响应格式

    泛型参数 T 决定 data 字段的具体类型：
      BaseResponse[ChatResponse] → data 是 ChatResponse 类型
      BaseResponse[list[ConversationListItem]] → data 是列表类型

    字段说明：
      - code:    HTTP 状态码（200 = 成功）
      - message: 提示信息（"ok" 或自定义描述）
      - data:    实际返回数据（泛型，可选，如 DELETE 操作无返回数据）
    """

    code: int = Field(
        default=200,
        description="HTTP 状态码",
        examples=[200],
    )
    message: str = Field(
        default="ok",
        description="提示信息",
        examples=["ok", "操作成功"],
    )
    data: Optional[T] = Field(
        default=None,
        description="响应数据",
    )


class ErrorResponse(BaseModel):
    """
    统一错误响应格式

    字段说明：
      - code:    HTTP 状态码（4xx / 5xx）
      - message: 错误摘要
      - detail:  错误详情（可选，给开发者和前端的补充信息）
    """

    code: int = Field(
        ...,
        description="HTTP 状态码",
        examples=[400, 422, 500],
    )
    message: str = Field(
        ...,
        description="错误摘要",
        examples=["参数校验失败", "Agent 执行失败"],
    )
    detail: Optional[str] = Field(
        default=None,
        description="错误详情",
        examples=["city 字段不能为空"],
    )


class ErrorDetail(BaseModel):
    """
    字段级错误详情（用于 422 参数校验失败时逐字段说明）

    示例：
        ErrorDetail(field="city", message="城市名称不能为空")
    """

    field: str = Field(
        ...,
        description="出错的字段名",
    )
    message: str = Field(
        ...,
        description="错误信息",
    )


class PaginationMeta(BaseModel):
    """
    分页元数据（用于历史记录等列表接口）

    字段说明：
      - page:        当前页码（从 1 开始）
      - page_size:   每页条数
      - total:       总记录数
      - total_pages: 总页数
    """

    page: int = Field(..., ge=1, description="当前页码")
    page_size: int = Field(..., ge=1, description="每页条数")
    total: int = Field(..., ge=0, description="总记录数")
    total_pages: int = Field(..., ge=0, description="总页数")
