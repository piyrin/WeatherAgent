/**
 * 聊天相关接口
 *
 * 所有接口基于 request.js（统一 baseURL / 拦截器）
 * 对接后端：POST /chat
 */

import request from './request.js'

/**
 * 发送聊天消息
 * @param {string} message - 用户输入的自然语言文本
 * @returns {Promise<{answer: string, steps: string[], tools: Array}>}
 */
export function sendMessage(message) {
  return request.post('/chat', { message })
}
