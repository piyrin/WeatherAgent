"""
=============================================================================
根路由汇总 — 注册所有子路由到 FastAPI 应用
=============================================================================
职责：
  1. 将各模块的子路由汇总到一个地方
  2. 统一设置 URL 前缀（/api/v1）
  3. 注册健康检查路由（无前缀）

设计原则：
  新增 API 时：
    ① 在 api/v1/ 目录新建路由文件
    ② 在此文件的 register_routers() 中添加注册代码
    ③ 无需修改 main.py
=============================================================================
"""

from fastapi import APIRouter, FastAPI

from app.api.health import router as health_router
from app.api.v1.chat import router as chat_router
from app.api.v1.history import router as history_router
from app.utils.logger import logger


def register_routers(app: FastAPI) -> None:
    """
    向 FastAPI 应用注册所有路由

    路由分组：
      - /health                     健康检查（无版本前缀）
      - /api/v1/chat                聊天接口
      - /api/v1/history             历史记录接口
      - /api/v1/history/{id}        会话详情/删除

    版本化策略：
      所有业务 API 放在 /api/v1/ 下，后续升级时可创建 v2 目录，
      新旧版本并行运行，保证向后兼容。

    参数：
        app: FastAPI 应用实例
    """
    # ---- 健康检查（无 API 版本前缀） ----
    app.include_router(health_router)

    # ---- API v1 路由（全部带 /api/v1 前缀） ----
    api_v1 = APIRouter(prefix="/api/v1")

    # 注册子路由
    api_v1.include_router(chat_router)
    api_v1.include_router(history_router)

    # 将 v1 路由器挂载到应用
    app.include_router(api_v1)

    # 打印已注册的路由（便于调试）
    logger.info("API 路由注册完成：")
    for route in app.routes:
        if hasattr(route, "methods") and hasattr(route, "path"):
            logger.info(f"  {route.methods} {route.path}")
