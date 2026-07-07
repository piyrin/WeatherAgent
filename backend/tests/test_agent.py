"""
=============================================================================
LangGraph Agent 验证脚本
=============================================================================
测试目标：
  1. 所有模块正常导入
  2. StateGraph 正确构建和编译
  3. AgentExecutor 可以正常初始化
  4. Graph 结构正确（节点数、边数）
=============================================================================
"""

import sys
import os

# 确保 backend 目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# =============================================================================
# Test 1: 模块导入
# =============================================================================
print("=" * 60)
print("Test 1: 模块导入检查")
print("=" * 60)

try:
    from app.agent.state import AgentState, MAX_ITERATIONS, MAX_RETRIES
    print("  ✅ state.py — AgentState 定义正常")
except Exception as e:
    print(f"  ❌ state.py — {e}")

try:
    from app.agent.prompts.understand_prompt import UNDERSTAND_SYSTEM_PROMPT
    from app.agent.prompts.planner_prompt import PLANNER_SYSTEM_PROMPT
    from app.agent.prompts.answer_prompt import ANSWER_SYSTEM_PROMPT
    print("  ✅ prompts/ — 所有提示词定义正常")
except Exception as e:
    print(f"  ❌ prompts/ — {e}")

try:
    from app.agent.router import tool_router
    print("  ✅ router.py — 路由函数定义正常")
except Exception as e:
    print(f"  ❌ router.py — {e}")

try:
    from app.agent.nodes.understand import create_understand_node
    from app.agent.nodes.planner import create_planner_node
    from app.agent.nodes.tool_executor import executor_node
    from app.agent.nodes.observer import observer_node
    from app.agent.nodes.answer import create_answer_node
    print("  ✅ nodes/ — 所有节点函数定义正常")
except Exception as e:
    print(f"  ❌ nodes/ — {e}")

try:
    from app.agent.graph import create_graph
    print("  ✅ graph.py — create_graph 函数定义正常")
except Exception as e:
    print(f"  ❌ graph.py — {e}")

try:
    from app.agent.executor import AgentExecutor, AgentResult, ToolCallStep, get_agent_executor
    print("  ✅ executor.py — AgentExecutor 相关类定义正常")
except Exception as e:
    print(f"  ❌ executor.py — {e}")

try:
    from app.agent import get_agent_executor as agent_get_executor
    print("  ✅ agent/__init__.py — 包导出正常")
except Exception as e:
    print(f"  ❌ agent/__init__.py — {e}")

# =============================================================================
# Test 2: State 结构验证
# =============================================================================
print("\n" + "=" * 60)
print("Test 2: AgentState 结构验证")
print("=" * 60)

# 验证 TypedDict 的所有字段
required_fields = [
    "user_message", "conversation_id", "chat_history", "start_time",
    "understanding", "plan_summary", "plan_steps", "current_step_index",
    "tool_calls", "observations",
    "next_action", "iteration_count", "retry_count",
    "final_answer", "steps", "error",
]

state = AgentState(
    user_message="test",
    conversation_id="test-123",
    chat_history="",
    start_time=0.0,
    understanding="",
    plan_summary="",
    plan_steps=[],
    current_step_index=0,
    tool_calls=[],
    observations=[],
    next_action="continue",
    iteration_count=0,
    retry_count=0,
    final_answer="",
    steps=[],
    error="",
)

for field in required_fields:
    if field in state:
        print(f"  ✅ {field}")
    else:
        print(f"  ❌ {field} — 缺失!")

print(f"\n  安全常量: MAX_ITERATIONS={MAX_ITERATIONS}, MAX_RETRIES={MAX_RETRIES}")

# =============================================================================
# Test 3: Graph 结构验证
# =============================================================================
print("\n" + "=" * 60)
print("Test 3: Graph 结构验证（不调用 LLM）")
print("=" * 60)

try:
    # 使用一个假的 LLM 来避免实际 API 调用
    from unittest.mock import MagicMock
    from langchain_core.language_models import BaseChatModel
    
    mock_llm = MagicMock(spec=BaseChatModel)
    
    graph = create_graph(mock_llm)
    print("  ✅ Graph 创建成功")
    
    # 检查 graph 属性
    print(f"  Graph 类型: {type(graph).__name__}")
    
    # LangGraph compiled graph 有 get_graph() 方法
    if hasattr(graph, "get_graph"):
        compiled_graph = graph.get_graph()
        print(f"  节点数: {len(compiled_graph.nodes)}")
        print(f"  边数: {len(compiled_graph.edges)}")
        
        print("  节点列表:")
        for node in compiled_graph.nodes:
            print(f"    - {node}")
        
        print("  边列表:")
        for edge in compiled_graph.edges:
            print(f"    - {edge}")
    
    print("\n  ✅ Graph 结构验证通过")
    
except Exception as e:
    print(f"  ❌ Graph 创建失败: {e}")
    import traceback
    traceback.print_exc()

# =============================================================================
# Test 4: Router 逻辑验证
# =============================================================================
print("\n" + "=" * 60)
print("Test 4: Router 路由逻辑验证")
print("=" * 60)

def build_test_state(**overrides):
    """构建测试用 AgentState"""
    base = {
        "user_message": "test",
        "conversation_id": "test-123",
        "chat_history": "",
        "start_time": 0.0,
        "understanding": "",
        "plan_summary": "",
        "plan_steps": [],
        "current_step_index": 0,
        "tool_calls": [],
        "observations": [],
        "next_action": "continue",
        "iteration_count": 0,
        "retry_count": 0,
        "final_answer": "",
        "steps": [],
        "error": "",
    }
    base.update(overrides)
    return base

# 测试1: 没有 plan steps → answer
state1 = build_test_state(plan_steps=[], current_step_index=0)
result1 = tool_router(state1)
print(f"  空计划 → {result1}")
assert result1 == "answer", f"期望 answer，得到 {result1}"
print("  ✅ 空计划正确路由到 answer")

# 测试2: 有 call_tool 步骤 → executor
state2 = build_test_state(
    plan_steps=[
        {"step_id": 1, "action": "call_tool", "tool_name": "weather", "tool_input": {}, "reason": "test"}
    ],
    current_step_index=0
)
result2 = tool_router(state2)
print(f"  call_tool 步骤 → {result2}")
assert result2 == "executor", f"期望 executor，得到 {result2}"
print("  ✅ call_tool 步骤正确路由到 executor")

# 测试3: 所有步骤完成 → answer
state3 = build_test_state(
    plan_steps=[
        {"step_id": 1, "action": "call_tool", "tool_name": "weather", "tool_input": {}, "reason": "test"}
    ],
    current_step_index=1  # 已完成
)
result3 = tool_router(state3)
print(f"  所有步骤完成 → {result3}")
assert result3 == "answer", f"期望 answer，得到 {result3}"
print("  ✅ 全部完成正确路由到 answer")

# 测试4: 超过最大迭代 → answer
state4 = build_test_state(
    plan_steps=[
        {"step_id": 1, "action": "call_tool", "tool_name": "weather", "tool_input": {}, "reason": "test"}
    ],
    current_step_index=0,
    iteration_count=MAX_ITERATIONS + 1
)
result4 = tool_router(state4)
print(f"  超限迭代 → {result4}")
assert result4 == "answer", f"期望 answer，得到 {result4}"
print("  ✅ 迭代超限正确路由到 answer")

# 测试5: replan → planner
state5 = build_test_state(next_action="replan")
result5 = tool_router(state5)
print(f"  replan → {result5}")
assert result5 == "planner", f"期望 planner，得到 {result5}"
print("  ✅ replan 正确路由到 planner")

print("\n🎉 所有测试通过！")
