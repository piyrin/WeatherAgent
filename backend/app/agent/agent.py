"""
=============================================================================
LLM 工厂 — 创建配置好的 LLM 实例（被 LangGraph Agent 复用）
=============================================================================
职责：
  1. 根据配置创建 LLM 实例（支持多 Provider）
  2. 提供 create_llm() 统一入口

Agent 架构变化（v2.0）：
  - 旧版：create_agent(tools) → AgentExecutor（LangChain 简单 Agent）
  - 新版：create_llm() → create_graph(llm) → AgentExecutor（LangGraph StateGraph）
  - 此文件只保留 LLM 工厂，不再包含 Agent 创建逻辑

设计原则：
  - LLM Provider 可切换：通过 settings.LLM_PROVIDER 切换模型厂商
  - 单例模式：整个 Agent 共享一个 LLM 实例
=============================================================================
"""

from langchain_core.language_models import BaseChatModel

from app.core.config import settings
from app.utils.logger import logger


# =============================================================================
# LLM 工厂 — 根据配置创建对应 Provider 的 ChatModel
# =============================================================================

def _create_zhipuai_chat_model() -> BaseChatModel:
    try:
        from langchain_community.chat_models import ChatZhipuAI

        return ChatZhipuAI(
            model=settings.LLM_MODEL,
            api_key=settings.LLM_API_KEY,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
        )
    except ImportError:
        logger.error("未安装 langchain-community，回退到 OpenAI 兼容接口")
        return _create_openai_compatible_chat_model()


def _create_openai_compatible_chat_model() -> BaseChatModel:
    """通过 OpenAI 兼容接口创建 ChatModel"""
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=settings.LLM_MODEL,
        base_url=settings.LLM_BASE_URL,
        api_key=settings.LLM_API_KEY,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
    )


# LLM Provider 工厂映射表
_PROVIDER_FACTORY = {
    "zhipuai": _create_zhipuai_chat_model,
    "openai": _create_openai_compatible_chat_model,
    "qwen": _create_openai_compatible_chat_model,
    "deepseek": _create_openai_compatible_chat_model,
    "moonshot": _create_openai_compatible_chat_model,
}


def create_llm() -> BaseChatModel:
    """
    根据配置创建 LLM 实例

    通过 settings.LLM_PROVIDER 查找对应的工厂函数并调用。
    如果 provider 不在映射表中，默认使用 OpenAI 兼容接口。

    返回值：
        BaseChatModel 实例（LangChain 标准聊天模型）
    """
    provider = settings.LLM_PROVIDER.lower()
    factory = _PROVIDER_FACTORY.get(provider)

    if factory is None:
        logger.warning(
            f"未知的 LLM Provider: {provider}，"
            f"默认使用 OpenAI 兼容接口（base_url={settings.LLM_BASE_URL}）"
        )
        factory = _create_openai_compatible_chat_model

    llm = factory()
    logger.info(
        f"LLM 创建成功 | provider={provider} | "
        f"model={settings.LLM_MODEL} | temperature={settings.LLM_TEMPERATURE}"
    )
    return llm
