"""
=============================================================================
Tool Router — LangGraph 条件边
=============================================================================
职责：
  根据当前 State 决定 Graph 的下一个节点。
  这是一个纯 Python 函数（条件边），不是 Node。

输入（State 读取）：
  - plan_steps: 结构化执行计划
  - current_step_index: 当前步骤索引
  - next_action: 控制信号（"continue" | "replan" | "answer"）
  - iteration_count: 循环计数器

返回值：
  "executor" — 还有工具步骤待执行
  "planner" — 需要重新规划
  "answer"  — 所有步骤完成或强制终止

路由逻辑：
  1. next_action == "replan"  → 返回 planner
  2. next_action == "answer"  → 返回 answer（强制终止）
  3. 当前步骤是 call_tool     → 返回 executor
  4. 没有更多步骤             → 返回 answer

安全机制：
  iteration_count > MAX_ITERATIONS → 强制返回 answer，防止死循环

设计原则：
  - 不含任何业务逻辑：不调 LLM，不调 Tool
  - 纯状态机：只读 State + 返回路由字符串
  - 新增 Tool 无需修改此文件
=============================================================================
"""

from app.agent.state import AgentState, MAX_ITERATIONS
from app.utils.logger import logger


def tool_router(state: AgentState) -> str:
    """
    Agent 流程路由决策

    这是 LangGraph 的 conditional_edge 函数，根据 State 返回下一个节点名称。

    参数：
        state: 当前 AgentState

    返回值：
        "executor" | "planner" | "answer"
    """
    iteration_count = state.get("iteration_count", 0)
    next_action = state.get("next_action", "continue")
    plan_steps = state.get("plan_steps", [])
    current_index = state.get("current_step_index", 0)

    logger.info(
        f"[Router] 路由决策 | iteration={iteration_count} | "
        f"next_action={next_action} | "
        f"step={current_index}/{len(plan_steps)} | "
        f"plan_tools={[s.get('tool_name','?') for s in plan_steps]}"
    )

    # ==== 安全边界：防止无限循环 ====
    if iteration_count > MAX_ITERATIONS:
        logger.warning(
            f"[router] 达到最大迭代次数 (iteration={iteration_count})，"
            f"强制进入 answer 节点"
        )
        return "answer"

    # ==== 控制信号优先 ====
    if next_action == "replan":
        logger.info("[router] next_action=replan → 返回 planner")
        return "planner"

    if next_action == "answer":
        logger.info("[router] next_action=answer → 返回 answer")
        return "answer"

    # ==== 检查是否还有待执行的步骤 ====
    if current_index >= len(plan_steps):
        logger.info(
            f"[router] 所有步骤已执行完毕 "
            f"(index={current_index}, total={len(plan_steps)}) → 返回 answer"
        )
        return "answer"

    # ==== 检查当前步骤的类型 ====
    current_step = plan_steps[current_index]

    if current_step.get("action") == "call_tool":
        tool_name = current_step.get("tool_name", "?")
        logger.info(
            f"[Router] 步骤 {current_step.get('step_id')}/{len(plan_steps)} "
            f"→ call_tool({tool_name}) → executor"
        )
        return "executor"

    # 未知 action 类型 → 安全兜底，跳过该步骤
    logger.warning(
        f"[router] 未知的步骤 action: {current_step.get('action')}，"
        f"跳过该步骤 → 返回 answer"
    )
    return "answer"
