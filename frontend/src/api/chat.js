/**
 * 聊天相关接口
 *
 * 所有接口基于 request.js（统一 baseURL / 拦截器）
 * 对接后端：POST /api/v1/chat
 *
 * ========================
 * 后端返回数据结构规范
 * ========================
 *
 * 后端 FastAPI + LangGraph 应返回以下结构：
 *
 * {
 *   "answer": "最终回答文本",
 *   "steps": [
 *     {
 *       "id": "step-1",              // 可选，步骤唯一ID
 *       "name": "理解用户问题",        // 必填，步骤显示名称
 *       "status": "completed",        // 必填，步骤状态
 *                                       // pending | running | completed | failed | retrying
 *       "type": "understand",        // 可选，步骤类型
 *                                       // understand | plan | tool_call | observe | answer
 *       "toolName": "get_weather",   // 可选，工具名称（type=tool_call 时）
 *       "toolInput": { ... },        // 可选，工具输入参数
 *       "toolOutput": { ... },       // 可选，工具返回结果
 *       "error": null,               // 可选，错误信息（status=failed 时）
 *       "retryCount": 0              // 可选，重试次数
 *     },
 *     ...
 *   ],
 *   "tools": [
 *     {
 *       "name": "get_weather",
 *       "input": { ... },
 *       "output": { ... }
 *     },
 *     ...
 *   ]
 * }
 *
 * ========================
 * 兼容性说明
 * ========================
 *
 * StepTimeline 组件同时支持两种 steps 格式：
 * 1. 简化格式：string[]（如 ["理解问题", "调用工具", "生成回答"]）
 *    - 组件会自动转换为 Step 对象，根据 currentStep 推断状态
 *    - 适用于最简实现
 * 2. 完整格式：Step[]（上述结构）
 *    - 组件直接使用，支持完整的状态、工具、错误、重试展示
 *    - 推荐后端返回此格式
 *
 * 当后端从简化格式升级到完整格式时，无需修改前端代码。
 */

import request from './request.js'

/**
 * 发送聊天消息
 * @param {string} message - 用户输入的自然语言文本
 * @returns {Promise<{answer: string, steps: Array, tools: Array}>}
 */
export async function sendMessage(message, conversationId = null) {
  const response = await request.post('/v1/chat', {
    message,
    conversation_id: conversationId
  })
  return normalizeChatResponse(response)
}

function normalizeChatResponse(response) {
  const payload = response?.data || response || {}
  const agentProcess = payload.agent_process || {}

  return {
    answer: payload.message || '',
    conversationId: payload.conversation_id || null,
    messageId: payload.message_id || null,
    createdAt: payload.created_at || null,
    steps: agentProcess.steps || [],
    tools: normalizeToolCalls(agentProcess.tool_calls || [])
  }
}

function normalizeToolCalls(toolCalls) {
  return toolCalls.map((tool) => ({
    name: tool.tool_name || tool.name || 'Tool',
    input: tool.tool_input || tool.input || null,
    output: parseToolOutput(tool.tool_output || tool.output || null),
    status: normalizeStatus(tool.status),
    durationMs: tool.duration_ms || null
  }))
}

function normalizeStatus(status) {
  if (status === 'success') return 'completed'
  if (status === 'error') return 'failed'
  return status || 'completed'
}

function parseToolOutput(output) {
  if (typeof output !== 'string') return output
  try {
    return JSON.parse(output.replaceAll("'", '"'))
  } catch (error) {
    return output
  }
}
