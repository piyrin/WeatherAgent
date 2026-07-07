"""
=============================================================================
全局异常处理器 — 统一捕获所有未处理异常，返回标准 JSON 错误响应
=============================================================================
职责：
  1. 捕获 FastAPI 内置异常（HTTPException、RequestValidationError）
  2. 捕获自定义业务异常（AppException）
  3. 兜底捕获所有未处理异常（Exception），防止返回 HTML 500 页面
  4. 将异常转换为统一格式的 JSON 响应 { code, message, detail }

使用方式：
    from app.middleware.exception_handler import register_exception_handlers
    register_exception_handlers(app)  # 在 main.py 中调用

设计原则：
  - 分层处理：已知异常 → 自定义异常 → 未知异常（兜底）
  - 安全：503 错误只在前端显示简单信息，详细错误写日志
  - 友好：所有异常返回 JSON，不会出现 FastAPI 默认的 HTML 错误页面
=============================================================================
"""

import traceback

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.utils.logger import logger
from app.utils.response import error


# =============================================================================
# 自定义业务异常
# =============================================================================


class AppException(Exception):
    """
    业务层自定义异常

    用法：
        raise AppException(message="会话不存在", code=404)

    参数：
        message: 返回给前端的错误信息
        code:    HTTP 状态码
        detail:  错误详情（可选，默认同 message）
    """

    def __init__(
        self,
        message: str = "服务器内部错误",
        code: int = 500,
        detail: str | None = None,
    ):
        self.message = message
        self.code = code
        self.detail = detail or message
        super().__init__(self.message)


# =============================================================================
# 异常处理函数
# =============================================================================


async def _http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    """
    处理 HTTP 异常（FastAPI/Starlette 内置）

    示例：404 Not Found、405 Method Not Allowed 等
    """
    logger.warning(
        f"HTTP 异常 | path={request.url.path} | "
        f"status={exc.status_code} | detail={exc.detail}"
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error(
            code=exc.status_code,
            message="请求处理失败",
            detail=str(exc.detail),
        ),
    )


async def _validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """
    处理 Pydantic 参数校验异常（422 Unprocessable Entity）

    FastAPI 使用 Pydantic 做请求体校验，校验失败时抛出此异常。
    此处将 Pydantic 的错误格式转为统一格式，方便前端解析。
    """
    # 提取所有校验错误信息
    errors = exc.errors()
    error_details = [
        {
            "field": " → ".join(str(loc) for loc in err["loc"]),
            "message": err["msg"],
        }
        for err in errors
    ]

    logger.warning(
        f"参数校验失败 | path={request.url.path} | "
        f"errors={error_details}"
    )

    return JSONResponse(
        status_code=422,
        content={
            "code": 422,
            "message": "参数校验失败",
            "detail": "; ".join(
                f"{e['field']}: {e['message']}" for e in error_details
            ),
            "errors": error_details,
        },
    )


async def _app_exception_handler(
    request: Request,
    exc: AppException,
) -> JSONResponse:
    """
    处理自定义业务异常

    业务层（Service、Agent）通过 raise AppException 主动抛出，
    此处统一捕获并转为 JSON 响应。
    """
    logger.warning(
        f"业务异常 | path={request.url.path} | "
        f"code={exc.code} | message={exc.message}"
    )
    return JSONResponse(
        status_code=exc.code if 400 <= exc.code < 600 else 500,
        content=error(
            code=exc.code,
            message=exc.message,
            detail=exc.detail,
        ),
    )


async def _generic_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """
    兜底异常处理 — 捕获所有未被上述 handler 处理的异常

    安全规则：
      - 只向前端返回通用错误信息（防止泄露内部细节）
      - 完整的异常堆栈写入日志文件
      - 生产环境中 APP_DEBUG=false 时不返回 traceback
    """
    # 记录完整异常信息到日志
    logger.error(
        f"未处理异常 | path={request.url.path} | "
        f"type={type(exc).__name__} | message={str(exc)}\n"
        f"{traceback.format_exc()}"
    )

    # 返回给前端的通用错误信息
    detail = None
    if hasattr(exc, "__str__"):
        detail = str(exc)

    return JSONResponse(
        status_code=500,
        content=error(
            code=500,
            message="服务器内部错误，请稍后重试",
            detail=detail,
        ),
    )


# =============================================================================
# 注册异常处理器
# =============================================================================


def register_exception_handlers(app: FastAPI) -> None:
    """
    向 FastAPI 应用注册所有异常处理器

    注册顺序不重要：FastAPI 按异常类型的继承关系自动匹配最具体的 handler。

    参数：
        app: FastAPI 应用实例
    """
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_exception_handler)
    app.add_exception_handler(AppException, _app_exception_handler)
    app.add_exception_handler(Exception, _generic_exception_handler)

    logger.info("全局异常处理器已注册")
