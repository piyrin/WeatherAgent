/**
 * 历史记录相关接口
 *
 * 所有接口基于 request.js（统一 baseURL / 拦截器）
 * 对接后端：GET /history | DELETE /history/:id | DELETE /history
 */

import request from './request.js'

/**
 * 获取历史记录列表（分页）
 * @param {Object} params - { page, size }
 * @returns {Promise<{records: Array, total: number}>}
 */
export function getHistory(params = {}) {
  return request.get('/history', { params })
}

/**
 * 删除单条历史记录
 * @param {string|number} id - 记录 ID
 */
export function deleteHistory(id) {
  return request.delete(`/history/${id}`)
}

/**
 * 清空全部历史记录
 */
export function clearHistory() {
  return request.delete('/history')
}
