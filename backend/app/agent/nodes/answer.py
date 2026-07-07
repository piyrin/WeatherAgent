"""
=============================================================================
Answer Node — 生成最终回答
=============================================================================
职责：
  1. 聚合所有上下文信息（理解、计划、工具结果、观察结论）
  2. 调用 LLM 生成结构化最终回答
  3. 写入 state.final_answer

输入（State 读取）：
  - user_message: 用户原始输入
  - understanding: 意图理解结果
  - plan_summary: 计划摘要
  - tool_calls: 所有工具调用记录
  - observations: 所有观察结论
  - start_time: 执行开始时间（用于计算总耗时）

输出（State 写入）：
  - final_answer: 最终回答文本
  - steps: 追加一条 "answer" 步骤

设计说明：
  - 最后一次 LLM 调用，聚合所有信息
  - 回答必须基于实测数据，而非 LLM 编造
  - 格式化工具结果为易读文本
=============================================================================
"""

import time

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.language_models import BaseChatModel

from app.agent.state import AgentState
from app.agent.prompts.answer_prompt import (
    ANSWER_SYSTEM_PROMPT,
    ANSWER_HUMAN_TEMPLATE,
)
from app.utils.logger import logger


def _format_tool_results(tool_calls: list[dict]) -> str:
    """
    将工具调用记录格式化为 LLM 可读的文本

    参数：
        tool_calls: 工具调用记录列表

    返回值：
        格式化的文本
    """
    if not tool_calls:
        return "（未调用任何工具）"

    lines = []
    for tc in tool_calls:
        status_icon = "✅" if tc.get("status") == "success" else "❌"
        lines.append(
            f"- {status_icon} **{tc['tool_name']}**: {tc.get('summary', '无输出')}"
        )
        if tc.get("error"):
            lines.append(f"  错误: {tc['error']}")
    return "\n".join(lines)


def _format_observations(observations: list[dict]) -> str:
    """
    将观察结论格式化为 LLM 可读的文本

    参数：
        observations: 观察结论列表

    返回值：
        格式化的文本
    """
    if not observations:
        return "（无观察结论）"

    lines = []
    for obs in observations:
        lines.append(f"- {obs.get('observation', '')}")
        facts = obs.get("extracted_facts", {})
        if facts:
            lines.append(f"  关键事实: {facts}")
    return "\n".join(lines)


def create_answer_node(llm: BaseChatModel):
    """
    创建 answer 节点函数（闭包注入 LLM）

    参数：
        llm: LangChain BaseChatModel 实例

    返回值：
        async callable(state: AgentState) -> dict
    """

    async def answer_node(state: AgentState) -> dict:
        """
        生成最终回答

        参数：
            state: 当前 AgentState

        返回值：
            要更新的 State 字段（部分）
        """
        logger.info("=" * 60)
        logger.info("[Answer] 开始生成最终回答")
        logger.info(f"[Answer] 工具调用数: {len(state.get('tool_calls', []))}")
        logger.info(f"[Answer] 工具结果:\n{_format_tool_results(state.get('tool_calls', []))}")
        logger.info("=" * 60)

        # 格式化工具结果和观察结论
        tool_results = _format_tool_results(state.get("tool_calls", []))
        observations = _format_observations(state.get("observations", []))

        # 计算总耗时
        total_duration_ms = 0.0
        if state.get("start_time"):
            total_duration_ms = round(
                (time.perf_counter() - state["start_time"]) * 1000, 2
            )

        # 构建 Prompt
        human_prompt = ANSWER_HUMAN_TEMPLATE.format(
            user_message=state["user_message"],
            understanding=state.get("understanding", "（无）"),
            plan_summary=state.get("plan_summary", "（无）"),
            tool_results=tool_results,
            observations=observations,
        )

        final_answer = ""

        try:
            # 调用 LLM 生成回答
            response = await llm.ainvoke([
                SystemMessage(content=ANSWER_SYSTEM_PROMPT),
                HumanMessage(content=human_prompt),
            ])

            final_answer = response.content.strip()

        except Exception as exc:
            # LLM 调用失败时，用工具结果拼接一个基础回答
            logger.error(f"[answer] LLM 调用失败: {exc}")
            parts = [f"根据查询结果：\n\n{tool_results}"]
            if observations:
                parts.append(f"\n分析：\n{observations}")
            final_answer = "\n\n".join(parts)

        logger.info(
            f"[Answer] 回答生成完成 | 长度={len(final_answer)}字符 | "
            f"总耗时={total_duration_ms:.0f}ms"
        )
        logger.debug(f"[Answer] 最终回答内容:\n{final_answer[:500]}")

        # 追加前端展示步骤
        step = {
            "id": "step-answer",
            "name": "生成最终回答",
            "status": "completed",
            "type": "answer",
            "totalDurationMs": total_duration_ms,
        }

        return {
            "final_answer": final_answer,
            "steps": [step],
        }

    return answer_node
