"""
=============================================================================
Planner Node — 任务规划
=============================================================================
职责：
  1. 调用 LLM 将意图理解结果转化为结构化执行计划（JSON）
  2. 将计划写入 state.plan_steps 和 state.plan_summary
  3. 初始化 current_step_index = 0

输入（State 读取）：
  - understanding: 意图理解结果
  - user_message: 用户原始输入

输出（State 写入）：
  - plan_summary: 计划人类可读摘要
  - plan_steps: 结构化步骤列表
  - current_step_index: 重置为 0
  - steps: 追加一条 "plan" 步骤

设计说明：
  - LLM 输出 JSON 数组，需要清理 markdown 包裹（```json ... ```）
  - 每个 plan step 有明确的 action、tool_name、tool_input
  - 解析失败时有降级策略（直接进入 answer）
=============================================================================
"""

import json
import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.language_models import BaseChatModel

from app.agent.state import AgentState
from app.agent.prompts.planner_prompt import (
    PLANNER_SYSTEM_PROMPT,
    PLANNER_HUMAN_TEMPLATE,
)
from app.agent.tool_registry import tool_registry
from app.utils.logger import logger


def _build_tools_info() -> str:
    """
    构建可用工具的描述文本，注入 Planner Prompt

    防御性处理：工具描述中如果包含花括号 { }，会被后续 .format() 误解析，
    因此先转义为 {{ 和 }}。

    返回值：
        "1. weather: 查询城市天气...
         2. date_parser: 解析自然语言日期..."
    """
    lines = []
    for i, tool in enumerate(tool_registry.get_all(), start=1):
        # 防御性转义：工具描述中可能有 JSON 示例等含花括号的内容
        desc = tool.description.replace("{", "{{").replace("}", "}}")
        lines.append(f"{i}. **{tool.name}**: {desc}")
    return "\n".join(lines)


def _extract_json(text: str) -> str:
    """
    从 LLM 输出中提取纯 JSON 文本

    处理 LLM 常见的输出变体：
      - ```json ... ```
      - ``` ... ```
      - 前后有额外文字

    参数：
        text: LLM 原始输出文本

    返回值：
        清理后的 JSON 文本
    """
    # 尝试提取 ```json ... ``` 中的内容
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        return match.group(1).strip()

    # 尝试找到第一个 [ 和最后一个 ] 之间的内容
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        return text[start:end + 1]

    return text.strip()


_CN_DAY_NUMBERS = {
    "一": 1,
    "二": 2,
    "两": 2,
    "俩": 2,
    "三": 3,
    "四": 4,
}


def _extract_forecast_days(user_message: str) -> int | None:
    """
    从用户问题中提取“未来/接下来 N 天”的预报天数。

    高德天气预报最多返回 4 天，所以这里也限制到 1-4。
    """
    patterns = [
        r"(?:未来|接下来|之后|最近|近)\s*([1-4一二两俩三四])\s*天",
        r"([1-4一二两俩三四])\s*天(?:内|里|之内)",
    ]
    for pattern in patterns:
        match = re.search(pattern, user_message)
        if not match:
            continue
        raw = match.group(1)
        days = int(raw) if raw.isdigit() else _CN_DAY_NUMBERS.get(raw)
        if days:
            return max(1, min(days, 4))
    if re.search(r"(?:未来|接下来|最近|近)几天", user_message):
        return 3
    return None


def _normalize_weather_plan(plan_steps: list[dict], user_message: str) -> list[dict]:
    """
    对 LLM 生成的天气计划做确定性修正。

    典型问题是“未来三天会下雨吗”被规划成只查“今天”。这里保留 LLM
    的整体计划，只补充 weather.days，确保工具拿到多天预报需求。
    """
    days = _extract_forecast_days(user_message)
    if not days:
        return plan_steps

    for step in plan_steps:
        if step.get("action") != "call_tool" or step.get("tool_name") != "weather":
            continue
        tool_input = step.setdefault("tool_input", {})
        tool_input["days"] = days
        if tool_input.get("date") in ("今天", "今日", "解析后日期"):
            tool_input.pop("date", None)
        reason = step.get("reason", "")
        if "未来" not in reason and "多天" not in reason:
            step["reason"] = f"{reason}；用户询问未来{days}天，需查询多天预报".strip("；")
    return plan_steps


def _normalize_route_weather(plan_steps: list[dict], user_message: str) -> list[dict]:
    """
    确定性修正：如果规划了路径规划（route_planner）但没有天气查询（weather），
    自动在 answer 步骤前补充 weather 步骤。

    出行场景下天气是重要参考，planner LLM 可能漏掉，这里兜底确保 weather 被调用。
    adcode 从 geocoding 或 city_resolver 的输出引用（$step_N.adcode）。
    """
    tool_steps = [s for s in plan_steps if s.get("action") == "call_tool"]
    has_route = any(s.get("tool_name") == "route_planner" for s in tool_steps)
    has_weather = any(s.get("tool_name") == "weather" for s in tool_steps)

    if not has_route or has_weather:
        return plan_steps  # 无路线或已有天气，不处理

    # 找 adcode 来源：优先 geocoding，其次 city_resolver
    adcode_source = None
    adcode_depends = []
    for s in tool_steps:
        if s.get("tool_name") == "geocoding":
            adcode_source = f"$step_{s['step_id']}.adcode"
            adcode_depends.append(s["step_id"])
            break
    if not adcode_source:
        for s in tool_steps:
            if s.get("tool_name") == "city_resolver":
                adcode_source = f"$step_{s['step_id']}.adcode"
                adcode_depends.append(s["step_id"])
                break

    if not adcode_source:
        logger.warning(
            "[planner] 路线规划存在但无 geocoding/city_resolver 提供 adcode，跳过 weather 补充"
        )
        return plan_steps

    # 找 date_parser（可选，提供 date）
    date_source = None
    date_depends = []
    for s in tool_steps:
        if s.get("tool_name") == "date_parser":
            date_source = f"$step_{s['step_id']}.date"
            date_depends.append(s["step_id"])
            break

    # 构建 weather 步骤
    weather_input = {"adcode": adcode_source}
    if date_source:
        weather_input["date"] = date_source

    depends_on = list(set(adcode_depends + date_depends))
    max_step_id = max((s.get("step_id", 0) for s in plan_steps), default=0)
    weather_step = {
        "step_id": max_step_id + 1,
        "action": "call_tool",
        "tool_name": "weather",
        "tool_input": weather_input,
        "reason": "确定性补充：出行场景必须查询天气，结合路线给出建议",
        "depends_on": depends_on,
        "on_failure": "skip",
    }

    # 在 answer 步骤前插入
    answer_index = next(
        (i for i, s in enumerate(plan_steps) if s.get("action") == "answer"),
        len(plan_steps),
    )
    plan_steps.insert(answer_index, weather_step)

    logger.info(
        f"[planner] 确定性补充 weather 步骤 | "
        f"adcode={adcode_source} | date={date_source or '(今天)'} | "
        f"插入位置={answer_index}"
    )
    return plan_steps


def create_planner_node(llm: BaseChatModel):
    """
    创建 planner 节点函数（闭包注入 LLM）

    参数：
        llm: LangChain BaseChatModel 实例

    返回值：
        async callable(state: AgentState) -> dict
    """

    async def planner_node(state: AgentState) -> dict:
        """
        制定执行计划

        参数：
            state: 当前 AgentState

        返回值：
            要更新的 State 字段（部分）
        """
        logger.info("=" * 60)
        logger.info("[Planner] 开始制定执行计划")
        logger.info(f"[Planner] 意图理解结果:\n{state['understanding'][:500]}")
        logger.info(f"[Planner] 用户输入: {state['user_message'][:200]}")
        logger.info(f"[Planner] 可用工具: {[t.name for t in tool_registry.get_all()]}")
        logger.info("=" * 60)

        # 构建 Prompt
        tools_info = _build_tools_info()
        system_prompt = PLANNER_SYSTEM_PROMPT.format(tools_info=tools_info)
        human_prompt = PLANNER_HUMAN_TEMPLATE.format(
            understanding=state["understanding"],
            user_message=state["user_message"],
        )

        plan_steps = []
        plan_summary = ""

        try:
            # 调用 LLM 生成计划
            response = await llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt),
            ])

            raw_output = response.content.strip()
            logger.debug(f"[Planner] LLM 原始输出 ({len(raw_output)} 字符):\n{raw_output[:1000]}")

            # 提取 JSON
            json_text = _extract_json(raw_output)
            plan_steps = json.loads(json_text)

            if not isinstance(plan_steps, list) or len(plan_steps) == 0:
                raise ValueError("LLM 返回的计划为空或格式不正确")

            plan_steps = _normalize_weather_plan(plan_steps, state["user_message"])
            plan_steps = _normalize_route_weather(plan_steps, state["user_message"])

            # 生成人类可读摘要
            summary_parts = []
            for step in plan_steps:
                action = step.get("action", "?")
                if action == "call_tool":
                    tool_name = step.get("tool_name", "?")
                    reason = step.get("reason", "")
                    summary_parts.append(f"步骤{step['step_id']}: 调用 {tool_name}（{reason}）")
                elif action == "answer":
                    summary_parts.append(f"步骤{step['step_id']}: 生成回答")
            plan_summary = "\n".join(summary_parts)

            logger.info(
                f"[Planner] 计划生成成功 | "
                f"共 {len(plan_steps)} 个步骤 | "
                f"工具序列: {[s.get('tool_name') for s in plan_steps if s.get('action') == 'call_tool']}"
            )
            for i, step in enumerate(plan_steps):
                logger.debug(
                    f"[Planner] Step {i+1}: action={step.get('action')}, "
                    f"tool={step.get('tool_name', '-')}, "
                    f"input={step.get('tool_input', {})}, "
                    f"depends_on={step.get('depends_on', [])}"
                )

        except (json.JSONDecodeError, ValueError, KeyError) as exc:
            # 计划生成失败 → 降级为直接回答
            logger.warning(f"[planner] 计划生成失败，降级为直接回答: {exc}")
            plan_steps = [
                {
                    "step_id": 1,
                    "action": "answer",
                    "tool_name": "",
                    "tool_input": {},
                    "reason": "计划生成失败，直接使用已有知识回答",
                    "depends_on": [],
                    "on_failure": "abort",
                }
            ]
            plan_summary = "计划生成失败，直接回答"

        # 追加前端展示步骤
        step = {
            "id": "step-plan",
            "name": "制定执行计划",
            "status": "completed",
            "type": "plan",
        }

        return {
            "plan_summary": plan_summary,
            "plan_steps": plan_steps,
            "current_step_index": 0,
            "next_action": "continue",
            "steps": [step],
        }

    return planner_node
