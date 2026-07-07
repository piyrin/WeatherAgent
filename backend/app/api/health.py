"""
=============================================================================
健康检查接口 — GET /health
=============================================================================
职责：
  1. 返回服务运行状态（供监控系统/前端检测）
  2. 返回基本服务信息（版本、运行时间等）

不包含 /api/ 前缀，方便负载均衡器和监控系统直接调用。
=============================================================================
"""

import time

from fastapi import APIRouter

from app.core.config import settings
from app.utils.response import success

router = APIRouter(tags=["系统"])

# 服务启动时间（模块加载时记录）
_START_TIME = time.time()


@router.get(
    "/health",
    summary="健康检查",
    description="返回服务运行状态和基本信息。",
)
async def health_check() -> dict:
    """
    健康检查接口

    返回：
        {
            "code": 200,
            "data": {
                "status": "healthy",
                "app_name": "天气与出行助手智能体",
                "version": "1.0.0",
                "uptime_seconds": 123456.78
            }
        }
    """
    uptime = time.time() - _START_TIME

    return success(data={
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "uptime_seconds": round(uptime, 2),
    })
