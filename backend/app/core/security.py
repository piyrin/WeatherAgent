"""
=============================================================================
安全工具模块 — API Key 校验、预留认证框架
=============================================================================
职责：
  1. 提供 API Key 校验工具（当前阶段用于简单的服务间认证）
  2. 预留 JWT Token 创建和验证接口（后续扩展用户系统时启用）
  3. 密码哈希工具（预留）

当前阶段：
  课程设计项目无需复杂的用户认证系统，本模块提供基础的 API Key 校验能力，
  确保只有持有正确 Key 的前端才能调用后端 API。

设计原则：
  - 最小权限：只暴露当前需要的接口
  - 可扩展：JWT 相关方法接口已预留，后续只需实现逻辑
=============================================================================
"""

import secrets
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.utils.logger import logger


# =============================================================================
# API Key 校验（当前阶段使用）
# =============================================================================

def verify_api_key(api_key: str | None) -> bool:
    """
    校验 API Key 是否有效

    简单实现：比对 LLM_API_KEY 的前 16 位作为内部 API Key。
    生产环境中应从数据库或 Redis 中读取密钥列表进行比对。

    参数：
        api_key: 请求头中的 API Key（可能为 None）

    返回值：
        True 表示校验通过，False 表示无效
    """
    if not api_key:
        return False

    # 如果 LLM_API_KEY 未配置或使用默认值，允许所有请求通过（开发模式）
    if not settings.LLM_API_KEY or settings.LLM_API_KEY == "your_actual_api_key_here":
        logger.debug("LLM_API_KEY 未配置，跳过 API Key 校验")
        return True

    # 简单比对（生产环境应使用常量时间比较以防止时序攻击）
    expected_key = settings.LLM_API_KEY[:16]
    return secrets.compare_digest(api_key, expected_key)


# =============================================================================
# JWT Token（预留 — 后续扩展用户系统时启用）
# =============================================================================

# JWT 签名密钥（预留）
# 生产环境应从环境变量或密钥管理服务中读取
_JWT_SECRET_KEY: str = settings.LLM_API_KEY or secrets.token_hex(32)
_JWT_ALGORITHM: str = "HS256"
_JWT_EXPIRE_MINUTES: int = 60 * 24  # 默认 24 小时


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    创建 JWT Access Token（预留接口）

    当前返回一个占位 Token，后续接入 PyJWT 库后实现完整的签名逻辑。

    参数：
        data: 要编码到 Token 中的载荷数据（如 {"sub": user_id}）
        expires_delta: Token 过期时间（默认 24 小时）

    返回值：
        JWT Token 字符串
    """
    # 预留接口，暂时返回一个占位字符串
    # 后续实现：
    #   import jwt
    #   expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=_JWT_EXPIRE_MINUTES))
    #   to_encode = data.copy()
    #   to_encode.update({"exp": expire})
    #   return jwt.encode(to_encode, _JWT_SECRET_KEY, algorithm=_JWT_ALGORITHM)
    logger.warning("JWT 功能尚未实现，create_access_token 返回占位 Token")
    return f"placeholder_token_{data.get('sub', 'unknown')}"


def verify_access_token(token: str) -> dict | None:
    """
    验证 JWT Access Token（预留接口）

    参数：
        token: 待验证的 JWT Token 字符串

    返回值：
        解析后的载荷字典，校验失败返回 None
    """
    # 预留接口
    # 后续实现：
    #   import jwt
    #   try:
    #       payload = jwt.decode(token, _JWT_SECRET_KEY, algorithms=[_JWT_ALGORITHM])
    #       return payload
    #   except jwt.PyJWTError:
    #       return None
    logger.warning("JWT 功能尚未实现，verify_access_token 返回 None")
    return None
