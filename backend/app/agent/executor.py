"""
=============================================================================
AgentExecutor — LangGraph Agent 的执行器（替换旧版）
=============================================================================
职责：
  1. 管理 LangGraph Agent 的生命周期
  2. 接收 ChatService 调用，初始化 AgentState，执行 Graph
  3. 将 Graph 执行结果转换为 AgentResult（与旧版保持兼容）

与旧版 AgentExecutor 的接口兼容：
  - 方法签名：async run(user_input, chat_history) -> AgentResult
  - chat_history 支持 str（ChatMemory 预格式化）或 list（旧版 LangChain 消息）
  - 相同的返回类型：AgentResult（success, answer, plan, steps, tool_calls, ...）
  - ChatService 传递字符串上下文，不再传递 LangChain 消息列表

内部实现变化：
  - 旧版：LangChain AgentExecutor.invoke()
  - 新版：LangGraph compiled_graph.ainvoke()

AgentResult 字段映射：
  - final_answer → AgentResult.answer
  - plan_summary  → AgentResult.plan
  - steps[]       → AgentResult.steps（字符串列表）
  - tool_calls[]  → AgentResult.tool_calls（ToolCallStep 列表）
  - error         → AgentResult.error_message
=============================================================================
"""

import time
import traceback
from dataclasses import dataclass, field
from typing import Any

from app.agent.graph import create_graph
from app.agent.state import AgentState
from app.utils.logger import logger


# =============================================================================
# 数据结构（与旧版完全兼容）
# =============================================================================


@dataclass
class ToolCallStep:
    """
    单次工具调用记录（保持与旧版字段一致）
    """
    step_number: int = 0
    tool_name: str = ""
    tool_input: dict | None = None
    tool_output: Any = None
    status: str = "success"
    duration_ms: float = 0.0


@dataclass
class AgentResult:
    """
    Agent 执行结果（保持与旧版字段一致）
    """
    success: bool = True
    answer: str = ""
    plan: str = ""
    steps: list[str] = field(default_factory=list)
    tool_calls: list[ToolCallStep] = field(default_factory=list)
    error_message: str = ""
    total_duration_ms: float = 0.0


# =============================================================================
# AgentExecutor
# =============================================================================


class AgentExecutor:
    """
    LangGraph Agent 执行器

    用法：
        executor = AgentExecutor()

        # 推荐方式：ChatMemory 预格式化的上下文字符串
        result = await executor.run(
            user_input="明天北京天气怎么样？",
            chat_history="[历史对话摘要]\n用户问了深圳天气...\n\n[最近对话]\n用户: 你好\n助手: 你好！",
        )

        # 兼容旧版：LangChain 消息列表
        result = await executor.run(
            user_input="明天北京天气怎么样？",
            chat_history=[HumanMessage(...), AIMessage(...)],
        )

    初始化：
        - 自动创建 LLM 和编译好的 Graph
        - 所有请求复用同一个 Graph 实例（Graph 本身无状态）
    """

    def __init__(self):
        # 延迟导入 create_llm，避免在模块加载时初始化
        from app.agent.agent import create_llm

        self._llm = create_llm()
        self._graph = create_graph(self._llm)
        logger.info("AgentExecutor (LangGraph) 初始化完成")

    async def run(
        self,
        user_input: str,
        chat_history: list | str | None = None,
    ) -> AgentResult:
        """
        执行 Agent 完整工作流

        参数：
            user_input:   用户输入文本
            chat_history: 对话上下文，支持两种类型：
                          - str:  ChatMemory 预格式化的上下文（摘要 + 最近对话）
                                 直接注入 AgentState.chat_history，无需再次处理
                          - list: LangChain HumanMessage/AIMessage 消息列表（兼容旧版调用）
                                  转换为纯文本后注入（只取最近 6 条）
                          - None: 无历史对话

        返回值：
            AgentResult：包含最终回答和执行过程
        """
        start_time = time.perf_counter()

        logger.info(f"[Agent] 开始执行 | 用户输入=\"{user_input[:100]}\"")

        # =================================================================
        # Step 1: 准备对话历史文本
        # =================================================================
        if isinstance(chat_history, str):
            # 新模式：ChatMemory 已格式化好上下文，直接使用
            chat_history_text = chat_history.strip() if chat_history else "（无历史对话）"
            logger.debug(
                f"[Agent] 使用预格式化上下文 | 长度={len(chat_history_text)}字符"
            )
        elif chat_history:
            # 兼容旧版：LangChain 消息列表 → 纯文本（只取最近 6 条）
            parts = []
            for msg in chat_history[-6:]:
                role = getattr(msg, "type", "unknown")
                content = getattr(msg, "content", "")
                if role == "human":
                    parts.append(f"用户: {content}")
                elif role == "ai":
                    parts.append(f"助手: {content}")
            chat_history_text = "\n".join(parts) if parts else "（无历史对话）"
        else:
            chat_history_text = "（无历史对话）"

        # =================================================================
        # Step 2: 初始化 AgentState
        # =================================================================
        initial_state: AgentState = {
            # 输入层
            "user_message": user_input,
            "conversation_id": "",
            "chat_history": chat_history_text,
            "start_time": start_time,
            # 推理层（待填充）
            "understanding": "",
            "plan_summary": "",
            "plan_steps": [],
            "current_step_index": 0,
            "city": "",
            "adcode": "",
            # 执行层（待追加）
            "tool_calls": [],
            "observations": [],
            # 控制层
            "next_action": "continue",
            "iteration_count": 0,
            "retry_count": 0,
            # 输出层（待填充）
            "final_answer": "",
            "steps": [],
            "error": "",
        }

        result = AgentResult()

        # =================================================================
        # Step 3: 执行 Graph
        # =================================================================
        try:
            final_state = await self._graph.ainvoke(initial_state)

            # =================================================================
            # Step 4: 转换为 AgentResult
            # =================================================================
            result.success = True
            result.answer = final_state.get("final_answer", "")
            result.plan = final_state.get("plan_summary", "")
            result.error_message = final_state.get("error", "")

            # 转换 steps（dict → 简化为字符串列表 + 完整对象）
            raw_steps = final_state.get("steps", [])
            result.steps = [
                s.get("name", f"步骤{i+1}")
                for i, s in enumerate(raw_steps)
            ]

            # 转换 tool_calls
            tool_call_step_number = 0
            for tc in final_state.get("tool_calls", []):
                tool_call_step_number += 1
                tool_output = tc.get("tool_output", "")

                result.tool_calls.append(ToolCallStep(
                    step_number=tool_call_step_number,
                    tool_name=tc.get("tool_name", ""),
                    tool_input=tc.get("tool_input"),
                    tool_output=tool_output,
                    status=tc.get("status", "success"),
                    duration_ms=tc.get("duration_ms", 0.0),
                ))

        except Exception as exc:
            result.success = False
            result.error_message = str(exc)
            result.answer = f"抱歉，Agent 执行过程中出现错误：{str(exc)}"

            logger.error(
                f"[Agent] 执行异常 | error={str(exc)}\n{traceback.format_exc()}"
            )

        # =================================================================
        # Step 5: 计算总耗时
        # =================================================================
        result.total_duration_ms = round(
            (time.perf_counter() - start_time) * 1000, 2
        )

        logger.info(
            f"[Agent] 执行完成 | success={result.success} | "
            f"耗时={result.total_duration_ms}ms | "
            f"工具调用={len(result.tool_calls)}次 | "
            f"回答长度={len(result.answer)}字符"
        )

        return result


# =============================================================================
# 全局单例
# =============================================================================

_global_executor: AgentExecutor | None = None


def get_agent_executor() -> AgentExecutor:
    """
    获取全局 Agent 执行器实例（懒加载）

    返回值：
        AgentExecutor 实例
    """
    global _global_executor
    if _global_executor is None:
        _global_executor = AgentExecutor()
    return _global_executor
