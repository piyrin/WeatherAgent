"""
=============================================================================
FastAPI 应用入口 — 生命周期管理 & 中间件注册
=============================================================================
职责：
  1. 创建 FastAPI 应用实例
  2. 注册中间件（CORS、请求日志、异常处理）
  3. 注册路由
  4. 管理应用生命周期（启动时建表、关闭时清理）

文件路径：
    D:/code/agent/weather-agent/backend/app/main.py

启动方式：
    python run.py        # 推荐
    或
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
=============================================================================
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import register_routers
from app.core.config import settings
from app.core.database import init_db
from app.middleware.cors import setup_cors
from app.middleware.exception_handler import register_exception_handlers
from app.middleware.request_log import RequestLogMiddleware
from app.utils.logger import logger

# 导入所有模型（确保 init_db 能发现所有表）
import app.models  # noqa: F401 — 触发模型注册


# =============================================================================
# 应用生命周期管理
# =============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 应用生命周期管理

    Startup：
      - 初始化数据库（自动创建表）
      - 打印启动信息

    Shutdown：
      - 打印关闭信息
      - 清理资源（预留）
    """
    # ===== Startup =====
    logger.info("=" * 60)
    logger.info(f"  {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"  Debug: {settings.APP_DEBUG}")
    logger.info(f"  LLM: {settings.LLM_PROVIDER}/{settings.LLM_MODEL}")
    logger.info(f"  Database: {settings.DATABASE_URL}")
    logger.info("=" * 60)

    # 初始化数据库表
    init_db()

    logger.info(f"🚀 应用启动成功 | http://{settings.APP_HOST}:{settings.APP_PORT}")
    logger.info(f"📖 API 文档: http://{settings.APP_HOST}:{settings.APP_PORT}/docs")

    yield  # 应用运行期间停在此处

    # ===== Shutdown =====
    logger.info("应用正在关闭...")


# =============================================================================
# 创建 FastAPI 应用
# =============================================================================

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "基于 LangChain 的天气与出行助手智能体系统。\n\n"
        "### 功能\n"
        "- 自然语言天气查询\n"
        "- 智能日期解析\n"
        "- 出行路线规划\n"
        "- 数学计算\n"
        "- 多轮对话记忆\n\n"
        "### Agent 工作流\n"
        "理解任务 → 制定计划 → 调用工具 → 观察结果 → 生成回答"
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# =============================================================================
# 注册中间件（顺序重要）
# =============================================================================

# 1. CORS 中间件（最先处理，确保跨域请求不被拒绝）
setup_cors(app)

# 2. 异常处理（必须在路由注册前注册）
register_exception_handlers(app)

# 3. 请求日志中间件
app.add_middleware(RequestLogMiddleware)

# =============================================================================
# 注册路由
# =============================================================================

register_routers(app)
