"""
=============================================================================
ORM 基类 & 通用 Mixin — 所有模型的父类
=============================================================================
职责：
  1. BaseModel：为所有模型提供 UUID 主键（性能优于自增 ID）
  2. TimestampMixin：为标准表提供 created_at / updated_at 时间戳

设计原则：
  - UUID 主键的好处：
    ① 分布式友好（不需要中心化的 ID 生成器）
    ② 安全（无法通过 ID 推测数据规模）
    ③ 前端可用（无需等待数据库返回自增 ID）
  - Mixin 模式：将通用字段抽离，避免每个 Model 重复定义
=============================================================================
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    """
    获取当前 UTC 时间

    独立函数而非 lambda 的原因：
      SQLAlchemy 的 default 参数需要一个可调用对象，
      lambda 在序列化时可能出问题，独立函数更安全。
    """
    return datetime.now(timezone.utc)


class BaseModel(Base):
    """
    所有模型的抽象基类

    特性：
      - 继承自 SQLAlchemy DeclarativeBase（获得 ORM 映射能力）
      - __abstract__ = True：不会在数据库中创建此表
      - id：UUID 类型主键，服务端自动生成（Python 端而非数据库端）
    """

    __abstract__ = True

    # UUID 主键：使用 Python 的 uuid.uuid4() 生成，而非数据库的 gen_random_uuid()
    # 原因：SQLite 不原生支持 UUID 类型，用 String(36) 存储
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),  # 每次插入时生成新的 UUID
        index=False,                         # 主键自带索引，无需额外索引
        comment="UUID 主键",
    )


class TimestampMixin:
    """
    时间戳 Mixin — 为模型添加创建时间和更新时间

    用法：
        class Conversation(BaseModel, TimestampMixin):
            ...

    注意：
      - Mixin 不继承 Base，通过多重继承组合到具体模型中
      - created_at 只在首次插入时设置（default）
      - updated_at 每次更新时自动刷新（onupdate）
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
        comment="创建时间（UTC）",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,           # 每次 UPDATE 时自动更新为当前时间
        nullable=False,
        comment="最后更新时间（UTC）",
    )
