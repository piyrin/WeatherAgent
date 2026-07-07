"""
=============================================================================
LLM + Tool Calling 核心模块
=============================================================================
职责：
  1. 根据配置创建 LLM 实例（支持多 Provider）
  2. generate_plan：让 LLM 生成结构化执行计划（规范第3节）
  3. generate_answer：让 LLM 根据工具调用结果生成最终回答
  4. 提供 System Prompt 管理

规范依据：agent_interface_spec.md 第3节（Planner 输出格式）
=============================================================================
"""

import json
from typing import Any, Dict, List

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

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
            base_url=settings.LLM_BASE_URL,
        )
    except ImportError:
        logger.error("未安装 langchain-community，回退到 OpenAI 兼容接口")
        return _create_openai_compatible_chat_model()
    except Exception as e:
        logger.error(f"创建 ZhipuAI 模型失败: {e}，回退到 OpenAI 兼容接口")
        return _create_openai_compatible_chat_model()


def _create_openai_compatible_chat_model() -> BaseChatModel:
    from langchain_openai import ChatOpenAI
    logger.debug(f"创建 OpenAI 兼容模型 | model={settings.LLM_MODEL} | base_url={settings.LLM_BASE_URL} | api_key_length={len(settings.LLM_API_KEY) if settings.LLM_API_KEY else 0}")
    return ChatOpenAI(
        model=settings.LLM_MODEL,
        base_url=settings.LLM_BASE_URL,
        api_key=settings.LLM_API_KEY,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
    )


def _create_anthropic_compatible_chat_model() -> BaseChatModel:
    from langchain_anthropic import ChatAnthropic
    logger.debug(f"创建 Anthropic 兼容模型 | model={settings.LLM_MODEL} | base_url={settings.LLM_BASE_URL} | api_key_length={len(settings.LLM_API_KEY) if settings.LLM_API_KEY else 0}")
    return ChatAnthropic(
        model=settings.LLM_MODEL,
        base_url=settings.LLM_BASE_URL,
        api_key=settings.LLM_API_KEY,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
    )


_PROVIDER_FACTORY = {
    "zhipuai": _create_zhipuai_chat_model,
    "openai": _create_openai_compatible_chat_model,
    "qwen": _create_openai_compatible_chat_model,
    "deepseek": _create_anthropic_compatible_chat_model,
    "moonshot": _create_openai_compatible_chat_model,
}


def create_llm() -> BaseChatModel:
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


PLAN_PROMPT = """你是一个严格的计划制定助手，必须为天气与出行助手智能体制定包含工具调用的执行计划。

## 你的任务
分析用户问题，识别需要调用的工具，生成结构化的执行计划 JSON。

## 必须调用工具的情况
- 用户提到天气、温度、下雨、带伞 → 必须调用 weather 工具
- 用户提到明天、后天、下周X、日期 → 必须调用 date_parser 工具
- 用户提到路线、出行、去某地 → 必须调用 route_planner 工具
- 用户提到计算、数学问题 → 必须调用 calculator 工具

## 计划格式要求
必须返回严格的 JSON 格式，包含以下字段：
{{
  "user_intent": "用户意图的自然语言描述",
  "intent_category": "意图分类（weather_check/travel_advice/date_query/calculation/general_chat）",
  "reasoning": "必须说明为什么调用这些工具",
  "plan": [
    {{
      "step_id": 1,
      "action": "call_tool",
      "tool_name": "date_parser",
      "tool_input": {{"date_text": "明天"}},
      "reason": "解析相对日期",
      "depends_on": [],
      "on_failure": "abort"
    }},
    {{
      "step_id": 2,
      "action": "call_tool",
      "tool_name": "weather",
      "tool_input": {{"city": "北京", "date": "$step_1.date"}},
      "reason": "查询天气",
      "depends_on": [1],
      "on_failure": "skip_and_notify"
    }},
    {{
      "step_id": 3,
      "action": "observe",
      "reason": "分析工具结果",
      "depends_on": [2]
    }},
    {{
      "step_id": 4,
      "action": "answer",
      "reason": "生成最终回答",
      "depends_on": [1, 2, 3]
    }}
  ],
  "total_steps": 4,
  "estimated_tools": ["date_parser", "weather"]
}}

## 可用工具
- weather: 查询城市天气（参数：city, date）
- date_parser: 解析自然语言日期（参数：date_text）
- route_planner: 规划出行路线（参数：origin, destination, travel_mode）
- calculator: 执行数学计算（参数：expression）

## 当前信息
当前时间：{current_time}

## 示例
用户：明天北京天气怎么样？
输出：
{{
  "user_intent": "查询明天北京的天气",
  "intent_category": "weather_check",
  "reasoning": "用户提到了'明天'（相对日期）和'北京'（城市），需要先解析日期，再查询天气",
  "plan": [
    {{"step_id": 1, "action": "call_tool", "tool_name": "date_parser", "tool_input": {{"date_text": "明天"}}, "reason": "解析'明天'为具体日期", "depends_on": [], "on_failure": "abort"}},
    {{"step_id": 2, "action": "call_tool", "tool_name": "weather", "tool_input": {{"city": "北京", "date": "$step_1.date"}}, "reason": "查询北京天气", "depends_on": [1], "on_failure": "skip_and_notify"}},
    {{"step_id": 3, "action": "observe", "reason": "分析天气结果", "depends_on": [2]}},
    {{"step_id": 4, "action": "answer", "reason": "生成回答", "depends_on": [1, 2, 3]}}
  ],
  "total_steps": 4,
  "estimated_tools": ["date_parser", "weather"]
}}

请只返回 JSON，不要包含任何其他文字。
"""


ANSWER_PROMPT = """你是一个专业的天气与出行助手智能体，名叫"小天气"。

## 你的任务
根据以下信息，生成最终回答：

### 用户问题
{user_message}

### 执行计划
{plan_summary}

### 工具调用结果
{tool_results}

### 观察结论
{observations}

## 回答要求
1. 基于工具返回的实际数据回答，不要编造
2. 回答要简洁、有条理，使用 Markdown 格式
3. 如果涉及出行，结合天气给出建议（是否适合出门、穿什么、带不带伞等）
4. 如果工具调用失败，诚实告知用户并给出替代建议
5. 不要提到"工具"、"调用"等技术术语，用自然语言回答

请直接输出最终回答，不要包含任何前缀或后缀。
"""


# =============================================================================
# Planner — 生成结构化执行计划
# =============================================================================


def generate_plan(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    根据用户问题生成结构化执行计划

    参数：
        state: AgentState

    返回值：
        符合规范第3节的 Plan 结构
    """
    llm = create_llm()

    prompt = ChatPromptTemplate.from_messages([
        ("system", PLAN_PROMPT),
        ("human", "{user_message}"),
    ])

    chain = prompt | llm

    response = chain.invoke({
        "user_message": state["user_message"],
        "current_time": state["current_time"],
    })

    content = response.content.strip()
    print(f"[DEBUG] LLM 返回内容: {content[:2000]}")

    try:
        plan = json.loads(content)
        print(f"[DEBUG] Plan JSON 解析成功: {json.dumps(plan, ensure_ascii=False)[:500]}")
    except json.JSONDecodeError as e:
        print(f"[DEBUG] Plan JSON 解析失败 | 错误: {e} | 原始内容: {content[:1000]}")
        plan = _create_fallback_plan(state["user_message"])

    if not isinstance(plan, dict) or "plan" not in plan:
        print(f"[DEBUG] Plan 格式不正确 | plan字段缺失或类型错误: {type(plan)}")
        plan = _create_fallback_plan(state["user_message"])

    logger.info(f"Plan 生成成功 | intent_category={plan.get('intent_category')} | total_steps={plan.get('total_steps')}")
    return plan


def _create_fallback_plan(user_message: str) -> Dict[str, Any]:
    """创建兜底计划"""
    plan = {
        "user_intent": user_message,
        "intent_category": "general_chat",
        "reasoning": "无法生成结构化计划，直接回答",
        "plan": [
            {
                "step_id": 1,
                "action": "answer",
                "reason": "直接回答用户问题",
                "depends_on": [],
                "on_failure": "abort",
            }
        ],
        "total_steps": 1,
        "estimated_tools": [],
    }
    return plan


# =============================================================================
# Answer Generator — 生成最终回答
# =============================================================================


def generate_answer(state: Dict[str, Any]) -> str:
    """
    根据工具调用结果生成最终回答

    参数：
        state: AgentState

    返回值：
        最终回答文本
    """
    llm = create_llm()

    plan = state.get("plan", {})
    plan_summary = json.dumps(plan, ensure_ascii=False) if plan else "无"

    tool_calls = state.get("tool_calls", [])
    tool_results = []
    for tc in tool_calls:
        result = tc.get("tool_output", {})
        tool_results.append({
            "tool_name": tc.get("tool_name"),
            "input": tc.get("tool_input"),
            "result": result.get("result"),
            "summary": result.get("summary"),
            "success": result.get("success"),
        })

    observations = state.get("observations", [])
    observation_texts = [obs.get("observation", "") for obs in observations]

    prompt = ChatPromptTemplate.from_messages([
        ("system", ANSWER_PROMPT),
        ("human", "用户问题: {user_message}\n执行计划: {plan_summary}\n工具调用结果: {tool_results}\n观察结论: {observations}"),
    ])

    chain = prompt | llm

    response = chain.invoke({
        "user_message": state["user_message"],
        "plan_summary": plan_summary,
        "tool_results": json.dumps(tool_results, ensure_ascii=False),
        "observations": "\n".join(observation_texts) if observation_texts else "无",
    })

    answer = response.content.strip()
    return answer