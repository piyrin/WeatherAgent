"""
=============================================================================
CORS 跨域配置 — 允许前端跨域访问后端 API
=============================================================================
职责：
  1. 配置 CORS 中间件，允许指定的前端来源访问后端 API
  2. 开发环境：允许所有来源（CORS_ORIGINS=*）
  3. 生产环境：仅允许配置的域名

使用方式：
    from app.middleware.cors import setup_cors
    setup_cors(app)  # 在 main.py 中调用

设计原则：
  - 集中管理：CORS 规则不散落在路由中
  - 从配置读取：来源列表从 settings.CORS_ORIGINS_LIST 获取
=============================================================================
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.utils.logger import logger


def setup_cors(app: FastAPI) -> None:
    """
    配置 CORS 中间件

    参数：
        app: FastAPI 应用实例

    CORS 规则：
      - allow_origins:     允许的域名列表（从 settings.CORS_ORIGINS_LIST 读取）
      - allow_credentials: 允许携带 Cookie（后续需要用户认证时启用）
      - allow_methods:     允许的 HTTP 方法（GET/POST/PUT/DELETE/OPTIONS）
      - allow_headers:     允许的请求头（* 表示允许所有）
      - expose_headers:    暴露给前端的响应头

    安全提示：
      生产环境中 CORS_ORIGINS 不应设置为 *，应指定前端的具体域名。
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS_LIST,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
        max_age=600,  # 预检请求缓存时间（秒）
    )

    logger.info(f"CORS 中间件已配置 | 允许来源={settings.CORS_ORIGINS_LIST}")
