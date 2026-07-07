# 天气与出行助手智能体系统

基于大语言模型 LangChain 的天气查询与出行建议智能助手，支持多工具调用与 Agent 执行过程可视化。

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + Vite + Element Plus + ECharts（Composition API，纯 JavaScript） |
| 后端 | FastAPI（Python）+ LangChain Agent + SQLAlchemy + SQLite |
| 工具链 | Axios / Vue Router / Pinia |

## 目录结构

```
WeatherAgent/
├── README.md
├── CONFIG_GUIDE.md                 # 前端环境配置说明
├── .gitignore
├── .vscode/                        # 编辑器配置
├── backend/                        # 后端服务
│   ├── app/
│   │   ├── api/                    # API 路由层
│   │   │   └── v1/                 # API v1（chat, history）
│   │   ├── core/                   # 基础设施（配置 / 数据库）
│   │   ├── models/                 # ORM 模型（Conversation, Message, ToolCallLog）
│   │   ├── schemas/                # Pydantic 请求/响应 Schema
│   │   ├── services/               # 业务服务层（ChatService, HistoryService）
│   │   ├── agent/                  # LangChain Agent 核心
│   │   ├── tools/                  # 可插拔工具集（天气 / 计算器 / 日期解析 / 路线规划）
│   │   ├── middleware/             # 中间件（CORS / 异常处理 / 请求日志）
│   │   └── utils/                  # 工具函数（日志 / 统一响应）
│   ├── data/                       # SQLite 数据库文件
│   ├── logs/                       # 日志文件
│   ├── tests/                      # 测试
│   ├── run.py                      # 启动入口
│   └── requirements.txt
└── frontend/                       # 前端应用
    ├── src/
    │   ├── api/                    # Axios 封装 + 接口模块（chat.js, history.js, request.js）
    │   ├── config/                 # 统一配置中心
    │   ├── components/             # 公共组件（8 个）
    │   │   ├── Navbar.vue          #   顶部导航栏（聊天 / 关于）
    │   │   ├── Sidebar.vue         #   侧边栏（开启新对话 + 历史记录列表）
    │   │   ├── ChatBox.vue         #   聊天消息展示区
    │   │   ├── MessageItem.vue     #   单条消息渲染
    │   │   ├── InputPanel.vue      #   消息输入框
    │   │   ├── StepTimeline.vue    #   Agent 执行步骤时间线
    │   │   ├── ToolPanel.vue       #   工具调用记录面板
    │   │   └── Loading.vue         #   加载状态指示
    │   ├── views/                  # 页面（4 个）
    │   │   ├── Home.vue            #   首页（功能介绍 + 入口）
    │   │   ├── Chat.vue            #   聊天页（核心交互）
    │   │   ├── About.vue           #   关于页（技术栈介绍）
    │   │   └── History.vue         #   历史记录页（备用）
    │   ├── router/                 # 路由配置
    │   ├── App.vue                 # 主布局（Header + Sidebar + Main）
    │   ├── main.js                 # 入口
    │   └── style.css               # 全局样式 + CSS 变量
    ├── index.html                  # HTML 入口
    ├── vite.config.js              # Vite 构建配置
    ├── .env.development            # 开发环境变量
    └── .env.production             # 生产环境变量
```

## 快速开始

### 前端

```bash
cd frontend
npm install
npm run dev        # 开发模式，http://localhost:5173
npm run build      # 生产构建 → frontend/dist/
```

开发模式下 API 请求通过 Vite proxy 转发到 `http://localhost:8000`。

### 后端

```bash
cd backend
pip install -r requirements.txt
python run.py      # http://localhost:8000
```

## 页面与路由

| 页面 | 路由 | 说明 |
|------|------|------|
| Home | `/` | 首页，功能介绍与入口，无侧边栏 |
| Chat | `/chat` | 聊天窗口，左侧聊天区 + 右侧 Agent 过程面板；左侧有历史记录侧边栏 |
| About | `/about` | 项目信息、技术栈，无侧边栏 |
| History | `/history` | 历史记录列表页（备选入口，主要历史功能已集成到侧边栏） |

## 布局说明

```
┌──────────────────────────────────────────────┐
│  Navbar:  [Logo]    聊天  |  关于    [Tag]   │
├────────┬─────────────────────────────────────┤
│Sidebar │         Chat Page                   │
│        │  ┌───────────────────┬───────────┐  │
│ [+新对话]│  │    ChatBox        │ StepTimeline│  │
│        │  │   (消息列表)       │ ToolPanel │  │
│ 历史记录 │  ├───────────────────┴───────────┤  │
│ · 明天武.│  │  InputPanel (输入框)           │  │
│ · 北京今.│  └───────────────────────────────┘  │
│ · ...   │                                     │
├────────┴─────────────────────────────────────┤
│          后端状态指示                         │
└──────────────────────────────────────────────┘
```

- **Navbar**：仅保留「聊天」和「关于」两个导航项
- **Sidebar**（仅 Chat 页显示）：顶部「开启新对话」按钮，下方历史记录列表，每条显示用户首发消息预览 + 日期，hover 可删除
- **Chat 页**：左侧聊天区 + 右侧 Agent 执行过程面板（StepTimeline + ToolPanel）

## 会话管理

一次完整的对话从「进入聊天页 / 点击开启新对话」开始，之后的所有问答都属于同一个会话。

- 首次发送消息 → 后端自动创建 `Conversation`，标题取用户首发消息前 50 字
- 后续消息自动追加到同一会话（前端跟踪 `conversation_id`）
- 点击侧边栏历史记录 → 加载该会话的全部消息，可继续对话
- 点击「开启新对话」→ 清空当前对话，创建全新会话

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/chat` | 发送消息（`{message, conversation_id?}`）→ `{answer, conversation_id, steps, tools}` |
| GET | `/api/v1/history` | 获取历史会话列表（`?page=&page_size=`） |
| GET | `/api/v1/history/:id` | 获取会话详情（含完整消息列表） |
| DELETE | `/api/v1/history/:id` | 删除指定会话（级联删除消息和工具日志） |
| DELETE | `/api/v1/history` | 清空全部会话 |

## 数据模型

| 表 | 关键字段 | 说明 |
|------|------|------|
| conversations | id, title, status, message_count, created_at, updated_at | 会话表，title = 首发消息前 50 字 |
| messages | id, conversation_id, role, content, content_type, metadata_json | 消息表，role ∈ {user, assistant, system, tool} |
| tool_call_logs | id, message_id, tool_name, tool_input_json, tool_output_text, status | 工具调用日志 |

会话 ↔ 消息是一对多关系，删除会话时级联删除关联消息和工具日志。

## 环境配置

环境变量通过 `.env.*` 文件管理：

- `.env.development` — 开发环境（`VITE_API_BASE_URL=/api`，走代理）
- `.env.production` — 生产环境（`VITE_API_BASE_URL=https://xxx/api`）

数据流：`.env.*` → `src/config/index.js`（唯一读取 `import.meta.env` 的位置）→ 业务代码。

切换部署地址只需修改 `.env.production` 中的 `VITE_API_BASE_URL`。

## 设计风格

白色 + 蓝色 ChatGPT 风格主题，Scoped CSS + CSS 变量，响应式布局适配桌面 / 平板 / 手机。
