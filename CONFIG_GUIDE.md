# 天气与出行助手智能体系统 - 环境配置改造

## 改造内容

将项目从"硬编码 baseURL"升级为 **Vite 多环境配置 + 统一配置中心** 的企业级方案。

## 新增/修改文件

| 文件 | 类型 | 职责 |
|------|------|------|
| `.env.development` | 新增 | 开发环境变量（VITE_API_BASE_URL=/api） |
| `.env.production` | 新增 | 生产环境变量（VITE_API_BASE_URL=https://xxx.xxx.xxx/api） |
| `src/config/index.js` | 新增 | 统一配置中心，唯一读取 import.meta.env 的地方 |
| `src/api/request.js` | 新增 | Axios 封装，baseURL 从 config 读取 |
| `src/api/chat.js` | 新增 | 聊天相关接口 |
| `src/api/history.js` | 新增 | 历史记录相关接口 |
| `src/api/index.js` | 删除 | 旧 API 文件已废弃 |
| `vite.config.js` | 修改 | 优化 resolve alias |

## 设计原则

1. **唯一配置源**：`.env.*` 文件是唯一的环境配置入口
2. **统一读取**：`src/config/index.js` 是唯一读取 `import.meta.env` 的地方
3. **零业务侵入**：业务代码只从 `@/config` 或 `@/api/*.js` 导入，不直接触碰环境变量
4. **一处切换**：更换部署地址只需改 `.env.production` 中的一个变量

## 配置文件说明

### src/config/index.js
只读一次 `import.meta.env`，提供：
- `config.apiBaseURL` - API 地址
- `config.appTitle` - 应用标题
- `config.isDev` / `config.isProd` - 环境判断
- `config.useMock` - Mock 开关
- `config.debug` - Debug 日志开关
- `debugLog()` - 条件日志函数

### src/api/request.js
Axios 实例封装，读取 `config.apiBaseURL` 创建实例，统一处理：
- 请求拦截器（Debug 日志）
- 响应拦截器（解包 data、错误提示）

## 数据流

```
.env.* → import.meta.env → src/config/index.js → src/api/request.js → src/api/chat.js / history.js → 组件
```

## 开发模式

```bash
npm run dev      # 自动加载 .env.development
                 # API → Vite proxy → http://localhost:8000
```

## 生产部署

```bash
npm run build    # 自动加载 .env.production
                 # 修改 VITE_API_BASE_URL 后 → npm run build
                 # 部署 dist/ 到任意静态服务器
```
