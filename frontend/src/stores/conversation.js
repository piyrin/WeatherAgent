/**
 * 对话状态管理 — Pinia Store
 *
 * 职责：
 * 1. 管理当前活跃的对话 ID
 * 2. 管理历史对话列表数据
 * 3. 提供 Sidebar 和 Chat 组件之间的通信桥梁
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useConversationStore = defineStore('conversation', () => {
  // ========== 状态 ==========

  /** 当前活跃的对话 ID */
  const currentConversationId = ref(null)

  /** 历史对话列表 */
  const conversations = ref([])

  /** 历史列表加载状态 */
  const loading = ref(false)

  /** 刷新触发器（自增计数器，watch 它来响应刷新请求） */
  const refreshTrigger = ref(0)

  // ========== 动作 ==========

  /** 开始新对话 */
  function newConversation() {
    currentConversationId.value = null
  }

  /** 选择历史对话 */
  function selectConversation(id) {
    currentConversationId.value = id
  }

  /** 设置对话列表 */
  function setConversations(list) {
    conversations.value = list
  }

  /** 设置加载状态 */
  function setLoading(val) {
    loading.value = val
  }

  /** 触发列表刷新 */
  function triggerRefresh() {
    refreshTrigger.value++
  }

  return {
    currentConversationId,
    conversations,
    loading,
    refreshTrigger,
    newConversation,
    selectConversation,
    setConversations,
    setLoading,
    triggerRefresh
  }
})
