/**
 * =============================================
 * Axios 请求封装（唯一实例）
 * =============================================
 *
 * 职责：
 * 1. 创建 axios 实例，baseURL 从 config 统一读取
 * 2. 请求拦截器：注入统一请求头、打印 Debug 日志
 * 3. 响应拦截器：解包 response.data、统一错误提示
 *
 * 业务代码不直接使用本文件。
 * 各 api 模块（chat.js / history.js）封装具体接口后对外暴露。
 */

import axios from 'axios'
import { ElMessage } from 'element-plus'
import config, { debugLog } from '@/config/index.js'

const request = axios.create({
  baseURL: config.apiBaseURL,
  timeout: config.timeout,
  headers: { 'Content-Type': 'application/json' }
})

// ========== 请求拦截器 ==========
request.interceptors.request.use(
  (req) => {
    if (config.debug) {
      debugLog(`→ ${req.method.toUpperCase()} ${req.baseURL}${req.url}`, req.data || req.params || '')
    }
    return req
  },
  (error) => Promise.reject(error)
)

// ========== 响应拦截器 ==========
request.interceptors.response.use(
  (response) => {
    if (config.debug) {
      debugLog(`← ${response.config.url}`, response.data)
    }
    const data = response.data
    return data.data !== undefined ? data.data : data
  },
  (error) => {
    const message = error.response?.data?.detail || error.message || '请求失败'
    ElMessage.error(message)
    debugLog('✕ 请求异常', error)
    return Promise.reject(error)
  }
)

export default request
