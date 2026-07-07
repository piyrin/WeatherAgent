/**
 * 历史记录相关接口
 *
 * 所有接口基于 request.js（统一 baseURL / 拦截器）
 * 对接后端：GET /api/v1/history | DELETE /api/v1/history/:id | DELETE /api/v1/history
 */

import request from './request.js'

/**
 * 获取历史记录列表（分页）
 * @param {Object} params - { page, page_size }
 * @returns {Promise<{conversations: Array, total: number, page: number, page_size: number}>}
 */
export function getHistory(params = {}) {
  return request.get('/v1/history', { params })
}

/**
 * 删除单条历史记录
 * @param {string|number} id - 记录 ID
 */
export function deleteHistory(id) {
  return request.delete(`/v1/history/${id}`)
}

/**
 * 获取会话详情（含完整消息列表）
 * @param {string} id - 会话 ID
 * @returns {Promise<{id: string, title: string, messages: Array, created_at: string, updated_at: string}>}
 */
export function getConversationDetail(id) {
  return request.get(`/v1/history/${id}`)
}

/**
 * 清空全部历史记录
 */
export function clearHistory() {
  return request.delete('/v1/history')
}
