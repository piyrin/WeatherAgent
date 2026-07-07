"""
=============================================================================
请求日志中间件 — 记录每个 HTTP 请求的方法、路径、耗时和状态码
=============================================================================
职责：
  1. 记录每个请求的基本信息（方法、路径、客户端 IP）
  2. 记录请求处理耗时（毫秒）
  3. 记录响应状态码

使用方式：
    from app.middleware.request_log import RequestLogMiddleware
    app.add_middleware(RequestLogMiddleware)  # 在 main.py 中

设计原则：
  - 纯 ASGI 中间件：在请求进入和响应返回两个时间点分别记录
  - 计时功能：用 time 模块精确到毫秒
  - 安全：不记录请求体内容（避免日志泄露用户数据和 API Key）
=============================================================================
"""

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.utils.logger import logger


class RequestLogMiddleware(BaseHTTPMiddleware):
    """
    HTTP 请求日志中间件

    每个请求记录一条日志，包含：
      - request_id:  请求唯一标识（UUID，用于全链路追踪）
      - method:      HTTP 方法（GET/POST/DELETE...）
      - path:        请求路径（如 /api/v1/chat）
      - client_ip:   客户端 IP 地址
      - status_code: HTTP 响应状态码
      - duration_ms: 请求处理耗时（毫秒）

    注意：
      - 不记录请求体内容（安全考虑，且大文件/流式请求会导致内存问题）
      - request_id 通过响应头 X-Request-ID 返回给前端（CORS 已配置暴露该头）
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # ---- 请求进入 ----
        # 生成请求唯一 ID
        request_id = str(uuid.uuid4())[:8]  # 截取前 8 位，方便日志查看
        request.state.request_id = request_id

        # 记录请求开始时间
        start_time = time.perf_counter()

        # 获取客户端 IP（优先从代理头中获取）
        client_ip = (
            request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            or request.headers.get("X-Real-IP", "")
            or (request.client.host if request.client else "unknown")
        )

        logger.debug(
            f"[{request_id}] --> {request.method} {request.url.path} "
            f"from {client_ip}"
        )

        # ---- 执行请求 ----
        try:
            response = await call_next(request)
        except Exception as exc:
            # 如果后续处理器抛出异常，记录并重新抛出
            duration = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"[{request_id}] <-- {request.method} {request.url.path} "
                f"ERROR | {duration:.1f}ms | {type(exc).__name__}"
            )
            raise

        # ---- 响应返回 ----
        duration = (time.perf_counter() - start_time) * 1000  # 转换为毫秒
        status_code = response.status_code

        # 根据状态码选择日志级别
        log_func = logger.info
        if status_code >= 500:
            log_func = logger.error
        elif status_code >= 400:
            log_func = logger.warning

        log_func(
            f"[{request_id}] <-- {request.method} {request.url.path} "
            f"{status_code} | {duration:.1f}ms"
        )

        # 将 request_id 添加到响应头，方便前端定位问题
        response.headers["X-Request-ID"] = request_id

        return response
