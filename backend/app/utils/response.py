"""
=============================================================================
统一响应构建器 — 快捷方法用于生成标准 JSON 响应
=============================================================================
职责：
  1. success()：构建成功响应 { code: 200, message: "ok", data: ... }
  2. error()：构建错误响应 { code: xxx, message: "...", detail: "..." }

使用方式：
    from app.utils.response import success, error

    # 成功
    return success(data=chat_response)

    # 失败
    return error(code=422, message="参数校验失败", detail="city 不能为空")

设计原则：
  - 所有 API 路由均使用这两个函数返回响应，保证格式统一
  - 不需要在每个路由中手动构造 dict
  - 泛型方法自动推断 data 类型
=============================================================================
"""

from typing import Any, Optional

from app.schemas.common import BaseResponse, ErrorResponse


def success(
    data: Any = None,
    message: str = "ok",
    code: int = 200,
) -> dict:
    """
    构建统一成功响应

    参数：
        data:    返回数据（可以是 Pydantic Model、dict、list、None）
        message: 提示信息
        code:    HTTP 状态码（默认 200）

    返回值：
        标准格式的 dict，可直接作为 FastAPI 路由的返回值

    示例：
        return success(data={"id": "xxx", "title": "天气咨询"})
        # => {"code": 200, "message": "ok", "data": {"id": "xxx", ...}}
    """
    response = BaseResponse(code=code, message=message, data=data)
    # 使用 model_dump(exclude_none=True) 排除 None 字段（如 data=None 时不输出）
    return response.model_dump(exclude_none=True)


def error(
    code: int = 500,
    message: str = "服务器内部错误",
    detail: Optional[str] = None,
) -> dict:
    """
    构建统一错误响应

    参数：
        code:    HTTP 状态码（4xx 客户端错误 / 5xx 服务端错误）
        message: 错误摘要
        detail:  错误详情（可选）

    返回值：
        标准格式的 dict

    示例：
        return error(code=422, message="参数校验失败", detail="city 不能为空")
        # => {"code": 422, "message": "参数校验失败", "detail": "city 不能为空"}
    """
    response = ErrorResponse(code=code, message=message, detail=detail)
    return response.model_dump(exclude_none=True)
