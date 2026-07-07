# 天气与出行助手智能体系统

基于大语言模型 LangChain 的天气查询与出行建议智能助手，支持多工具调用与 Agent 执行过程可视化。

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + Vite + Element Plus + ECharts（Composition API，纯 JavaScript） |
| 后端 | FastAPI（Python）+ LangChain Agent |
| 工具链 | Axios / Vue Router / Pinia |

## 目录结构

```
weather-agent/
├── README.md                   # 项目总览
├── .gitignore                  # 仓库级忽略规则
├── .vscode/                    # 编辑器配置
├── agent/                      # Agent 核心（独立模块）
├── backend/                    # 后端服务
│   ├── app/
│   │   ├── api/                # API 路由层
│   │   │   └── v1/             # API v1 版本
│   │   ├── core/               # 基础设施（配置/数据库/安全）
│   │   ├── models/             # ORM 数据模型
│   │   ├── schemas/            # Pydantic 请求/响应模型
│   │   ├── services/           # 业务服务层
│   │   ├── agent/              # LangChain Agent 核心
│   │   ├── tools/              # 可插拔工具集
│   │   ├── middleware/         # 中间件
│   │   └── utils/              # 工具函数
│   ├── data/                   # SQLite 数据库
│   ├── logs/                   # 日志文件
│   └── tests/                  # 测试
├── database/                   # 数据库相关
├── docs/                       # 文档（接口规范等）
├── frontend/                   # 前端应用
│   ├── src/
│   │   ├── api/                # Axios 封装 + 接口模块
│   │   ├── config/             # 统一配置中心
│   │   ├── components/         # 公共组件（9 个）
│   │   ├── views/              # 页面（4 个）
│   │   ├── router/             # 路由配置
│   │   ├── mock/               # Mock 数据
│   │   ├── assets/             # 静态资源
│   │   ├── App.vue             # 主布局
│   │   ├── main.js             # 入口
│   │   └── style.css           # 全局样式
│   ├── public/                 # 静态资源
│   ├── index.html              # HTML 入口
│   ├── vite.config.js          # Vite 构建配置
│   ├── .env.development        # 开发环境变量
│   ├── .env.production         # 生产环境变量
│   └── CONFIG_GUIDE.md         # 配置说明
└── tools/                      # 工具脚本
```

## 快速开始

### 前端

```bash
cd weather-agent/frontend
npm install
npm run dev        # 开发模式，http://localhost:5173
npm run build      # 生产构建 → frontend/dist/
```

开发模式下 API 请求通过 Vite proxy 转发到 `http://localhost:8000`。

### 后端

```bash
cd weather-agent/backend
pip install -r requirements.txt
uvicorn main:app --reload    # http://localhost:8000
```

## 页面

| 页面 | 路由 | 说明 |
|------|------|------|
| Home | `/` | 首页，功能介绍与入口 |
| Chat | `/chat` | 智能聊天窗口，Agent 执行步骤 + 工具调用面板 |
| History | `/history` | 历史会话查看、删除、清空 |
| About | `/about` | 项目信息、技术栈 |

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/chat` | 发送消息 → `{answer, steps, tools}` |
| GET | `/api/v1/history` | 获取历史记录列表 |
| DELETE | `/api/v1/history/:id` | 删除指定会话 |
| DELETE | `/api/v1/history` | 清空全部记录 |

## 环境配置

环境变量通过 `.env.*` 文件管理：

- `.env.development` — 开发环境（`VITE_API_BASE_URL=/api`，走代理）
- `.env.production` — 生产环境（`VITE_API_BASE_URL=https://xxx/api`）

数据流：`.env.*` → `src/config/index.js`（唯一读取 `import.meta.env` 的位置）→ 业务代码。

切换部署地址只需修改 `.env.production` 中的 `VITE_API_BASE_URL`。

## 设计风格

白色 + 蓝色 ChatGPT 风格主题，Scoped CSS + CSS 变量，响应式布局适配桌面 / 平板 / 手机。
