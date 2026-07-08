"""
=============================================================================
日期时间工具 — 统一处理 datetime 序列化为前端可用的 ISO 字符串
=============================================================================

核心问题：
  数据库（SQLite）不原生支持时区。TimestampMixin 用 datetime.now(timezone.utc)
  存入 UTC 时间，但 SQLAlchemy 从 SQLite 读取后会丢失时区信息（返回 naive
  datetime）。若直接 isoformat() 输出 '2026-07-08T06:23:29'（无时区标记），
  前端 new Date() 会把它当作本地时间解析，导致 UTC+8 用户看到的时间比实际
  早 8 小时。

解决方案：
  统一通过 format_dt() 序列化：naive datetime 视为 UTC，补上时区后再输出，
  前端即可正确转换为本地时间。
=============================================================================
"""

from datetime import datetime, timezone


def format_dt(dt: datetime | None) -> str:
    """
    将 datetime 格式化为带时区的 ISO 8601 字符串

    规则：
      - None → 空字符串
      - naive datetime（无 tzinfo）→ 视为 UTC，补 +00:00 后输出
      - aware datetime → 原样输出（保留原始时区）

    参数：
        dt: 待格式化的 datetime 对象（可为 None）

    返回值：
        带时区的 ISO 8601 字符串，如 '2026-07-08T06:23:29+00:00'；
        dt 为 None 时返回空字符串。

    用法：
        from app.utils.datetime import format_dt
        created_at: str = format_dt(conv.created_at)
    """
    if dt is None:
        return ""
    if dt.tzinfo is None:
        # SQLite 读取后丢失时区，按存储时的 UTC 还原
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()
