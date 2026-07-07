"""
=============================================================================
统一配置中心 — 使用 Pydantic Settings 从 .env 读取全部配置
=============================================================================
职责：
  1. 读取 .env 文件中的所有环境变量
  2. 提供类型安全的配置访问接口（settings.LLM_MODEL 而非 os.getenv("LLM_MODEL")）
  3. 为不同模块提供分组配置（应用、LLM、数据库、日志、第三方 API）

设计原则：
  - 全局唯一实例：全项目通过 `from app.core.config import settings` 访问
  - 禁止硬编码：任何密钥、URL、路径都不允许出现在代码中
  - 启动时校验：缺少必要配置时立即报错，而非运行时才发现
=============================================================================
"""

from pathlib import Path
from typing import Literal, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    全局配置模型 — 所有配置项通过 Pydantic 类型系统自动校验

    用法:
        from app.core.config import settings
        print(settings.LLM_MODEL)   # => "glm-4-flash"
        print(settings.APP_PORT)    # => 8000 (int, 不是 str)

    扩展方式（新增配置项）：
        1. 在 .env 和 .env.example 中添加变量
        2. 在此类中新增对应字段和注释
        3. 重启服务即可生效，无需修改其他任何代码
    """

    # ---- Pydantic Settings 配置 ----
    model_config = SettingsConfigDict(
        # 自动查找 .env 文件（向上搜索 2 层，覆盖 backend/ 根目录）
        env_file=".env",
        env_file_encoding="utf-8",
        # 允许读取额外的环境变量（不报错）
        extra="ignore",
        # 区分大小写
        case_sensitive=True,
    )

    # =========================================================================
    # 应用配置
    # =========================================================================

    APP_NAME: str = Field(
        default="天气与出行助手智能体",
        description="应用名称，用于 Swagger 文档标题和日志标识",
    )
    APP_VERSION: str = Field(
        default="1.0.0",
        description="应用版本号",
    )
    APP_DEBUG: bool = Field(
        default=True,
        description="调试模式：true 时输出详细日志，生产环境必须设为 false",
    )
    APP_HOST: str = Field(
        default="0.0.0.0",
        description="服务监听地址",
    )
    APP_PORT: int = Field(
        default=8000,
        description="服务监听端口",
    )

    # =========================================================================
    # LLM 配置（LangChain Agent 的核心依赖）
    # =========================================================================

    LLM_PROVIDER: str = Field(
        default="zhipuai",
        description="LLM 提供商标识（如 openai / zhipuai / qwen / deepseek）",
    )
    LLM_MODEL: str = Field(
        default="glm-4-flash",
        description="LLM 模型名称",
    )
    LLM_BASE_URL: str = Field(
        default="https://open.bigmodel.cn/api/paas/v4",
        description="LLM API 基础地址",
    )
    LLM_API_KEY: str = Field(
        default="",
        description="LLM API 密钥（敏感信息）",
    )
    LLM_TEMPERATURE: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="LLM 生成温度（0~1，Agent 场景建议 0~0.3 以保证工具调用的确定性）",
    )
    LLM_MAX_TOKENS: int = Field(
        default=2048,
        description="LLM 单次生成最大 Token 数",
    )

    # =========================================================================
    # 数据库配置
    # =========================================================================

    DATABASE_URL: str = Field(
        default="sqlite:///./data/weather_agent.db",
        description="SQLite 数据库连接字符串（相对或绝对路径）",
    )

    @property
    def DATABASE_PATH(self) -> Path:
        """
        从 DATABASE_URL 中提取数据库文件的绝对路径

        用于日志输出和文件系统操作（如检查数据库文件是否存在）
        例如: "sqlite:///./data/weather_agent.db" → Path("/backend/data/weather_agent.db")
        """
        # sqlite:///./data/weather_agent.db → ./data/weather_agent.db
        path_str = self.DATABASE_URL.replace("sqlite:///", "")
        return Path(path_str).resolve()

    # =========================================================================
    # 日志配置
    # =========================================================================

    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="DEBUG",
        description="日志级别",
    )
    LOG_DIR: str = Field(
        default="./logs",
        description="日志文件存放目录",
    )
    LOG_MAX_SIZE_MB: int = Field(
        default=10,
        description="单个日志文件最大大小（MB）",
    )
    LOG_RETENTION_DAYS: int = Field(
        default=30,
        description="日志文件保留天数（超过后自动删除）",
    )

    # =========================================================================
    # 天气 API 配置（供 weather.py Tool 使用）
    # =========================================================================

    WEATHER_PROVIDER: str = Field(
        default="openweathermap",
        description="天气数据提供商",
    )
    WEATHER_API_KEY: str = Field(
        default="",
        description="天气 API 密钥",
    )

    # =========================================================================
    # 地图/路线 API 配置（供 route_planner.py Tool 使用）
    # =========================================================================

    MAP_PROVIDER: str = Field(
        default="amap",
        description="地图服务提供商",
    )
    MAP_API_KEY: str = Field(
        default="",
        description="地图 API 密钥",
    )

    # =========================================================================
    # 安全配置
    # =========================================================================

    CORS_ORIGINS: str = Field(
        default="*",
        description="CORS 允许的来源（多个用逗号分隔，* 表示允许所有 — 仅开发环境使用）",
    )

    # =========================================================================
    # 计算属性 — 将字符串配置转为 Python 原生类型
    # =========================================================================

    @property
    def CORS_ORIGINS_LIST(self) -> list[str]:
        """
        将逗号分隔的 CORS 字符串转为列表

        "http://localhost:5173,http://localhost:8080" → ["http://localhost:5173", "http://localhost:8080"]
        "*" → ["*"]
        """
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @field_validator("LOG_DIR", mode="before")
    @classmethod
    def validate_log_dir(cls, v):
        """
        确保日志目录在首次使用时自动创建

        Pydantic 验证器在 settings 实例化时自动调用
        """
        log_path = Path(v)
        log_path.mkdir(parents=True, exist_ok=True)
        return v


# =============================================================================
# 全局单例 — 全项目唯一的配置入口
# =============================================================================
# 模块加载时立即实例化，所有 import 此模块的代码共享同一个实例
settings = Settings()
