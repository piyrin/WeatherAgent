/**
 * 历史记录相关接口
 *
 * 所有接口基于 request.js（统一 baseURL / 拦截器）
 * 对接后端：
 *   GET    /api/v1/history       — 获取会话列表
 *   GET    /api/v1/history/:id   — 获取会话详情
 *   DELETE /api/v1/history/:id   — 删除指定会话
 *   DELETE /api/v1/history       — 清空全部会话
 */

import request from './request.js'

/**
 * 获取历史记录列表（分页）
 * @param {Object} params - { page, size }
 * @returns {Promise<{conversations: Array, total: number}>}
 */
export async function getHistory(params = {}) {
  const response = await request.get('/v1/history', { params })
  // 后端返回: { code: 200, data: { conversations: [...], total: N } }
  // axios 拦截器已取 response.data，所以 response = { code, data: { conversations, total } }
  const payload = response?.data || response || {}
  return {
    conversations: (payload.conversations || []).map(conv => ({
      id: conv.id,
      title: conv.title || '新对话',
      message_count: conv.message_count || 0,
      // TODO: 等后端添加 first_user_message 字段后启用
      first_user_message: conv.first_user_message || null,
      last_message: conv.last_message || null,
      created_at: conv.created_at || '',
      updated_at: conv.updated_at || ''
    })),
    total: payload.total || 0
  }
}

/**
 * 获取单个会话详情（含完整消息列表）
 * @param {string} conversationId - 会话 ID
 * @returns {Promise<{id: string, title: string, messages: Array}>}
 */
export async function getConversationDetail(conversationId) {
  const response = await request.get(`/v1/history/${conversationId}`)
  const payload = response?.data || response || {}
  return {
    id: payload.id,
    title: payload.title || '新对话',
    messages: (payload.messages || []).map(msg => ({
      id: msg.id,
      role: msg.role,
      content: msg.content,
      created_at: msg.created_at || ''
    })),
    created_at: payload.created_at || '',
    updated_at: payload.updated_at || ''
  }
}

/**
 * 删除单条历史记录
 * @param {string} id - 会话 ID
 */
export function deleteHistory(id) {
  return request.delete(`/v1/history/${id}`)
}

/**
 * 清空全部历史记录
 */
export function clearHistory() {
  return request.delete('/v1/history')
}
