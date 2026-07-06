/**
 * =============================================
 * 应用统一配置中心
 * =============================================
 * 所有环境变量统一从这里读取，业务代码只需 import config
 *
 * 设计原则：
 * 1. 唯一真理源：所有配置皆来自 import.meta.env
 * 2. 零业务侵入：业务代码只 import config，不直接触碰 process/import.meta
 * 3. 类型安全：所有值带默认 fallback，防止未定义
 * 4. 一处切换：改 .env 文件即可，无需动任何业务代码
 *
 * 对应文件：
 *   开发 → .env.development (npm run dev)
 *   生产 → .env.production (npm run build)
 */

const config = {
  // ---------- API ----------
  /** API 基础地址，开发时由 Vite proxy 转发，部署后为完整 URL */
  apiBaseURL: import.meta.env.VITE_API_BASE_URL || '/api',

  // ---------- 应用元信息 ----------
  /** 应用标题（页面 tab 名称） */
  appTitle: import.meta.env.VITE_APP_TITLE || '天气与出行助手智能体系统',

  // ---------- 运行模式 ----------
  /** 当前环境：development | production */
  env: import.meta.env.VITE_APP_ENV || import.meta.env.MODE || 'development',

  /** 是否为开发环境 */
  isDev: (import.meta.env.VITE_APP_ENV || import.meta.env.MODE) === 'development',

  /** 是否为生产环境 */
  isProd: (import.meta.env.VITE_APP_ENV || import.meta.env.MODE) === 'production',

  // ---------- 功能开关 ----------
  /** 是否使用 Mock 数据 */
  useMock: import.meta.env.VITE_USE_MOCK === 'true',

  /** 是否输出 Debug 日志 */
  debug: import.meta.env.VITE_DEBUG === 'true',

  // ---------- 超时 ----------
  /** 请求超时时间（毫秒） */
  timeout: 60000
}

export default config

/**
 * 调试日志工具
 * 只有在 VITE_DEBUG=true 时才输出
 */
export function debugLog(...args) {
  if (config.debug) {
    console.log('[WeatherAgent]', ...args)
  }
}
