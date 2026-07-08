# 天气与出行助手智能体系统

基于 LangGraph + LangChain 的天气查询与出行规划智能助手，支持自然语言对话、多工具协同调用、Agent 执行过程可视化，以及路线地图渲染。

## 功能特性

- **自然语言对话**：用户用自然语言提问，Agent 自动理解意图、规划步骤、调用工具、综合回答
- **天气查询**：接入高德天气 API，支持单日/多日预报、降水判断
- **路径规划**：接入高德路径规划 API，支持驾车/公交地铁/步行三种方式，返回距离、耗时、路线坐标串、打车费用
- **地图展示**：前端集成高德 JSAPI 2.0，路线结果以地图卡片形式渲染（路线高亮、起终点标记、点击全屏查看）
- **地铁路线详情**：公交/地铁路线输出完整换乘方案（乘几号线、上下车站、途经站点、换乘点）
- **天气+出行结合**：Agent 综合天气与路线给出交通建议（暴雨推荐地铁、高温推荐打车等）
- **Agent 过程可视化**：右侧面板实时展示执行步骤、工具调用输入输出
- **历史会话管理**：对话持久化到 SQLite，支持查看/删除/清空

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + Vite + Element Plus + ECharts + 高德 JSAPI 2.0（Composition API，纯 JavaScript） |
| 后端 | FastAPI + SQLAlchemy 2.0 + LangGraph + LangChain + SQLite |
| Agent | LangGraph 5 节点（understand → planner → executor → observer → answer） |
| 工具链 | Axios / Vue Router / Pinia / 高德 WebService API |

## 系统架构

```
用户自然语言
    │
    ▼
LangGraph Agent（5 节点）
├── understand   意图理解（LLM）
├── planner      任务规划（LLM 生成 plan_steps + 确定性修正兜底）
├── executor     工具调度（支持 $step_N.field 参数引用，工具间数据传递）
├── observer     观察分析（提取关键事实）
└── answer       LLM 综合回答（聚合工具结果 + 出行建议）
    │
    ▼
可插拔工具层（7 个工具）
├── date_parser    日期解析（支持"明天中午""下午两点"等时段+具体时间）
├── city_resolver  城市名 → 高德 adcode
├── geocoding      地址 ↔ 经纬度互转
├── weather        高德天气 API（单日/多日预报）
├── route_planner  高德路径规划（driving/transit/walking，返回 polyline）
├── ip_location    IP 定位
└── calculator     数值计算
    │
    ▼
FastAPI → Vue → 高德 JSAPI 绘制路线地图
```

## 目录结构

```
weather-agent/
├── README.md
├── .gitignore
├── frontend/                       # 前端应用
│   ├── src/
│   │   ├── api/                    # Axios 封装 + 接口模块（chat / history）
│   │   ├── config/                 # 统一配置中心（唯一读取 import.meta.env）
│   │   ├── components/             # 组件（MessageItem / ChatBox / MapCard / StepTimeline / ToolPanel ...）
│   │   ├── views/                  # 页面（Home / Chat / History / About）
│   │   ├── utils/                  # 工具（amap.js JSAPI 加载器）
│   │   ├── router/ stores/
│   │   ├── App.vue main.js style.css
│   ├── public/ index.html
│   ├── vite.config.js
│   ├── .env.development .env.production
│   └── package.json
├── backend/                        # 后端服务
│   ├── run.py                      # 启动入口
│   ├── requirements.txt
│   ├── .env                        # 后端环境变量
│   ├── app/
│   │   ├── main.py                 # FastAPI 入口
│   │   ├── core/                   # config / database / security
│   │   ├── models/                 # ORM（conversation / message / tool_call_log）
│   │   ├── schemas/                # Pydantic Schema（chat / history）
│   │   ├── api/v1/                 # 路由（chat / history / health）
│   │   ├── services/               # 业务编排（chat_service / history_service）
│   │   ├── agent/                  # LangGraph Agent
│   │   │   ├── graph.py            # 图定义（5 节点 + 条件边）
│   │   │   ├── state.py            # AgentState
│   │   │   ├── nodes/              # 节点（planner / executor / observer / answer ...）
│   │   │   ├── prompts/            # 提示词（planner_prompt / answer_prompt）
│   │   │   ├── router.py           # 条件路由
│   │   │   └── tool_registry.py    # 工具注册中心
│   │   ├── tools/                  # 可插拔工具（7 个）
│   │   ├── middleware/             # CORS / 异常处理 / 请求日志
│   │   └── utils/                  # logger / response
│   └── data/                       # SQLite 数据库文件
```

## 快速开始

### 1. 配置高德 API Key

在高德开放平台（https://console.amap.com/dev/key/app）申请两个 Key：

| Key 类型 | 用途 | 配置位置 |
|----------|------|----------|
| Web服务 API | 后端调用（天气/地理编码/路径规划） | `backend/.env` 的 `AMAP_API_KEY` |
| Web端 JS API | 前端地图渲染 | `frontend/.env.development` 的 `VITE_AMAP_JSAPI_KEY` + `VITE_AMAP_SECURITY_CODE` |

### 2. 启动后端

```bash
cd weather-agent/backend
pip install -r requirements.txt
# 编辑 .env，填入 AMAP_API_KEY、LLM_API_KEY 等
python run.py          # http://localhost:8000
```

### 3. 启动前端

```bash
cd weather-agent/frontend
npm install
# 编辑 .env.development，填入 VITE_AMAP_JSAPI_KEY 和 VITE_AMAP_SECURITY_CODE
npm run dev            # http://localhost:5173
```

开发模式下前端 API 请求通过 Vite proxy 转发到 `http://localhost:8000`。

### 4. 生产构建

```bash
cd weather-agent/frontend
npm run build          # 产物 → frontend/dist/
```

## 页面

| 页面 | 路由 | 说明 |
|------|------|------|
| Home | `/` | 首页，功能介绍与入口 |
| Chat | `/chat` | 智能聊天窗口，左侧对话 + 右侧 Agent 执行过程/工具调用面板 |
| History | `/history` | 历史会话查看、删除、清空 |
| About | `/about` | 项目信息、技术栈 |

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/chat` | 发送消息，返回 `{message, agent_process: {steps, tool_calls}}` |
| GET | `/api/v1/history` | 获取历史会话列表 |
| GET | `/api/v1/history/{id}` | 获取指定会话详情 |
| DELETE | `/api/v1/history/{id}` | 删除指定会话 |
| DELETE | `/api/v1/history` | 清空全部会话 |
| GET | `/api/v1/health` | 健康检查 |

## 环境配置

### 后端（`backend/.env`）

| 变量 | 说明 |
|------|------|
| `AMAP_API_KEY` | 高德 WebService API Key（天气/地理编码/路径规划共用） |
| `AMAP_BASE_URL` | 高德 API 基础地址（默认 `https://restapi.amap.com`） |
| `LLM_API_KEY` | LLM API 密钥 |
| `LLM_MODEL` | LLM 模型名（默认 `glm-4-flash`） |
| `DATABASE_URL` | SQLite 连接字符串 |

### 前端（`frontend/.env.development` / `.env.production`）

| 变量 | 说明 |
|------|------|
| `VITE_API_BASE_URL` | 后端 API 地址（开发 `/api`，生产完整 URL） |
| `VITE_AMAP_JSAPI_KEY` | 高德 JSAPI Key（前端地图渲染，与后端 WebService Key 不同） |
| `VITE_AMAP_SECURITY_CODE` | 高德 JSAPI 安全密钥 |

数据流：`.env.*` → `src/config/index.js`（唯一读取 `import.meta.env` 的位置）→ 业务代码。

切换部署地址只需修改 `.env.production` 中的 `VITE_API_BASE_URL`。

## 工具清单

| 工具 | 入参 | 出参 | 数据源 |
|------|------|------|--------|
| `date_parser` | `date_text` | date / weekday / time_period | 本地计算 |
| `city_resolver` | `city` | adcode / province / level | 本地 cities.json |
| `geocoding` | `address` 或 `location` | location / formatted_address / adcode | 高德地理编码 API |
| `weather` | `adcode` / `date` / `days` | 天气状况 / 温度 / has_precipitation / forecast_days | 高德天气 API |
| `route_planner` | `origin` / `destination` / `travel_mode` / `city` | distance / duration / polyline / transit_detail / taxi_cost | 高德路径规划 API |
| `ip_location` | `ip`（可选） | province / city / adcode | 高德 IP 定位 API |
| `calculator` | `expression` | result / value | 本地计算 |

## 设计风格

白色 + 蓝色 ChatGPT 风格主题，Scoped CSS + CSS 变量，响应式布局适配桌面 / 平板 / 手机。
