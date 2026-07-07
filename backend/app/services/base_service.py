"""
=============================================================================
Service 基类 — 为所有 Service 提供数据库会话注入
=============================================================================
职责：
  1. 封装 SQLAlchemy Session 的注入
  2. 提供子类共同的数据库操作方法

设计原则：
  所有 Service 继承此类，通过构造函数接收 db: Session，
  避免在每个 Service 的方法参数中重复传递 db。
=============================================================================
"""

from sqlalchemy.orm import Session


class BaseService:
    """
    Service 基类

    子类通过构造函数接收数据库会话：
        class ChatService(BaseService):
            def __init__(self, db: Session):
                super().__init__(db)

            def send_message(self, ...):
                # 通过 self.db 访问数据库
                self.db.add(...)
    """

    def __init__(self, db: Session):
        """
        初始化 Service

        参数：
            db: SQLAlchemy 数据库会话（由 FastAPI 依赖注入提供）
        """
        self.db = db
