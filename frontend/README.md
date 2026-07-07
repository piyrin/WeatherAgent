# 前端

Vue 3 + Vite + Element Plus + ECharts

## 快速开始

```bash
npm install
npm run dev    # http://localhost:5173
npm run build  # 生产构建
```

## 页面路由

| 页面 | 路由 | 说明 |
|------|------|------|
| Home | `/` | 首页 |
| Chat | `/chat` | 智能聊天 + Agent 执行步骤可视化 |
| History | `/history` | 历史会话 |
| About | `/about` | 项目信息 |

## 组件

- `ChatBox.vue` - 聊天消息展示
- `InputPanel.vue` - 输入面板
- `Loading.vue` - 加载动画
- `MessageItem.vue` - 消息项
- `Navbar.vue` - 导航栏
- `Sidebar.vue` - 侧边栏
- `StepTimeline.vue` - Agent 执行步骤时间线
- `ToolPanel.vue` - 工具调用面板

## API 代理

开发环境下 Vite 代理配置：

```js
// vite.config.js
server: {
  proxy: {
    '/api': 'http://localhost:8000'
  }
}
```

## 环境配置

详见 [CONFIG_GUIDE.md](./CONFIG_GUIDE.md)
