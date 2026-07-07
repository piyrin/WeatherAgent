# 天气与出行助手 — Agent 数据协议与接口规范

> 版本：v1.0 | 日期：2026-07-07 | 作者：Agent 架构设计
>
> 本规范定义了整个 Agent 系统的数据流与接口契约。**所有模块开发必须严格遵循此规范。**

---

## 目录

1. [FastAPI → Agent 调用协议](#1-fastapi--agent-调用协议)
2. [AgentState（LangGraph State）](#2-agentstatelanggraph-state)
3. [Planner 输出格式](#3-planner-输出格式)
4. [Tool Router 规范](#4-tool-router-规范)
5. [Tool 统一输入格式](#5-tool-统一输入格式)
6. [Tool 统一返回格式](#6-tool-统一返回格式)
7. [Observation 存储规范](#7-observation-存储规范)
8. [Agent → FastAPI 返回格式](#8-agent--fastapi-返回格式)
9. [Vue 前端字段对照](#9-vue-前端字段对照)
10. [完整数据流图](#10-完整数据流图)

---

## 1. FastAPI → Agent 调用协议

ChatService 调用 AgentExecutor 时的输入契约：

| 字段 | 类型 | 必填 | 来源 | 作用 |
|------|------|------|------|------|
| `message` | `string` | 是 | 用户输入 | Agent 推理核心目标 |
| `conversation_id` | `string`(UUID) | 是 | 数据库 | 关联会话、加载历史 |
| `chat_history` | `List[Message]` | 否 | 数据库构建 | LangChain 格式对话上下文 |
| `current_time` | `string`(ISO 8601) | 否 | 服务端生成 | Agent 感知当前时间 |
| `config` | `object` | 否 | .env 配置 | 可覆盖参数 |

```json
{
  "message": "明天去武汉大学需要带伞吗",
  "conversation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "chat_history": [
    {"role": "user", "content": "你好"},
    {"role": "assistant", "content": "你好！我是天气助手..."}
  ],
  "current_time": "2026-07-07T09:30:00+08:00",
  "config": {}
}
```

---

## 2. AgentState（LangGraph State）

LangGraph 中每个 Node 共享的 State 结构：

```
AgentState（基于 MessagesState 扩展）
├── 输入层（初始化后只读）
│   ├── user_message: str
│   ├── conversation_id: str
│   ├── chat_history: List[Message]
│   └── current_time: str
│
├── 推理层（Planner/ReAct 持续更新）
│   ├── understanding: str
│   ├── plan: Plan | null
│   ├── plan_revision: int          (初始 0)
│   ├── messages: List[BaseMessage] (LangGraph 内部消息流)
│   └── iteration_count: int        (防无限循环)
│
├── 执行层（Tool 调用后写入）
│   ├── tool_calls: List[ToolCallRecord]   (按执行顺序追加)
│   ├── observations: List[Observation]     (按执行顺序追加)
│   └── current_action: str | null
│
├── 控制层（Router/流程控制）
│   ├── next_action: "plan"|"call_tool"|"observe"|"replan"|"answer"|"end"
│   └── should_continue: bool
│
└── 输出层（最终组装）
    ├── final_answer: str | null
    ├── steps: List[AgentStep]      (给前端的执行步骤)
    └── errors: List[str]           (非致命错误)
```

### Node 与 State 的读写关系

| Node | Writer（写入 State） | Reader（读取 State） |
|------|---------------------|---------------------|
| `understand` | `understanding`, `next_action` | `user_message`, `chat_history` |
| `plan` | `plan`, `next_action` | `understanding`, `user_message` |
| `tool_router`（边） | — | `plan.next_steps`, `tool_calls[-1].status` |
| `call_tool` | `tool_calls`（追加）, `next_action` | `plan.next_steps`, `chat_history` |
| `observe` | `observations`（追加）, `next_action` | `tool_calls[-1]`, `plan` |
| `replan` | `plan`（更新）, `plan_revision++`, `next_action` | `observations`, `plan`, `iteration_count` |
| `answer` | `final_answer`, `next_action`, `steps[]` | `understanding`, `plan`, `tool_calls`, `observations` |

---

## 3. Planner 输出格式

Planner Node 输出到 `state.plan` 的结构化 JSON：

```json
{
  "user_intent": "查询明天武汉的天气，判断是否需要带伞",
  "intent_category": "weather_check",
  "reasoning": "用户提到了'明天'和'武汉'，需要先解析日期，再查询天气，最后根据天气判断",
  "plan": [
    {
      "step_id": 1,
      "action": "call_tool",
      "tool_name": "date_parser",
      "tool_input": { "date_text": "明天" },
      "reason": "用户使用相对时间'明天'，需解析为具体日期",
      "depends_on": [],
      "on_failure": "retry_once"
    },
    {
      "step_id": 2,
      "action": "call_tool",
      "tool_name": "weather",
      "tool_input": { "city": "武汉", "date": "$step_1.parsed_date" },
      "reason": "获取武汉在目标日期的天气数据",
      "depends_on": [1],
      "on_failure": "skip_and_notify"
    },
    {
      "step_id": 3,
      "action": "observe",
      "reason": "根据天气数据判断是否需要带伞",
      "depends_on": [2]
    },
    {
      "step_id": 4,
      "action": "answer",
      "reason": "综合所有结果生成回答",
      "depends_on": [1, 2, 3]
    }
  ],
  "total_steps": 4,
  "estimated_tools": ["date_parser", "weather"]
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `user_intent` | `string` | 用户意图的自然语言描述 |
| `intent_category` | `string` | 意图分类：weather_check / travel_advice / date_query / calculation / general_chat |
| `reasoning` | `string` | 规划推理过程 |
| `plan[]` | `array` | 执行步骤列表 |
| `plan[].step_id` | `int` | 步骤序号 |
| `plan[].action` | `string` | call_tool / observe / answer |
| `plan[].tool_name` | `string` | 工具名称（action=call_tool 时必填） |
| `plan[].tool_input` | `object` | 工具参数（支持 `$step_N.field` 引用） |
| `plan[].reason` | `string` | 为什么需要这一步 |
| `plan[].depends_on` | `int[]` | 依赖的 step_id |
| `plan[].on_failure` | `string` | 失败策略：retry_once / skip_and_notify / abort |
| `total_steps` | `int` | 总步骤数 |
| `estimated_tools` | `string[]` | 预计调用的工具 |

---

## 4. Tool Router 规范

### 4.1 Router 是什么

Tool Router 是 LangGraph 的**条件边（Conditional Edge）**，不是独立 Node。

### 4.2 输入（从 State 读取）

```
plan.next_steps[0]        → 当前待执行的步骤
tool_calls[-1].status     → 上一个工具状态
observations[-1]          → 上一次观察结论
iteration_count           → 循环计数（防止死循环）
```

### 4.3 路由决策逻辑

```
当前步骤 action 是什么？
├── action = call_tool  → 转到 call_tool Node
├── action = observe    → 转到 observe Node
│     └── 观察后判断
│          ├── need_replan = true  → 转到 replan Node
│          └── need_replan = false → 继续下一步（回到 Router）
├── action = answer     → 转到 answer Node
└── 无后续步骤          → 转到 answer Node
```

### 4.4 返回值

```
next_action: "call_tool" | "observe" | "replan" | "answer" | "end"
should_continue: bool
```

### 4.5 安全约束

- `iteration_count > MAX_ITERATIONS(10)` → 强制终止，转到 answer
- `plan_revision > MAX_REVISIONS(3)` → 放弃重新规划，用现有信息回答

---

## 5. Tool 统一输入格式

所有 Tool 通过 JSON Schema 定义输入，LangChain 自动进行参数填充。

### WeatherTool

```json
{
  "city": "武汉",           // string, 必填
  "date": "2026-07-08"      // string, 可选，默认今天
}
```

### DateParserTool

```json
{
  "date_text": "明天"       // string, 必填
}
```

### RoutePlannerTool

```json
{
  "origin": "武汉大学",      // string, 必填
  "destination": "武汉站",   // string, 必填
  "travel_mode": "driving"  // string, 可选，默认 driving
}
```

### CalculatorTool

```json
{
  "expression": "(25 + 15) * 0.6"  // string, 必填
}
```

### 通用约束

| 约束 | 说明 |
|------|------|
| 参数命名 | snake_case |
| 必填声明 | Schema 中 `required: [...]` |
| 类型校验 | JSON Schema 自动校验 |
| 默认值 | Schema 中声明 `default` |
| 新增 Tool | 只需实现：`name` / `description` / `input_schema` / `_execute` |

---

## 6. Tool 统一返回格式

所有 `_execute()` 方法返回统一结构：

### 成功

```json
{
  "success": true,
  "result": {
    "city": "武汉",
    "date": "2026-07-08",
    "weather": "中雨",
    "temperature": "25°C",
    "humidity": "85%"
  },
  "summary": "武汉 2026-07-08 天气：中雨，25°C，湿度85%",
  "error": null,
  "duration_ms": 320
}
```

### 失败

```json
{
  "success": false,
  "result": null,
  "summary": "天气查询失败",
  "error": {
    "code": "API_TIMEOUT",
    "message": "天气服务请求超时",
    "detail": "请求 openweathermap API 超过 5 秒未响应"
  },
  "duration_ms": 5001
}
```

### 业务异常

```json
{
  "success": false,
  "result": null,
  "summary": "未找到城市信息",
  "error": {
    "code": "CITY_NOT_FOUND",
    "message": "未找到城市'火星'的天气数据",
    "detail": null
  },
  "duration_ms": 45
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `success` | `bool` | 执行是否成功 |
| `result` | `object\|null` | 成功时的业务数据 |
| `summary` | `string` | 人类可读的摘要 |
| `error` | `object\|null` | 失败信息 |
| `error.code` | `string` | 错误码 |
| `error.message` | `string` | 错误简述 |
| `error.detail` | `string\|null` | 错误详情（调试用） |
| `duration_ms` | `int` | 执行耗时 |

### 错误码规范

| 错误码 | 含义 | 处理策略 |
|--------|------|---------|
| `API_TIMEOUT` | 外部 API 超时 | retry_once |
| `CITY_NOT_FOUND` | 城市不存在 | skip_and_notify |
| `PARSE_ERROR` | 输入解析失败 | abort |
| `RATE_LIMIT` | API 限流 | retry_once |
| `UNKNOWN` | 未知错误 | abort |

---

## 7. Observation 存储规范

Observation Node 读取 Tool 返回结果，写入分析结论。

### 写入 State 的结构

```json
{
  "step_id": 2,
  "tool_name": "weather",
  "observation": "武汉明天(2026-07-08)有中雨，气温25°C，湿度85%，需要带伞",
  "extracted_facts": {
    "has_rain": true,
    "temperature": "25°C",
    "need_umbrella": true
  },
  "need_replan": false,
  "replan_reason": null,
  "confidence": 0.95
}
```

### 写入位置与用途

| 字段 | 写入 State 位置 | 用途 |
|------|----------------|------|
| `observation` | `observations[]` 追加 | 供 answer Node 综合生成回答 |
| `extracted_facts` | `observations[]` 内嵌 | 结构化关键事实 |
| `need_replan` | Router 判断条件 | 是否需要重新规划 |
| `confidence` | `observations[]` 内嵌 | 对结论的信心（0-1） |

### replan 触发条件

- `confidence < 0.3` → 必须重新规划
- Tool 返回 `success=false` 且 `on_failure=replan` → 重新规划
- 任意 Observation 发现关键事实矛盾 → 重新规划

---

## 8. Agent → FastAPI 返回格式

AgentExecutor.run() 返回值，经 ChatService 组装为 ChatResponse：

```json
{
  "success": true,
  "answer": "根据查询结果，武汉明天（7月8日）有中雨，气温25°C，建议带伞出行。",

  "steps": [
    {
      "id": "step-1",
      "name": "理解用户意图",
      "status": "completed",
      "type": "understand"
    },
    {
      "id": "step-2",
      "name": "制定执行计划",
      "status": "completed",
      "type": "plan"
    },
    {
      "id": "step-3",
      "name": "调用日期解析工具",
      "status": "completed",
      "type": "tool_call",
      "toolName": "date_parser",
      "toolInput": { "date_text": "明天" },
      "toolOutput": { "parsed": "2026-07-08", "dayOfWeek": "星期三" },
      "error": null,
      "retryCount": 0
    },
    {
      "id": "step-4",
      "name": "调用天气查询工具",
      "status": "completed",
      "type": "tool_call",
      "toolName": "weather",
      "toolInput": { "city": "武汉", "date": "2026-07-08" },
      "toolOutput": { "weather": "中雨", "temperature": "25°C", "humidity": "85%" },
      "error": null,
      "retryCount": 0
    },
    {
      "id": "step-5",
      "name": "分析天气结果",
      "status": "completed",
      "type": "observe"
    },
    {
      "id": "step-6",
      "name": "生成最终回答",
      "status": "completed",
      "type": "answer"
    }
  ],

  "plan": {
    "intent_category": "weather_check",
    "reasoning": "用户询问明天武汉天气并关注是否需要带伞",
    "total_steps": 6
  },

  "tools": [
    {
      "name": "date_parser",
      "input": { "date_text": "明天" },
      "output": { "parsed": "2026-07-08", "dayOfWeek": "星期三" },
      "status": "completed",
      "duration_ms": 12
    },
    {
      "name": "weather",
      "input": { "city": "武汉", "date": "2026-07-08" },
      "output": { "weather": "中雨", "temperature": "25°C", "humidity": "85%" },
      "status": "completed",
      "duration_ms": 320
    }
  ],

  "total_duration_ms": 2450,
  "error_message": null
}
```

### Agent 字段 → ChatResponse 映射

| Agent 返回字段 | ChatResponse 字段 | 说明 |
|---------------|------------------|------|
| `answer` | `.message` | 最终回答文本 |
| `steps[]` | `.agent_process.steps` | 前端 Timeline 直接使用 |
| `plan` | `.agent_process.plan` | 规划摘要 |
| `tools[]` | `.agent_process.tool_calls` | 工具调用记录面板 |
| `total_duration_ms` | `.agent_process.total_duration_ms` | 总耗时 |
| `success` / `error_message` | 决定 HTTP 状态码 | 错误响应 |

### steps[] 中每个 Step 对象的完整字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | `string` | 否 | 步骤唯一ID |
| `name` | `string` | 是 | 步骤显示名称 |
| `status` | `string` | 是 | pending / running / completed / failed / retrying |
| `type` | `string` | 否 | understand / plan / tool_call / observe / answer |
| `toolName` | `string` | 否 | 工具名称（type=tool_call 时） |
| `toolInput` | `object` | 否 | 工具输入参数 |
| `toolOutput` | `object` | 否 | 工具返回结果 |
| `error` | `string` | 否 | 错误信息（status=failed 时） |
| `retryCount` | `int` | 否 | 重试次数 |

---

## 9. Vue 前端字段对照

### 前端组件与后端字段的对应关系

| Vue 组件 | Prop | 后端字段 | 格式要求 |
|----------|------|---------|---------|
| `StepTimeline` | `steps` | `response.steps` | `Array<Step>` |
| `StepTimeline` | `currentStep` | 前端本地计算 | 根据 `steps[].status` 推断 |
| `StepTimeline` | `isRunning` | 前端本地状态 | 请求中为 true |
| `ToolPanel` | `tools` | `response.tools` | `Array<Tool>` |

### Step 对象渲染映射

| Step 字段 | Timeline 渲染效果 |
|----------|------------------|
| `name` | 步骤名称文字 |
| `status: "running"` | 蓝色节点 + Loading 图标 |
| `status: "completed"` | 绿色节点 + Check 图标 |
| `status: "failed"` | 红色节点 + Warning 图标 |
| `status: "retrying"` | 黄色节点 + Refresh 图标 |
| `toolName` | 工具名称标签（Tag） |
| `toolInput` | 折叠面板 → 输入参数 |
| `toolOutput` | 折叠面板 → 返回结果 |
| `error` | 红色 Alert 提示框 |
| `retryCount > 0` | "重试 N 次" Badge |

### 兼容性承诺

前端 StepTimeline 组件**同时支持**：
1. **简化格式**：`string[]`（如 `["理解问题", "调用工具", "生成回答"]`），组件自动推断状态
2. **完整格式**：`Step[]`（上述结构），完整状态与工具展示

当后端从简化格式升级到完整格式时，**无需任何前端修改**。

---

## 10. 完整数据流

```
┌─────────────────────────────────────────────────────────────────┐
│ 用户                                                                │
│   │                                                                │
│   │ "明天去武汉大学需要带伞吗"                                         │
│   ▼                                                                │
│ ┌──────────────────────────────────────────────────────────────┐  │
│ │ Vue 前端                                                       │  │
│ │   POST /api/v1/chat → { message, conversation_id }             │  │
│ └──────────────────────────┬───────────────────────────────────┘  │
│                            ▼                                        │
│ ┌──────────────────────────────────────────────────────────────┐  │
│ │ FastAPI 路由层                                                 │  │
│ │   校验 ChatRequest → 调用 ChatService                           │  │
│ └──────────────────────────┬───────────────────────────────────┘  │
│                            ▼                                        │
│ ┌──────────────────────────────────────────────────────────────┐  │
│ │ ChatService（业务编排）                                        │  │
│ │   1. 创建/查找 Conversation                                     │  │
│ │   2. 保存用户 Message                                          │  │
│ │   3. 构建 chat_history（SQLite → LangChain）                   │  │
│ │   4. 调用 AgentExecutor.run()                                  │  │
│ │      ↓ 传入 { message, conversation_id, chat_history,          │  │
│ │               current_time }                                   │  │
│ │   5. 接收 AgentResult                                          │  │
│ │   6. 保存助手 Message + ToolCallLog                            │  │
│ │   7. 组装 ChatResponse 返回                                    │  │
│ └──────────────────────────┬───────────────────────────────────┘  │
│                            ▼                                        │
│ ┌──────────────────────────────────────────────────────────────┐  │
│ │ AgentExecutor（Agent 执行器）                                   │  │
│ │   初始化 AgentState → 进入 LangGraph 图                         │  │
│ │                                                                │  │
│ │   ┌─────────────────────────────────────────────────────┐    │  │
│ │   │ LangGraph 图                                          │    │  │
│ │   │                                                       │    │  │
│ │   │   ENTRY                                               │    │  │
│ │   │     ▼                                                 │    │  │
│ │   │   [understand]  → write: understanding                │    │  │
│ │   │     ▼                                                 │    │  │
│ │   │   [plan]        → write: plan (JSON)                  │    │  │
│ │   │     ▼                                                 │    │  │
│ │   │   [tool_router] → 条件边：根据 plan 决定下一步         │    │  │
│ │   │     │                                                 │    │  │
│ │   │     ├──→ [call_tool]  → write: tool_calls[]            │    │  │
│ │   │     │       ▼                                         │    │  │
│ │   │     │     [observe]    → write: observations[]         │    │  │
│ │   │     │       │                                         │    │  │
│ │   │     │       ├── need_replan? yes → [replan] → back     │    │  │
│ │   │     │       └── need_replan? no  → back to router     │    │  │
│ │   │     │                                                 │    │  │
│ │   │     └──→ [answer]     → write: final_answer, steps[]   │    │  │
│ │   │                                                       │    │  │
│ │   │   EXIT → 返回 AgentResult                              │    │  │
│ │   └─────────────────────────────────────────────────────┘    │  │
│ │                                                                │  │
│ │   组装返回：{ success, answer, steps[], plan, tools[],         │  │
│ │              total_duration_ms }                               │  │
│ └──────────────────────────┬───────────────────────────────────┘  │
│                            ▼                                        │
│ ┌──────────────────────────────────────────────────────────────┐  │
│ │ ChatResponse → Vue 前端                                        │  │
│ │   { answer, steps[], plan, tools[], total_duration_ms }        │  │
│ └──────────────────────────┬───────────────────────────────────┘  │
│                            ▼                                        │
│ ┌──────────────────────────────────────────────────────────────┐  │
│ │ Vue StepTimeline 渲染                                          │  │
│ │   每个 Step 按 status 显示不同颜色/图标/工具详情                  │  │
│ └──────────────────────────────────────────────────────────────┘  │
│   │                                                                │
│   ▼                                                                │
│ 用户看到：执行过程 Timeline + 最终回答                               │
└─────────────────────────────────────────────────────────────────┘
```

### 数据格式速查

| 环节 | 输入 | 输出 |
|------|------|------|
| Vue → FastAPI | `{ message, conversation_id }` | HTTP 200 + `BaseResponse<ChatResponse>` |
| FastAPI → Service | `ChatRequest` | — |
| Service → Agent | `{ message, conversation_id, chat_history, current_time }` | `AgentResult` |
| Agent → Graph | `AgentState` 初始化 | `AgentState`（图结束后） |
| Graph Node: plan | `user_message` | `plan` (JSON) |
| Graph Node: call_tool | `{ city, date, ... }` | `{ success, result, summary, error, duration_ms }` |
| Graph Node: observe | `tool_calls[-1]` | `{ observation, extracted_facts, need_replan }` |
| Graph Node: answer | `{ understanding, plan, observations }` | `final_answer` |
| Agent → Service | `AgentResult` | — |
| Service → FastAPI | `ChatResponse` | — |
| FastAPI → Vue | `BaseResponse<ChatResponse>` | — |
| Vue Timeline | `response.steps` | 动态渲染 |

---

> **扩展性保证**：新增 Tool 只需实现 `name` / `description` / `input_schema` / `_execute` 四个接口，
> 并在 ToolRegistry 注册即可。无需修改 Agent/Tool Router/LangGraph/Parser/Render 等任何其他模块。
