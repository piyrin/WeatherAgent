"""
=============================================================================
数据库引擎 & 会话管理 — 基于 SQLAlchemy 2.0 异步风格
=============================================================================
职责：
  1. 创建 SQLAlchemy 引擎（连接到 SQLite）
  2. 提供会话工厂（sessionmaker）
  3. 提供 FastAPI 依赖注入函数（get_db）
  4. 声明 SQLAlchemy Base（所有 ORM 模型的父类）
  5. 提供 init_db() 工具函数（启动时自动建表）

使用方式：
    # 在模型文件中继承 Base
    from app.core.database import Base
    class Conversation(Base): ...

    # 在 FastAPI 路由中注入 DB Session
    from app.core.database import get_db
    @router.post("/chat")
    async def chat(db: Session = Depends(get_db)): ...

设计原则：
  - SQLite 使用同步引擎（check_same_thread=False 允许多线程）
  - echo=settings.APP_DEBUG：开发环境打印 SQL，生产环境关闭
  - 所有表创建通过 Base.metadata.create_all 自动完成
=============================================================================
"""

from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings
from app.utils.logger import logger


# =============================================================================
# 数据库引擎 — 全局单例
# =============================================================================

def _create_engine() -> Engine:
    """
    创建 SQLAlchemy 引擎

    SQLite 特殊处理：
      - check_same_thread=False：允许跨线程使用同一连接（FastAPI 默认多线程）
      - connect_args 中的参数对非 SQLite 数据库无效（安全忽略）

    返回值：
        SQLAlchemy Engine 实例
    """
    connect_args = {}
    if "sqlite" in settings.DATABASE_URL:
        # SQLite 特有参数：允许多线程访问
        connect_args["check_same_thread"] = False

    engine = create_engine(
        settings.DATABASE_URL,
        echo=settings.APP_DEBUG,      # 开发环境打印 SQL 语句（便于调试）
        connect_args=connect_args,
        # pool_pre_ping=True 对 SQLite 不必要，但保留以防日后切换到 PostgreSQL
    )

    logger.info(f"数据库引擎创建成功 | 连接串={settings.DATABASE_URL}")
    return engine


# 全局引擎实例
engine: Engine = _create_engine()

# =============================================================================
# 会话工厂
# =============================================================================

# 创建会话工厂（autocommit=False, autoflush=False 为手动控制事务边界）
SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

# =============================================================================
# 声明式基类 — 所有 ORM 模型必须继承此类
# =============================================================================


class Base(DeclarativeBase):
    """
    SQLAlchemy 声明式基类

    所有 ORM 模型通过继承此类获得声明式映射能力：
        class Conversation(Base):
            __tablename__ = "conversations"
            ...

    注意：
      - 不要直接实例化 Base
      - 模型文件中的类继承此 Base 即可自动注册到元数据
    """
    pass


# =============================================================================
# FastAPI 依赖注入 — get_db
# =============================================================================


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI 依赖注入函数：为每个请求提供一个独立的数据库会话

    用法：
        @router.post("/chat")
        async def chat(db: Session = Depends(get_db)):
            ...

    生命周期：
        请求进入 → 创建新 Session → 注入到路由函数 → 请求结束 → 自动关闭 Session

    注意：
        yield 后的 finally 块保证即使路由函数抛出异常，Session 也会被正确关闭，
        防止数据库连接泄漏。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =============================================================================
# 建表工具 — init_db
# =============================================================================


def init_db() -> None:
    """
    初始化数据库：自动创建所有 ORM 模型对应的表

    调用时机：
        - 应用启动时（main.py 的 lifespan 事件中）
        - 测试脚本中

    原理：
        Base.metadata.create_all 会遍历所有继承了 Base 的模型类，
        根据 __tablename__ 和 Column 定义自动创建表。
        如果表已存在则跳过（不会覆盖数据）。

    注意：
        必须先 import 所有模型文件，否则这些模型不会被注册到 Base.metadata 中。
        推荐在调用此函数前导入 models 包。
    """
    logger.info("开始初始化数据库表结构...")
    Base.metadata.create_all(bind=engine)
    logger.info("数据库表结构初始化完成")
