"""
=============================================================================
LangChain Agent 工厂 — 创建配置好的 Agent 实例
=============================================================================
职责：
  1. 根据配置创建 LLM 实例（支持多 Provider）
  2. 加载 System Prompt（定义 Agent 的行为模式）
  3. 绑定 Tools 到 LLM（实现 Function Calling）
  4. 创建并返回 ReAct Agent

Agent 类型：
  使用 LangChain 的 create_react_agent，它支持：
    - ReAct 模式：思考(Thought) → 行动(Action) → 观察(Observation) → ...
    - Function Calling：LLM 自动选择并调用工具
    - 多轮推理：根据工具返回结果继续思考

设计原则：
  - LLM Provider 可切换：通过 settings.LLM_PROVIDER 切换模型厂商
  - Tool 动态绑定：从 tool_registry 获取工具列表，无需硬编码
  - Prompt 模板化：System Prompt 独立管理，方便调优
=============================================================================
"""

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import BaseTool as LangChainBaseTool

from app.core.config import settings
from app.utils.logger import logger


# =============================================================================
# LLM 工厂 — 根据配置创建对应 Provider 的 ChatModel
# =============================================================================

def _create_zhipuai_chat_model() -> BaseChatModel:
    """
    创建智谱 AI（ChatGLM）的 ChatModel

    使用 langchain-community 的 ChatZhipuAI。
    需要安装：pip install langchain-community
    """
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
    """
    通过 OpenAI 兼容接口创建 ChatModel

    适用于大多数国产模型厂商（智谱、通义千问、DeepSeek 等），
    它们都提供与 OpenAI API 兼容的接口。
    """
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=settings.LLM_MODEL,
        base_url=settings.LLM_BASE_URL,
        api_key=settings.LLM_API_KEY,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
    )


# LLM Provider 工厂映射表
# 新增 Provider 时在此字典中添加一项即可
_PROVIDER_FACTORY = {
    "zhipuai": _create_zhipuai_chat_model,
    "openai": _create_openai_compatible_chat_model,
    "qwen": _create_openai_compatible_chat_model,      # 通义千问使用 OpenAI 兼容接口
    "deepseek": _create_openai_compatible_chat_model,   # DeepSeek 使用 OpenAI 兼容接口
    "moonshot": _create_openai_compatible_chat_model,   # Moonshot 使用 OpenAI 兼容接口
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


# =============================================================================
# System Prompt — 定义 Agent 的行为模式
# =============================================================================

SYSTEM_PROMPT = """你是一个专业的天气与出行助手智能体，名叫"小天气"。

## 你的能力
你可以使用以下工具来帮助用户：
- **weather**: 查询城市天气（温度、湿度、风力、天气状况等）
- **date_parser**: 解析自然语言日期（如"明天"→具体日期）
- **route_planner**: 规划出行路线（距离、耗时、出行建议）
- **calculator**: 执行数学计算

## 你的工作流程
当用户提出问题时，你需要：
1. **理解意图**：分析用户真正想知道什么
2. **制定计划**：确定需要调用哪些工具、按什么顺序调用
3. **执行调用**：使用工具获取准确数据
4. **综合分析**：结合工具返回的数据，给出专业、完整的回答
5. **出行建议**：如果涉及出行，结合天气给出建议（是否适合出门、穿什么、带不带伞等）

## 行为规范
- 回答前先分析问题，不要直接猜测
- 涉及日期的地方先调用 date_parser 解析，不要自己算
- 涉及天气的地方必须调用 weather 工具，不要编造数据
- 回答要简洁、有条理，使用 Markdown 格式
- 如果工具调用失败，诚实告知用户并给出替代建议

## 当前信息
当前日期：{current_date}
用户所在城市（如果未指定）：默认使用北京

现在，请开始帮助用户解决问题。
"""


# =============================================================================
# Agent 创建函数
# =============================================================================

def create_agent(tools: list[LangChainBaseTool]) -> "AgentExecutor":
    """
    创建配置好的 LangChain Agent

    参数：
        tools: LangChain BaseTool 列表（从 tool_registry 获取）

    返回值：
        AgentExecutor 实例，可以直接调用 invoke({"input": "..."})

    注意：
        - 需要先创建 LLM 实例（create_llm()）
        - 需要先从 tool_registry 获取工具列表
        - Agent 内部使用 Tool Calling（Function Calling）模式进行推理和工具调用
    """
    # 创建 LLM
    llm = create_llm()

    # 构建 Prompt 模板
    # MessagesPlaceholder 会在运行时插入对话历史和中间步骤
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    # 创建 Tool Calling Agent（使用 Function Calling，无需 ReAct 模板）
    agent = create_tool_calling_agent(
        llm=llm,
        tools=tools,
        prompt=prompt,
    )

    # 使用 AgentExecutor 运行 Agent，它会自动处理 intermediate_steps 循环
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=settings.APP_DEBUG,
        handle_parsing_errors=True,
    )

    logger.info(
        f"Agent 创建成功 | tools={[t.name for t in tools]}"
    )

    return agent_executor
