"""
智能体层 — LangGraph Agent 核心

目录结构：
  state.py            AgentState TypedDict 定义
  agent.py            LLM 工厂（create_llm）
  graph.py            LangGraph StateGraph 构建
  executor.py         AgentExecutor（外部调用入口）
  router.py           条件边（tool_router）
  memory.py           对话记忆（预留）
  nodes/              各节点实现
  prompts/            Prompt 模板

对外接口：
  from app.agent import get_agent_executor
  executor = get_agent_executor()
  result = await executor.run(user_input="...", chat_history=[...])
"""

from app.agent.executor import (  # noqa: F401
    AgentExecutor,
    AgentResult,
    ToolCallStep,
    get_agent_executor,
)
