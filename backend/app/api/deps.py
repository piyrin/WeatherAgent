"""
=============================================================================
路由层公共依赖 — FastAPI Depends 复用
=============================================================================
职责：
  1. 提供 get_db 依赖（从 core/database.py 重新导出，统一入口）
  2. 提供分页参数依赖（page, page_size）
  3. 提供可选的 API Key 校验依赖

使用方式：
    from app.api.deps import get_db, PaginationParams

    @router.get("/history")
    async def get_history(
        db: Session = Depends(get_db),
        pagination: PaginationParams = Depends(),
    ):
        ...
=============================================================================
"""

from dataclasses import dataclass

from fastapi import Query

from app.core.database import get_db

# 重新导出 get_db，方便 API 层统一从 deps 导入
__all__ = ["get_db", "PaginationParams"]


@dataclass
class PaginationParams:
    """
    分页参数依赖

    用法：
        @router.get("/history")
        async def get_history(pagination: PaginationParams = Depends()):
            page = pagination.page
            page_size = pagination.page_size
    """

    page: int = Query(
        default=1,
        ge=1,
        description="页码（从 1 开始）",
    )
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
        description="每页条数（1-100）",
    )
