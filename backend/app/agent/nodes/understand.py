"""
=============================================================================
Understand Node — 意图理解
=============================================================================
职责：
  1. 调用 LLM 分析用户输入，提取意图类别和关键实体
  2. 将理解结果写入 state.understanding
  3. 追加前端展示步骤到 state.steps

输入（State 读取）：
  - user_message: 用户输入文本
  - chat_history: 对话历史文本

输出（State 写入）：
  - understanding: 意图理解结果
  - steps: 追加一条 "understand" 步骤

设计说明：
  - 这是 Graph 的第一个节点，轻量级 LLM 调用
  - 输出为结构化文本（非 JSON），供 planner 和 answer 使用
  - 错误兜底：LLM 调用失败时使用降级理解结果
=============================================================================
"""

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.language_models import BaseChatModel

from app.agent.state import AgentState
from app.agent.prompts.understand_prompt import (
    UNDERSTAND_SYSTEM_PROMPT,
    UNDERSTAND_HUMAN_TEMPLATE,
)
from app.utils.logger import logger


def create_understand_node(llm: BaseChatModel):
    """
    创建 understand 节点函数（闭包注入 LLM）

    参数：
        llm: LangChain BaseChatModel 实例

    返回值：
        async callable(state: AgentState) -> dict
    """

    async def understand_node(state: AgentState) -> dict:
        """
        执行意图理解

        参数：
            state: 当前 AgentState

        返回值：
            要更新的 State 字段（部分）
        """
        logger.info("[understand] 开始分析用户意图")

        # 构建 Prompt
        human_prompt = UNDERSTAND_HUMAN_TEMPLATE.format(
            user_message=state["user_message"],
            chat_history=state.get("chat_history", "（无历史对话）"),
        )

        try:
            # 调用 LLM
            response = await llm.ainvoke([
                SystemMessage(content=UNDERSTAND_SYSTEM_PROMPT),
                HumanMessage(content=human_prompt),
            ])

            understanding = response.content.strip()

        except Exception as exc:
            # LLM 调用失败时的降级策略
            logger.warning(f"[understand] LLM 调用失败，使用降级理解: {exc}")
            understanding = (
                f"意图类别: general_chat\n"
                f"推理: LLM 调用失败，降级为通用理解。"
            )

        logger.info(f"[understand] 意图分析完成\n{understanding}")

        # 追加前端展示步骤
        step = {
            "id": "step-understand",
            "name": "理解用户意图",
            "status": "completed",
            "type": "understand",
        }

        return {
            "understanding": understanding,
            "steps": [step],
        }

    return understand_node
