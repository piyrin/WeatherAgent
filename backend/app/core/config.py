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
    # 高德开放平台（AMAP）配置 — 天气 / 路线 / 地理编码 / POI / 距离 等所有服务共用
    # =========================================================================
    # 设计原则：
    #   1. 高德开放平台的所有服务（天气查询、路线规划、地理编码、POI搜索等）
    #      共用一个 AMAP_API_KEY，不维护多个重复 Key。
    #   2. WEATHER_PROVIDER / MAP_PROVIDER 保留，支持未来切换其他平台
    #      （如 OpenWeather、腾讯地图、百度地图），但当前默认均为 amap。
    #   3. 通过 get_provider_api_key() 预留下游 Tool 独立 API Key 的扩展能力，
    #      当前实现直接返回 AMAP_API_KEY，无需修改任何 Tool。

    AMAP_API_KEY: str = Field(
        default="",
        description="高德开放平台 API Key（天气、地图、路线、地理编码等服务共用）",
    )
    AMAP_BASE_URL: str = Field(
        default="https://restapi.amap.com",
        description="高德开放平台 API 基础地址",
    )

    @property
    def AMAP_WEATHER_URL(self) -> str:
        """高德天气 API 完整 URL（基于 AMAP_BASE_URL 拼接）"""
        return f"{self.AMAP_BASE_URL}/v3/weather/weatherInfo"

    def amap_direction_url(self, mode: str = "driving") -> str:
        """
        高德路径规划 API 完整 URL（基于 AMAP_BASE_URL 拼接）

        参数：
            mode: 出行方式
                driving  → /v3/direction/driving
                transit  → /v3/direction/transit/integrated（公交/地铁换乘）
                walking  → /v3/direction/walking
        """
        path_map = {
            "driving": "driving",
            "transit": "transit/integrated",
            "walking": "walking",
        }
        path = path_map.get(mode, "driving")
        return f"{self.AMAP_BASE_URL}/v3/direction/{path}"

    WEATHER_PROVIDER: str = Field(
        default="amap",
        description="天气数据提供商（当前: amap，预留: openweathermap）",
    )

    MAP_PROVIDER: str = Field(
        default="amap",
        description="地图/路线服务提供商（当前: amap，预留: tencent / baidu）",
    )


    @property
    def WEATHER_API_KEY(self) -> str:
        return self.AMAP_API_KEY

    @property
    def MAP_API_KEY(self) -> str:
        return self.AMAP_API_KEY

    @property
    def WEATHER_BASE_URL(self) -> str:
        return self.AMAP_BASE_URL

    @property
    def MAP_BASE_URL(self) -> str:
        return self.AMAP_BASE_URL

    # ---- Provider API Key 扩展点 ----

    def get_provider_api_key(self, provider: str) -> str:
        """
        根据 Provider 返回对应的 API Key（预留未来多 Provider 支持）

        当前实现：所有高德相关服务返回 AMAP_API_KEY。
        未来扩展：可在此方法中根据 provider 返回不同 Key。

        参数：
            provider: 服务提供商（"amap" / "openweathermap" / "tencent" / "baidu"）

        返回值：
            对应的 API Key

        示例：
            key = settings.get_provider_api_key("amap")  # → AMAP_API_KEY
            key = settings.get_provider_api_key("openweathermap")  # → OPENWEATHER_API_KEY (未来)
        """
        provider_key_map = {
            "amap": self.AMAP_API_KEY,
            # 未来扩展示例：
            # "openweathermap": self.OPENWEATHER_API_KEY,
            # "tencent": self.TENCENT_MAP_API_KEY,
            # "baidu": self.BAIDU_MAP_API_KEY,
        }
        key = provider_key_map.get(provider, "")
        if not key:
            logger = __import__("app.utils.logger", fromlist=["logger"]).logger
            logger.warning(
                f"[config] Provider '{provider}' 的 API Key 未配置，"
                f"使用 AMAP_API_KEY 作为默认值"
            )
            return self.AMAP_API_KEY
        return key

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
