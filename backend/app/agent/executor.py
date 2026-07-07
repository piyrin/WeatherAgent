"""
=============================================================================
Agent 执行器 — 基于 LangGraph 的状态机架构
=============================================================================
职责：
  1. 构建 LangGraph StateGraph（understand → plan → tool_router → call_tool → observe → answer）
  2. 执行 Agent 工作流并收集执行过程
  3. 将执行结果封装为结构化的 AgentResult
  4. 提供执行过程的可视化数据

规范依据：agent_interface_spec.md 第2、4、7、8节

节点流程：
  ENTRY → [understand] → [plan] → [tool_router]
                                    ├──→ [call_tool] → [observe] → back to router
                                    └──→ [answer] → EXIT
=============================================================================
"""

import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from langgraph.graph import StateGraph, END
from langchain_core.messages import AIMessage, HumanMessage

from app.agent.state import AgentState, create_initial_state, MAX_ITERATIONS, MAX_REVISIONS
from app.agent.tool_registry import tool_registry
from app.utils.logger import logger


# =============================================================================
# 执行结果数据结构
# =============================================================================


@dataclass
class ToolCallRecord:
    step_number: int
    tool_name: str
    tool_input: Dict[str, Any]
    tool_output: Dict[str, Any]
    status: str = "success"
    duration_ms: float = 0.0


@dataclass
class AgentResult:
    success: bool = True
    answer: str = ""
    plan: Dict[str, Any] = field(default_factory=dict)
    steps: List[Dict[str, Any]] = field(default_factory=list)
    tools: List[Dict[str, Any]] = field(default_factory=list)
    error_message: str = ""
    total_duration_ms: float = 0.0


# =============================================================================
# LangGraph 节点实现
# =============================================================================


def _node_understand(state: AgentState) -> Dict[str, Any]:
    """理解用户意图"""
    user_msg = state["user_message"]
    understanding = f"用户意图：{user_msg}"

    step_id = f"step-{len(state['steps']) + 1}"
    state["steps"].append({
        "id": step_id,
        "name": "理解用户意图",
        "status": "completed",
        "type": "understand",
        "retryCount": 0,
    })

    logger.info(f"[understand] {understanding}")
    return {
        "understanding": understanding,
        "next_action": "plan",
        "steps": state["steps"],
    }


def _node_plan(state: AgentState) -> Dict[str, Any]:
    """制定执行计划"""
    from app.agent.agent import generate_plan

    plan = generate_plan(state)

    step_id = f"step-{len(state['steps']) + 1}"
    state["steps"].append({
        "id": step_id,
        "name": "制定执行计划",
        "status": "completed",
        "type": "plan",
        "retryCount": 0,
    })

    logger.info(f"[plan] 总步骤: {plan['total_steps']} | 预计工具: {plan['estimated_tools']}")
    return {
        "plan": plan,
        "next_action": "call_tool",
        "steps": state["steps"],
    }


async def _node_call_tool(state: AgentState) -> Dict[str, Any]:
    """调用工具"""
    plan = state["plan"]
    if not plan:
        return {"next_action": "answer"}

    plan_steps = plan["plan"]
    tool_calls = state["tool_calls"]
    completed_step_ids = [tc["step_id"] for tc in tool_calls]

    for step in plan_steps:
        if step["action"] == "call_tool" and step["step_id"] not in completed_step_ids:
            depends_ok = all(d in completed_step_ids for d in step["depends_on"])
            if not depends_ok:
                continue

            tool_name = step["tool_name"]
            tool_input = step["tool_input"]

            tool_input_resolved = _resolve_input_references(tool_input, tool_calls)

            step_id = f"step-{len(state['steps']) + 1}"
            state["steps"].append({
                "id": step_id,
                "name": f"调用 {tool_name} 工具",
                "status": "running",
                "type": "tool_call",
                "toolName": tool_name,
                "toolInput": tool_input_resolved,
                "retryCount": 0,
            })

            logger.info(f"[call_tool] {tool_name} | input={tool_input_resolved}")

            start_time = time.perf_counter()
            tool = tool_registry.get_tool(tool_name)
            tool_output = {}

            if tool:
                result = await tool.run(**tool_input_resolved)
                tool_output = {
                    "success": result.get("success", False),
                    "result": result.get("result", {}),
                    "summary": result.get("summary", ""),
                    "error": result.get("error"),
                    "duration_ms": result.get("duration_ms", 0),
                }
            else:
                tool_output = {
                    "success": False,
                    "result": None,
                    "summary": f"工具 {tool_name} 未找到",
                    "error": f"TOOL_NOT_FOUND: 工具 {tool_name} 未注册",
                    "duration_ms": 0,
                }

            duration_ms = (time.perf_counter() - start_time) * 1000

            tool_call_record = {
                "step_id": step["step_id"],
                "tool_name": tool_name,
                "tool_input": tool_input_resolved,
                "tool_output": tool_output,
                "status": "success" if tool_output["success"] else "error",
                "retry_count": 0,
                "duration_ms": duration_ms,
            }
            state["tool_calls"].append(tool_call_record)

            for s in state["steps"]:
                if s["id"] == step_id:
                    s["status"] = "completed" if tool_output["success"] else "failed"
                    s["toolOutput"] = tool_output.get("result") or tool_output.get("summary")
                    s["error"] = tool_output.get("error")
                    break

            logger.info(f"[call_tool] {tool_name} 完成 | duration={duration_ms:.1f}ms | success={tool_output['success']}")
            return {
                "tool_calls": state["tool_calls"],
                "next_action": "observe",
                "steps": state["steps"],
            }

    return {"next_action": "answer"}


def _resolve_input_references(tool_input: Dict[str, Any], tool_calls: List[Dict[str, Any]]) -> Dict[str, Any]:
    """解析工具输入中的引用（如 $step_1.parsed_date）"""
    resolved = {}
    for key, value in tool_input.items():
        if isinstance(value, str) and value.startswith("$step_"):
            parts = value[1:].split(".")
            step_ref = parts[0]
            field_name = parts[1] if len(parts) > 1 else None
            step_num = int(step_ref.split("_")[1])
            for tc in tool_calls:
                if tc["step_id"] == step_num:
                    result = tc["tool_output"].get("result", {})
                    resolved[key] = result.get(field_name) if field_name else result
                    break
        else:
            resolved[key] = value
    return resolved


def _node_observe(state: AgentState) -> Dict[str, Any]:
    """观察工具调用结果"""
    tool_calls = state["tool_calls"]
    if not tool_calls:
        return {"next_action": "answer"}

    last_tool_call = tool_calls[-1]
    tool_output = last_tool_call["tool_output"]
    tool_name = last_tool_call["tool_name"]

    observation_text = tool_output.get("summary", "")
    need_replan = False
    confidence = 0.9

    if not tool_output.get("success"):
        need_replan = True
        confidence = 0.1

    observation = {
        "step_id": last_tool_call["step_id"],
        "tool_name": tool_name,
        "observation": observation_text,
        "extracted_facts": tool_output.get("result", {}),
        "need_replan": need_replan,
        "replan_reason": "工具调用失败" if not tool_output.get("success") else None,
        "confidence": confidence,
    }
    state["observations"].append(observation)

    step_id = f"step-{len(state['steps']) + 1}"
    state["steps"].append({
        "id": step_id,
        "name": "分析工具返回结果",
        "status": "completed",
        "type": "observe",
        "retryCount": 0,
    })

    logger.info(f"[observe] need_replan={need_replan} | confidence={confidence}")

    next_action = "replan" if need_replan else "call_tool"
    return {
        "observations": state["observations"],
        "next_action": next_action,
        "steps": state["steps"],
    }


def _node_replan(state: AgentState) -> Dict[str, Any]:
    """重新规划"""
    plan_revision = state["plan_revision"] + 1
    if plan_revision > MAX_REVISIONS:
        logger.warning(f"[replan] 超过最大重规划次数 {MAX_REVISIONS}")
        return {"next_action": "answer", "plan_revision": plan_revision}

    from app.agent.agent import generate_plan

    plan = generate_plan(state)

    step_id = f"step-{len(state['steps']) + 1}"
    state["steps"].append({
        "id": step_id,
        "name": f"重新规划（第 {plan_revision} 次）",
        "status": "completed",
        "type": "plan",
        "retryCount": 0,
    })

    logger.info(f"[replan] 第 {plan_revision} 次重规划 | 总步骤: {plan['total_steps']}")
    return {
        "plan": plan,
        "plan_revision": plan_revision,
        "next_action": "call_tool",
        "steps": state["steps"],
    }


def _node_answer(state: AgentState) -> Dict[str, Any]:
    """生成最终回答"""
    from app.agent.agent import generate_answer

    answer = generate_answer(state)

    step_id = f"step-{len(state['steps']) + 1}"
    state["steps"].append({
        "id": step_id,
        "name": "生成最终回答",
        "status": "completed",
        "type": "answer",
        "retryCount": 0,
    })

    logger.info(f"[answer] 回答长度: {len(answer)}字符")
    return {
        "final_answer": answer,
        "next_action": "end",
        "should_continue": False,
        "steps": state["steps"],
    }


def _edge_tool_router(state: AgentState) -> str:
    """工具路由条件边"""
    next_action = state["next_action"]
    iteration_count = state["iteration_count"] + 1

    if iteration_count > MAX_ITERATIONS:
        logger.warning(f"[router] 超过最大迭代次数 {MAX_ITERATIONS}")
        return "answer"

    state["iteration_count"] = iteration_count

    if next_action == "plan":
        return "plan"
    elif next_action == "call_tool":
        plan = state["plan"]
        if plan:
            plan_steps = plan["plan"]
            tool_calls = state["tool_calls"]
            completed_step_ids = [tc["step_id"] for tc in tool_calls]
            for step in plan_steps:
                if step["action"] == "call_tool" and step["step_id"] not in completed_step_ids:
                    return "call_tool"
        return "answer"
    elif next_action == "observe":
        return "observe"
    elif next_action == "replan":
        return "replan"
    elif next_action == "answer":
        return "answer"
    elif next_action == "end":
        return "answer"

    return "answer"


# =============================================================================
# Agent 执行器（使用 LangGraph）
# =============================================================================


class AgentGraphExecutor:
    """
    基于 LangGraph 的 Agent 执行器

    用法：
        executor = AgentGraphExecutor()
        result = await executor.run(
            user_message="明天北京天气怎么样？",
            conversation_id="xxx",
            chat_history=[],
            current_time="2026-07-07T09:30:00+08:00",
        )
    """

    def __init__(self):
        self._graph = self._build_graph()
        logger.info("AgentGraphExecutor 初始化完成")

    def _build_graph(self) -> StateGraph:
        """构建 LangGraph 状态图"""
        workflow = StateGraph(AgentState)

        workflow.add_node("understand", _node_understand)
        workflow.add_node("plan", _node_plan)
        workflow.add_node("call_tool", _node_call_tool)
        workflow.add_node("observe", _node_observe)
        workflow.add_node("replan", _node_replan)
        workflow.add_node("answer", _node_answer)

        workflow.set_entry_point("understand")

        workflow.add_edge("understand", "plan")
        workflow.add_edge("plan", "call_tool")
        workflow.add_edge("call_tool", "observe")
        workflow.add_conditional_edges("observe", _edge_tool_router)
        workflow.add_edge("replan", "call_tool")
        workflow.add_edge("answer", END)

        return workflow.compile()

    async def run(
        self,
        user_message: str,
        conversation_id: str,
        chat_history: List[Any] = None,
        current_time: str = None,
    ) -> AgentResult:
        """
        执行 Agent 的完整工作流

        参数：
            user_message:   用户输入文本
            conversation_id:会话 ID
            chat_history:   历史对话消息列表
            current_time:   当前时间

        返回值：
            AgentResult，包含最终回答和执行过程
        """
        start_time = time.perf_counter()
        result = AgentResult()

        if current_time is None:
            current_time = datetime.now(timezone.utc).isoformat()

        logger.info(f"Agent 开始执行 | 用户输入=\"{user_message[:100]}\" | conversation_id={conversation_id}")

        try:
            initial_state = create_initial_state(
                user_message=user_message,
                conversation_id=conversation_id,
                chat_history=chat_history or [],
                current_time=current_time,
            )

            final_state = await self._graph.ainvoke(initial_state)

            result.answer = final_state.get("final_answer", "")
            result.plan = final_state.get("plan", {})
            result.steps = final_state.get("steps", [])
            result.tools = [
                {
                    "name": tc["tool_name"],
                    "input": tc["tool_input"],
                    "output": tc["tool_output"].get("result") or tc["tool_output"].get("summary"),
                    "status": "completed" if tc["status"] == "success" else "failed",
                    "duration_ms": tc["duration_ms"],
                }
                for tc in final_state.get("tool_calls", [])
            ]
            result.success = True

            if not result.answer:
                result.answer = "抱歉，我无法处理您的请求，请稍后重试。"

        except Exception as exc:
            result.success = False
            result.error_message = str(exc)
            result.answer = f"抱歉，Agent 执行过程中出现错误：{str(exc)}"
            logger.error(f"Agent 执行异常 | error={str(exc)}", exc_info=True)

        result.total_duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        logger.info(
            f"Agent 执行完成 | success={result.success} | "
            f"耗时={result.total_duration_ms}ms | "
            f"工具调用={len(result.tools)}次 | "
            f"回答长度={len(result.answer)}字符"
        )

        return result


# =============================================================================
# 全局单例
# =============================================================================

_global_executor: AgentGraphExecutor | None = None


def get_agent_executor() -> AgentGraphExecutor:
    """获取全局 Agent 执行器实例"""
    global _global_executor
    if _global_executor is None:
        _global_executor = AgentGraphExecutor()
    return _global_executor