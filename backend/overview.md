# 后端开发完成概览

## 完成状态：全部文件已写入

`weather-agent/backend/` 共 **49 个文件**，涵盖企业级 FastAPI 项目的完整骨架。

---

## 目录结构

```
backend/
├── .env                          # 环境配置（含 LLM API Key）
├── .env.example                  # 配置模板
├── .gitignore                    # Git 忽略规则
├── requirements.txt              # Python 依赖
├── run.py                        # 启动入口
│
├── app/
│   ├── main.py                   # FastAPI 入口 & 生命周期
│   ├── core/                     # 基础设施层
│   │   ├── config.py             # Pydantic Settings 配置中心
│   │   ├── database.py           # SQLAlchemy 引擎 & 会话 & Base
│   │   └── security.py           # API Key 校验（JWT 预留）
│   ├── models/                   # 数据层（ORM）
│   │   ├── base.py               # BaseModel + TimestampMixin
│   │   ├── conversation.py       # 会话表
│   │   ├── message.py            # 消息表
│   │   └── tool_call_log.py      # Tool 调用日志表
│   ├── schemas/                  # 契约层（Pydantic）
│   │   ├── common.py             # 统一响应格式
│   │   ├── chat.py               # 聊天请求/响应
│   │   └── history.py            # 历史记录请求/响应
│   ├── api/                      # 接口层（路由）
│   │   ├── deps.py               # 公共依赖
│   │   ├── health.py             # 健康检查
│   │   ├── router.py             # 路由汇总
│   │   └── v1/
│   │       ├── chat.py           # POST /api/v1/chat
│   │       └── history.py        # GET/DELETE /api/v1/history
│   ├── services/                 # 业务层
│   │   ├── base_service.py       # Service 基类
│   │   ├── chat_service.py       # 聊天业务编排
│   │   └── history_service.py    # 历史记录 CRUD
│   ├── agent/                    # 智能体层（LangChain）
│   │   ├── agent.py              # Agent 创建 & LLM 工厂
│   │   ├── executor.py           # Agent 执行器
│   │   └── tool_registry.py      # Tool 注册中心
│   ├── tools/                    # 工具层（可插拔）
│   │   ├── base.py               # Tool 抽象基类
│   │   ├── weather.py            # 天气查询
│   │   ├── date_parser.py        # 日期解析
│   │   ├── route_planner.py      # 路线规划
│   │   └── calculator.py         # 计算器（AST 安全求值）
│   ├── middleware/               # 中间件
│   │   ├── cors.py               # CORS 跨域
│   │   ├── exception_handler.py  # 全局异常处理
│   │   └── request_log.py        # 请求日志
│   └── utils/                    # 工具函数
│       ├── logger.py             # Loguru 日志配置
│       └── response.py           # 统一响应构建器
│
├── data/                         # SQLite 数据库文件目录
├── logs/                         # 日志文件目录
└── tests/                        # 测试目录
```

---

## 核心设计亮点

| 特性 | 实现方式 |
|------|----------|
| **Agent 核心** | LangChain ReAct Agent + Function Calling，完全解耦于 HTTP 框架 |
| **Tool 可插拔** | BaseTool 抽象类 + ToolRegistry 注册中心，新增 Tool 不改已有代码 |
| **LLM 可切换** | Provider 工厂模式，`.env` 中改 `LLM_PROVIDER` 即可切换智谱/DeepSeek/Qwen/OpenAI |
| **统一响应** | 所有 API 返回 `{ code, message, data }` JSON 结构 |
| **全局异常** | 三层异常处理（HTTP → 业务 → 兜底），永远不返回 HTML 500 |
| **请求追踪** | 每个请求分配 UUID，通过 `X-Request-ID` 响应头返回 |
| **API 版本化** | `/api/v1/` 前缀，后续可并行 `v2` 目录 |
| **安全计算器** | AST 白名单求值，杜绝 `eval()` 代码注入 |

---

## 启动方式

```bash
cd weather-agent/backend
pip install -r requirements.txt
# 修改 .env 中的 LLM_API_KEY
python run.py
# 访问 http://localhost:8000/docs 查看 API 文档
```

## API 清单

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/health` | 健康检查 |
| `POST` | `/api/v1/chat` | 发送聊天消息 |
| `GET` | `/api/v1/history` | 获取会话列表 |
| `GET` | `/api/v1/history/{id}` | 获取会话详情 |
| `DELETE` | `/api/v1/history/{id}` | 删除指定会话 |
| `DELETE` | `/api/v1/history` | 清空所有会话 |
