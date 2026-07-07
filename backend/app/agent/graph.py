"""
=============================================================================
Graph 构建器 — LangGraph StateGraph 组装
=============================================================================
职责：
  1. 创建 LangGraph StateGraph 实例
  2. 注册所有节点（understand / planner / executor / observer / answer）
  3. 配置条件边（tool_router）
  4. 编译并返回可调用的 graph 对象

Graph 流程：
  START
    │
    ▼
  [understand]  ──→  意图理解（LLM × 1）
    │
    ▼
  [planner]     ──→  制定计划（LLM × 1）
    │
    ▼
  [tool_router] ──→  条件边（纯逻辑，不计 LLM）
    │
    ├─ "executor" → [executor] → [observer] → tool_router（循环）
    ├─ "planner"  → [planner]（重新规划）
    └─ "answer"   → [answer]（LLM × 1）
                      │
                      ▼
                     END

LLM 调用次数：
  - 有工具调用: 3 次（understand + planner + answer）
  - 无工具调用: 3 次（understand + planner + answer，planner 输出直接 answer）
  - 重新规划: +1 次 planner

设计原则：
  - Graph 构建与 LLM 创建分离：graph 接收已配置好的节点函数
  - 节点函数通过闭包注入 LLM 实例
  - 单一入口 create_graph() → 返回 compiled graph
=============================================================================
"""

from langgraph.graph import StateGraph, END

from app.agent.state import AgentState
from app.agent.nodes.understand import create_understand_node
from app.agent.nodes.planner import create_planner_node
from app.agent.nodes.tool_executor import executor_node
from app.agent.nodes.observer import observer_node
from app.agent.nodes.answer import create_answer_node
from app.agent.router import tool_router
from app.utils.logger import logger


def create_graph(llm) -> StateGraph:
    """
    创建并编译 LangGraph StateGraph

    参数：
        llm: LangChain BaseChatModel 实例（已配置好 Provider 和参数）

    返回值：
        已编译的 StateGraph 实例（可调用 .ainvoke(state)）

    用法：
        from app.agent.graph import create_graph
        from app.agent.agent import create_llm

        llm = create_llm()
        graph = create_graph(llm)
        result = await graph.ainvoke(initial_state)
    """
    # =====================================================================
    # Step 1: 基于 AgentState 创建 StateGraph
    # =====================================================================
    workflow = StateGraph(AgentState)

    # =====================================================================
    # Step 2: 注册节点
    # =====================================================================
    # understand 和 planner 和 answer 需要 LLM，通过闭包注入
    understand = create_understand_node(llm)
    planner = create_planner_node(llm)
    answer = create_answer_node(llm)

    # 注册到 StateGraph
    workflow.add_node("understand", understand)
    workflow.add_node("planner", planner)
    workflow.add_node("executor", executor_node)
    workflow.add_node("observer", observer_node)
    workflow.add_node("answer", answer)

    logger.info("Graph 节点注册完成: understand, planner, executor, observer, answer")

    # =====================================================================
    # Step 3: 配置边（流程控制）
    # =====================================================================

    # 入口 → understand
    workflow.set_entry_point("understand")

    # understand → planner
    workflow.add_edge("understand", "planner")

    # planner → tool_router（条件边）
    # tool_router 根据 State 决定去 executor 还是 answer
    workflow.add_conditional_edges(
        "planner",
        tool_router,
        {
            "executor": "executor",
            "planner": "planner",   # replan 场景
            "answer": "answer",
        },
    )

    # executor → observer
    workflow.add_edge("executor", "observer")

    # observer → tool_router（条件边，循环或结束）
    workflow.add_conditional_edges(
        "observer",
        tool_router,
        {
            "executor": "executor",
            "planner": "planner",
            "answer": "answer",
        },
    )

    # answer → END
    workflow.add_edge("answer", END)

    # =====================================================================
    # Step 4: 编译
    # =====================================================================
    compiled = workflow.compile()
    logger.info("Graph 编译完成")

    return compiled
