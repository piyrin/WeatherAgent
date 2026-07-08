"""
=============================================================================
AgentState — LangGraph StateGraph 的共享状态定义
=============================================================================
职责：
  1. 定义所有 Node 共享的 State 结构（TypedDict）
  2. 使用 Annotated + operator.add 实现列表追加语义
  3. 作为 StateGraph 初始化时的 schema 参数

State 分层设计：
  ┌─────────────┐
  │ 输入层      │ user_message / conversation_id / chat_history / start_time
  ├─────────────┤
  │ 推理层      │ understanding / plan_summary / plan_steps / current_step_index
  ├─────────────┤
  │ 执行层      │ tool_calls* / observations*   （* = 追加写入）
  ├─────────────┤
  │ 控制层      │ next_action / iteration_count / retry_count
  ├─────────────┤
  │ 输出层      │ final_answer / steps* / error
  └─────────────┘

LangGraph 约定：
  - 普通字段最后写入胜出（last-write-wins）
  - Annotated[list, operator.add] 字段每写一次都追加到已有列表末尾
  - node 函数签名：def node(state: AgentState) -> dict，返回要更新的部分

设计原则：
  - 与 FastAPI / ChatService 完全解耦，State 不包含任何 Web 框架依赖
  - PlanStep 使用 dict 而非 Pydantic Model，避免 LangGraph 序列化问题
=============================================================================
"""

import operator
from typing import Annotated, TypedDict


# =============================================================================
# PlanStep 结构（文档说明用，实际 State 中存 dict）
# =============================================================================
#
# plan_steps 中每个元素的字段约定：
# {
#     "step_id":    int,       # 步骤序号（从 1 开始）
#     "action":     str,       # "call_tool" | "observe" | "answer"
#     "tool_name":  str,       # 工具名称（action="call_tool" 时必填）
#     "tool_input": dict,      # 工具输入参数
#     "reason":     str,       # 为什么需要这一步
#     "depends_on": list[int], # 依赖的 step_id 列表
#     "on_failure": str,       # "retry_once" | "skip" | "abort"
#     "status":     str,       # "pending" | "running" | "completed" | "failed"
# }


# =============================================================================
# AgentState — 核心状态定义
# =============================================================================

class AgentState(TypedDict):
    """
    LangGraph 共享状态

    写策略说明：
      - 直接赋值字段：后面写入会覆盖前面的值
      - Annotated[list, add] 字段：每次写入追加到列表末尾

    使用示例：
        state: AgentState = {
            "user_message": "明天去武汉需要带伞吗",
            "conversation_id": "xxx",
            ...
        }
        graph.invoke(state)
    """

    # =====================================================================
    # 输入层 — 初始化后不再修改
    # =====================================================================

    user_message: str
    """
    用户原始输入文本
    写入者：AgentExecutor（初始化时设置）
    读取者：understand、planner、answer
    写入次数：1 次（初始化时）
    """

    conversation_id: str
    """
    会话唯一标识（UUID）
    写入者：AgentExecutor（初始化时设置）
    读取者：日志、错误追踪
    写入次数：1 次
    """

    client_ip: str
    """
    客户端 IP 地址（从 HTTP 请求中提取）
    写入者：AgentExecutor（从 ChatService 传入）
    读取者：executor_node（注入 ip_location 工具调用）
    用途：ip_location 工具定位用户当前位置
    示例："114.247.50.2"、"192.168.1.1"（局域网）
    """

    chat_history: str
    """
    对话历史的文本摘要（非 LangChain 消息对象）
    写入者：AgentExecutor（从 ChatService 传入，已序列化为文本）
    读取者：understand、answer
    写入次数：1 次

    为什么不用 list[BaseMessage]？
      LangGraph 序列化 State 时 BaseMessage 会出现兼容性问题。
      这里用纯字符串，由 AgentExecutor 在初始化时负责从 Message 转换为文本。
    """

    start_time: float
    """
    执行开始时间（perf_counter 值）
    写入者：AgentExecutor
    写入次数：1 次
    用途：answer 节点计算总耗时
    """

    # =====================================================================
    # 推理层 — understand 和 planner 写入
    # =====================================================================

    understanding: str
    """
    意图理解结果
    写入者：understand 节点
    读取者：planner、answer
    内容示例：
        "用户想知道明天（2026-07-08）武汉的天气情况，以及是否需要带伞出行。
         意图类别: weather_check。关键实体: 城市=武汉, 日期=明天, 关注点=降雨/带伞。"
    """

    city: str
    """
    用户查询的目标城市（中文名）
    写入者：planner / observer（从 CityResolver 结果提取）
    读取者：answer、后续工具调用
    示例： "上海"、"北京"、"应城"
    """

    adcode: str
    """
    用户查询的目标行政区划代码
    写入者：observer（从 CityResolver 结果提取）或 executor
    读取者：weather 工具、answer
    示例： "310000"、"420981"
    """

    plan_summary: str
    """
    计划的人类可读摘要（给前端展示用）
    写入者：planner 节点
    读取者：answer 节点、前端 StepTimeline
    内容示例：
        "步骤1: 解析日期'明天' → 步骤2: 查询武汉天气 → 步骤3: 分析天气给出建议"
    """

    plan_steps: list[dict]
    """
    结构化执行计划
    写入者：planner 节点（或 replan 时覆盖）
    读取者：tool_router、executor、answer

    每个 dict 的字段约定（见文件顶部 PlanStep 说明）。
    最少包含：step_id, action, tool_name, tool_input, reason
    """

    current_step_index: int
    """
    当前正在执行的步骤索引（从 0 开始）
    写入者：executor（每执行完一步 +1）
    读取者：tool_router
    初始值：0
    """

    # =====================================================================
    # 执行层 — executor 和 observer 追加写入
    # =====================================================================

    tool_calls: Annotated[list[dict], operator.add]
    """
    工具调用记录列表（追加写入，不覆盖）

    每个 dict 的字段约定：
    {
        "step_id":     int,       # 对应 plan_steps 中的 step_id
        "tool_name":   str,       # 工具名称
        "tool_input":  dict,      # 输入参数
        "tool_output": str | dict,# 工具返回结果
        "summary":     str,       # 人类可读摘要
        "status":      str,       # "success" | "error"
        "duration_ms": float,     # 耗时（毫秒）
        "error":       str | None # 错误信息（失败时）
    }

    写入者：executor 节点
    读取者：observer、answer、前端 ToolPanel
    """

    observations: Annotated[list[dict], operator.add]
    """
    观察结论列表（追加写入，不覆盖）

    每个 dict 的字段约定：
    {
        "step_id":       int,       # 对应的 plan step_id
        "tool_name":     str,       # 被观察的工具名称
        "observation":   str,       # 自然语言观察结论
        "extracted_facts": dict,    # 提取的关键事实
        "need_replan":   bool,      # 是否需要重新规划
        "confidence":    float,     # 对结论的信心（0~1）
    }

    写入者：observer 节点
    读取者：tool_router（判断 need_replan）、answer
    """

    # =====================================================================
    # 控制层 — router / observer / executor 写入
    # =====================================================================

    next_action: str
    """
    下一步动作
    写入者：tool_router、observer
    读取者：tool_router（条件边判断）
    可能值：
      "continue" — 继续处理下一个 plan step
      "replan"   — 需要重新规划（返回 planner）
      "answer"   — 进入 answer 节点
    """

    iteration_count: int
    """
    Agent 循环计数器（每个 tool_executor → observe 循环算一次迭代）
    写入者：tool_router（每次路由递增）
    安全限制：超过 MAX_ITERATIONS(10) 强制进入 answer 节点
    初始值：0
    """

    retry_count: int
    """
    工具调用重试计数器
    写入者：observer（需要重试时递增）
    安全限制：超过 MAX_RETRIES(3) 放弃重试，标记为失败
    初始值：0
    """

    # =====================================================================
    # 输出层 — answer 节点写入，最终返回给 AgentExecutor
    # =====================================================================

    final_answer: str
    """
    最终回答文本（Markdown 格式）
    写入者：answer 节点
    读取者：AgentExecutor → ChatService → 前端
    内容：综合所有信息后给用户的最终回复
    """

    steps: Annotated[list[dict], operator.add]
    """
    前端展示步骤列表（追加写入，不覆盖）

    每个 dict 的字段约定：
    {
        "id":       str,       # 步骤唯一标识
        "name":     str,       # 显示名称
        "status":   str,       # "completed" | "running" | "failed" | "pending" | "retrying"
        "type":     str,       # "understand" | "plan" | "tool_call" | "observe" | "answer"
        "toolName": str | None,# 工具名称（type=tool_call 时）
        "toolInput": dict | None,
        "toolOutput": dict | None,
        "error":    str | None,# 错误信息（status=failed 时）
        "retryCount": int,     # 重试次数
    }

    写入者：各节点在开始/结束时追加
    读取者：AgentExecutor → ChatResponse.agent_process.steps → 前端
    """

    error: str
    """
    错误信息
    写入者：observer / answer / executor
    为空字符串表示无错误
    """


# =============================================================================
# 安全常量
# =============================================================================

MAX_ITERATIONS = 10
"""
最大迭代次数

当 iteration_count > MAX_ITERATIONS 时，tool_router 强制路由到 answer，
防止 Agent 进入无限循环。

典型场景：plan_steps 包含了 4 个工具调用步骤，
每步（executor + observer）算一次迭代，总共 ≤ 4 次迭代。
10 次上限已经留了充足的 buffer。
"""

MAX_RETRIES = 3
"""
最大重试次数

同一个工具调用失败时，observer 可以设置 next_action="replan" 或
增加 retry_count 触发重试。超过此值则跳过该工具，继续下一步。
"""
