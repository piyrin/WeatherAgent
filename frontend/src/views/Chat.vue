<template>
  <div class="chat-page">
    <!-- 左侧：聊天区 -->
    <div class="chat-left">
      <ChatBox
        ref="chatBoxRef"
        :messages="messages"
        :auto-scroll="autoScroll"
        @clear="handleNewChat"
        @example-click="handleExampleClick"
      />
      <div class="chat-bottom">
        <div v-if="isLoading" class="thinking-bar">
          <Loading text="AI 正在思考中..." />
        </div>
        <InputPanel
          :disabled="isLoading"
          @send="handleSend"
        />
      </div>
    </div>

    <!-- 右侧：Agent 过程面板 -->
    <div class="chat-right">
      <StepTimeline
        :steps="agentSteps"
        :current-step="currentStep"
        :is-running="isLoading"
      />
      <ToolPanel :tools="toolCalls" />
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import config from '@/config/index.js'
import { sendMessage } from '@/api/chat.js'
import { sendMessageMock } from '@/mock/chatMock.js'
import { getHistory, getConversationDetail, deleteHistory } from '@/api/history.js'
import { useConversationStore } from '@/stores/conversation.js'
import ChatBox from '@/components/ChatBox.vue'
import InputPanel from '@/components/InputPanel.vue'
import StepTimeline from '@/components/StepTimeline.vue'
import ToolPanel from '@/components/ToolPanel.vue'
import Loading from '@/components/Loading.vue'

const store = useConversationStore()

// ==================== 聊天状态 ====================
const messages = ref([])
const autoScroll = ref(true)
const chatBoxRef = ref(null)
const isLoading = ref(false)
const agentSteps = ref([])
const currentStep = ref(-1)
const toolCalls = ref([])
const conversationId = ref(null)  // 后端返回的 conversation ID（用于 API 调用）

let messageId = 0

// ==================== 初始化：加载历史列表 ====================
onMounted(() => {
  fetchConversations()
})

async function fetchConversations() {
  store.setLoading(true)
  try {
    const res = await getHistory({ page: 1, size: 50 })
    store.setConversations(res.conversations || [])
  } catch (error) {
    console.error('获取历史记录失败：', error)
    store.setConversations([])
  } finally {
    store.setLoading(false)
  }
}

// ==================== 监听 store 中当前对话的变化 ====================
watch(() => store.currentConversationId, async (newId, oldId) => {
  if (newId === null && oldId !== null) {
    // 新对话：清空聊天区
    clearChatState()
  } else if (newId && newId !== oldId) {
    // 选择了历史对话：加载消息
    await loadConversation(newId)
  }
})

watch(() => store.refreshTrigger, () => {
  fetchConversations()
})

// ==================== 消息处理 ====================
function addMessage(role, content, isStreaming = false) {
  const msg = {
    id: ++messageId,
    role,
    content,
    timestamp: new Date().toISOString(),
    isStreaming
  }
  messages.value.push(msg)
  return msg
}

function updateLastMessage(content) {
  const last = messages.value[messages.value.length - 1]
  if (last && last.role === 'assistant') {
    last.content = content
  }
}

async function handleSend(text) {
  addMessage('user', text)

  isLoading.value = true
  agentSteps.value = []
  currentStep.value = -1
  toolCalls.value = []

  // 添加 AI 占位消息
  addMessage('assistant', '正在分析你的问题...', true)

  try {
    const result = config.useMock
      ? await sendMessageMock(text, (updatedSteps) => {
          agentSteps.value = updatedSteps
          currentStep.value = updatedSteps.findIndex(s => s.status === 'running')
        })
      : await sendMessage(text, conversationId.value)

    // 更新完整结果
    agentSteps.value = result.steps || []
    currentStep.value = result.steps ? result.steps.length - 1 : -1
    toolCalls.value = result.tools || []

    // 更新 conversationId（首次对话时后端返回）
    if (result.conversationId) {
      conversationId.value = result.conversationId

      // 如果是新对话，更新 store 并刷新列表
      if (!store.currentConversationId) {
        store.selectConversation(result.conversationId)
        store.triggerRefresh()
      }
    }

    // 更新最终回答
    updateLastMessage(result.answer || '抱歉，我暂时无法回答这个问题。')
    const lastMsg = messages.value[messages.value.length - 1]
    if (lastMsg) lastMsg.isStreaming = false

    // 提取路线数据，挂载到 assistant 消息上（用于地图卡片渲染）
    // 注意：executor 存的 tool_output 已是 route_planner 的 result 字段（含 polyline），
    // 不是整个 {success, result, ...} 外层结构，因此直接检测 polyline 并用 output 本身
    const routeTool = (result.tools || []).find(
      (t) => t.name === 'route_planner' && t.output && t.output.polyline
    )
    if (routeTool && lastMsg && lastMsg.role === 'assistant') {
      lastMsg.routeData = routeTool.output
    }

  } catch (error) {
    console.error('发送消息失败：', error)
    updateLastMessage('抱歉，请求失败，请检查后端服务是否正常运行。')
    const lastMsg = messages.value[messages.value.length - 1]
    if (lastMsg) lastMsg.isStreaming = false
  } finally {
    isLoading.value = false
  }
}

function handleExampleClick(example) {
  handleSend(example)
}

// ==================== 对话管理 ====================
function clearChatState() {
  messages.value = []
  agentSteps.value = []
  toolCalls.value = []
  currentStep.value = -1
  conversationId.value = null
  messageId = 0
}

function handleNewChat() {
  clearChatState()
  store.newConversation()
  ElMessage.success('已开始新对话')
}

async function loadConversation(id) {
  // 禁用自动滚动，防止加载历史时滚到底部
  autoScroll.value = false

  try {
    const detail = await getConversationDetail(id)
    const msgs = detail.messages || []

    // 重建消息列表（只显示 user 和 assistant 消息）
    messageId = 0
    messages.value = msgs
      .filter(m => m.role === 'user' || m.role === 'assistant')
      .map(m => ({
        id: ++messageId,
        role: m.role,
        content: m.content,
        timestamp: m.created_at || '',
        isStreaming: false
      }))

    conversationId.value = id
    agentSteps.value = []
    toolCalls.value = []
    currentStep.value = -1

    // 滚到顶部
    await nextTick()
    chatBoxRef.value?.scrollToTop?.()
  } catch (error) {
    console.error('加载对话详情失败：', error)
    ElMessage.error('加载对话失败')
    // 加载失败时重置为当前对话
    store.selectConversation(conversationId.value)
  } finally {
    // 重新启用自动滚动（稍延迟，确保 scrollToTop 先执行完）
    setTimeout(() => {
      autoScroll.value = true
    }, 100)
  }
}

async function handleDeleteConversation(id) {
  try {
    await ElMessageBox.confirm('确定删除这条对话记录吗？', '确认删除', {
      type: 'warning'
    })
    await deleteHistory(id)

    // 如果删除的是当前对话，清空聊天区
    if (id === store.currentConversationId) {
      clearChatState()
      store.newConversation()
    }

    ElMessage.success('已删除')
    fetchConversations()
  } catch {
    // 用户取消
  }
}

// 暴露给父组件用于处理删除操作
defineExpose({
  handleDeleteConversation
})
</script>

<style scoped>
.chat-page {
  display: flex;
  flex-direction: row;
  height: 100%;
  overflow: hidden;
}

/* 左侧聊天区 — 整体不可滚动，只有 ChatBox 内部滚动 */
.chat-left {
  flex: 1 1 0;
  display: flex;
  flex-direction: column;
  min-width: 0;
  height: 100%;
  overflow: hidden;
  border-right: 1px solid var(--border-color);
}

.chat-bottom {
  flex: 0 0 auto;
}

.thinking-bar {
  padding: 4px 20px;
  background: #fefce8;
  border-top: 1px solid #fde68a;
}

/* 右侧面板 — 内部可滚动 */
.chat-right {
  width: 340px;
  flex: 0 0 auto;
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 16px;
  background: var(--bg-secondary);
}

@media (max-width: 1024px) {
  .chat-right {
    display: none;
  }
  .chat-left {
    border-right: none;
  }
}
</style>
