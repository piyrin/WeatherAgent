"""
=============================================================================
Agent 执行器 — 编排 理解→计划→调用→观察→回答 全流程
=============================================================================
职责：
  1. 接收用户输入，调用 LangChain Agent 执行
  2. 提取 Agent 执行过程（工具调用、思考步骤）
  3. 将执行结果封装为结构化的 AgentResult
  4. 提供执行过程的可视化数据（给前端 Agent 过程面板使用）

Agent 执行全流程：
  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
  │ 理解任务 │ → │ 制定计划 │ → │ 调用工具 │ → │ 观察结果 │ → │ 生成回答 │
  └──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘

设计原则：
  - Agent 执行与 HTTP 框架完全解耦：executor 不依赖 FastAPI
  - 执行过程可观测：每一步都有日志记录和结构化输出
  - 错误隔离：Agent 异常不影响服务可用性
=============================================================================
"""

import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone

from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.messages import AIMessage, HumanMessage

from app.agent.agent import create_agent
from app.agent.tool_registry import tool_registry
from app.utils.logger import logger


# =============================================================================
# 执行结果数据结构
# =============================================================================


@dataclass
class ToolCallStep:
    """
    单次工具调用的记录（对应前端 Agent 过程面板中的一步）

    字段说明：
      - step_number: 步骤序号（从 1 开始）
      - tool_name:   工具名称
      - tool_input:  工具输入参数
      - tool_output: 工具输出文本
      - status:      执行状态（success / error）
      - duration_ms: 耗时（毫秒）
    """

    step_number: int
    tool_name: str
    tool_input: dict | None
    tool_output: str | None
    status: str = "success"
    duration_ms: float = 0.0


@dataclass
class AgentResult:
    """
    Agent 执行结果

    字段说明：
      - success:          是否执行成功
      - answer:           Agent 最终回答文本
      - plan:             执行计划（LLM 生成的思考链）
      - steps:            执行步骤描述列表
      - tool_calls:       工具调用记录列表
      - error_message:    错误信息（仅失败时有值）
      - total_duration_ms:总耗时（毫秒）
    """

    success: bool = True
    answer: str = ""
    plan: str = ""
    steps: list[str] = field(default_factory=list)
    tool_calls: list[ToolCallStep] = field(default_factory=list)
    error_message: str = ""
    total_duration_ms: float = 0.0


# =============================================================================
# Agent 执行器
# =============================================================================


class AgentExecutor:
    """
    Agent 执行器 — 管理 Agent 的生命周期

    用法：
        executor = AgentExecutor()
        result = await executor.run(
            user_input="明天北京天气怎么样？",
            chat_history=[],  # 可选：对话历史
        )
    """

    def __init__(self):
        # 获取所有 LangChain 工具
        self._tools = tool_registry.get_all_langchain_tools()
        # 创建 Agent 实例
        self._agent = create_agent(tools=self._tools)
        logger.info(f"AgentExecutor 初始化完成 | tools_count={len(self._tools)}")

    async def run(
        self,
        user_input: str,
        chat_history: list | None = None,
    ) -> AgentResult:
        """
        执行 Agent 的完整工作流

        参数：
            user_input:   用户输入文本
            chat_history: 历史对话消息列表（LangChain 消息格式，可选）

        返回值：
            AgentResult，包含最终回答和执行过程
        """
        start_time = time.perf_counter()
        result = AgentResult()

        logger.info(f"Agent 开始执行 | 用户输入=\"{user_input[:100]}\"")

        try:
            # ---- Step 1: 构建输入 ----
            # 构造 LangChain Agent 的输入格式
            agent_input = {
                "input": user_input,
                "chat_history": chat_history or [],
                "current_date": datetime.now(timezone.utc).strftime("%Y年%m月%d日"),
            }

            # ---- Step 2: 执行 Agent ----
            # invoke 方法是同步的，但内部 LLM 调用是异步的
            # LangChain 的 invoke 在同步上下文中也能正常工作
            raw_result = self._agent.invoke(agent_input)

            # ---- Step 3: 解析执行过程 ----
            self._parse_intermediate_steps(raw_result, result)

            # ---- Step 4: 提取最终回答 ----
            # LangChain ReAct Agent 的输出在 "output" 字段
            result.answer = raw_result.get("output", "")

            if not result.answer:
                result.answer = "抱歉，我无法处理您的请求，请稍后重试。"

            result.success = True

        except Exception as exc:
            # ---- 异常处理 ----
            result.success = False
            result.error_message = str(exc)
            result.answer = f"抱歉，Agent 执行过程中出现错误：{str(exc)}"

            logger.error(
                f"Agent 执行异常 | error={str(exc)}\n{traceback.format_exc()}"
            )

        # ---- 计算总耗时 ----
        result.total_duration_ms = round(
            (time.perf_counter() - start_time) * 1000, 2
        )

        logger.info(
            f"Agent 执行完成 | success={result.success} | "
            f"耗时={result.total_duration_ms}ms | "
            f"工具调用={len(result.tool_calls)}次 | "
            f"回答长度={len(result.answer)}字符"
        )

        return result

    def _parse_intermediate_steps(
        self,
        raw_result: dict,
        result: AgentResult,
    ) -> None:
        """
        解析 Agent 的中间执行步骤

        从 LangChain 的 intermediate_steps 中提取：
          - 计划/思考链
          - 工具调用记录
          - 执行步骤描述

        参数：
            raw_result: LangChain Agent 的原始输出
            result:     要填充的 AgentResult 对象
        """
        steps = raw_result.get("intermediate_steps", [])

        if not steps:
            result.plan = "无需工具调用，直接回答"
            result.steps = ["分析用户问题", "直接生成回答"]
            return

        plan_parts = []
        step_descriptions = []

        step_number = 0
        for step in steps:
            if len(step) < 2:
                continue

            action: AgentAction = step[0]
            observation = step[1]

            step_number += 1

            # 提取工具输入
            tool_input = action.tool_input if isinstance(action.tool_input, dict) else {"input": str(action.tool_input)}

            # 提取工具输出
            if isinstance(observation, str):
                tool_output = observation
            elif isinstance(observation, list):
                # 有时候 observation 是消息列表
                tool_output = str(observation[0]) if observation else ""
            else:
                tool_output = str(observation)

            # 记录工具调用
            result.tool_calls.append(ToolCallStep(
                step_number=step_number,
                tool_name=action.tool,
                tool_input=tool_input,
                tool_output=tool_output[:500] if tool_output else None,
                status="success",
            ))

            # 计划描述
            plan_parts.append(f"步骤{step_number}: 调用 {action.tool} 工具")
            step_descriptions.append(
                f"调用 {action.tool} 工具获取数据"
            )

        result.plan = " → ".join(plan_parts) + " → 综合分析并生成回答"
        result.steps = step_descriptions + ["分析工具返回数据", "生成最终回答"]


# =============================================================================
# 全局单例
# =============================================================================

# 全局唯一的 Agent 执行器实例
# 在模块加载时初始化，所有请求共享同一个执行器
# 注意：Agent 本身是无状态的（每次调用独立），所以线程安全
_global_executor: AgentExecutor | None = None


def get_agent_executor() -> AgentExecutor:
    """
    获取全局 Agent 执行器实例

    懒加载模式：首次调用时创建，后续直接返回。
    这样即使 Agent 初始化失败（如 API Key 未配置），
    也不会导致模块加载失败，而是在首次请求时才报错。

    返回值：
        AgentExecutor 实例
    """
    global _global_executor
    if _global_executor is None:
        _global_executor = AgentExecutor()
    return _global_executor
