"""
=============================================================================
日志配置模块 — 基于 Loguru，支持控制台输出 + 滚动文件
=============================================================================
职责：
  1. 提供统一的日志记录接口（`from app.utils.logger import logger`）
  2. 控制台彩色输出（开发时便于排查）
  3. 文件滚动存储（按大小轮转 + 按时间保留）
  4. 自动过滤：开发环境输出 DEBUG，生产环境只输出 INFO+

使用方式：
    from app.utils.logger import logger

    logger.debug("调试信息")
    logger.info("Agent 开始执行")
    logger.warning("Tool 调用超时")
    logger.error(f"异常详情: {exc}")

设计原则：
  - 全局单例：全项目共用一个 logger 实例，避免日志分散
  - 不污染根 logger：使用 Loguru 的 logger.remove(0) 清除默认 handler
  - 文件安全：自动创建日志目录，磁盘满时不会崩溃
=============================================================================
"""

import sys
from pathlib import Path

from loguru import logger

from app.core.config import settings


def _setup_logger() -> None:
    """
    初始化 Loguru 日志配置

    配置策略：
      1. 移除默认 handler（避免和自定义 handler 重复输出）
      2. 添加控制台 handler（开发时实时查看）
      3. 添加文件 handler（滚动存储 + 自动清理）

    此函数在模块加载时自动执行一次
    """
    # 清除所有已有 handler（包括 Loguru 默认的 stderr handler）
    logger.remove()

    # ---- 控制台输出 ----
    # 使用 colorize 在 IDE 终端中显示彩色日志
    logger.add(
        sys.stdout,
        level=settings.LOG_LEVEL,                # 日志级别
        colorize=True,                            # ANSI 彩色输出
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        # 开发环境启用彩色，生产环境关闭（有些日志收集系统不兼容 ANSI）
        enqueue=False,                            # 不启用异步队列（单线程场景无需）
    )

    # ---- 文件输出 ----
    log_dir = Path(settings.LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)

    logger.add(
        log_dir / "weather_agent_{time:YYYY-MM-DD}.log",
        level=settings.LOG_LEVEL,
        rotation=f"{settings.LOG_MAX_SIZE_MB} MB",     # 按大小轮转
        retention=f"{settings.LOG_RETENTION_DAYS} days", # 按天数保留
        encoding="utf-8",                                # 确保中文不乱码
        enqueue=True,                                    # 异步写入（文件 IO 不阻塞主线程）
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level: <8} | "
            "{name}:{function}:{line} | "
            "{message}"
        ),
    )

    # ---- 启动日志 ----
    logger.info(f"日志系统初始化完成 | 日志级别={settings.LOG_LEVEL} | 日志目录={log_dir.resolve()}")


# 模块加载时自动初始化日志配置
_setup_logger()

# 导出全局唯一的 logger 实例
__all__ = ["logger"]
