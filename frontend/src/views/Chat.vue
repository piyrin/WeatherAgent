<template>
  <div class="chat-page">
    <!-- 左侧：聊天区 -->
    <div class="chat-left">
      <ChatBox
        :messages="messages"
        @clear="clearMessages"
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
import { ref, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { sendMessage } from '@/api/chat.js'
import { getConversationDetail } from '@/api/history.js'
import ChatBox from '@/components/ChatBox.vue'
import InputPanel from '@/components/InputPanel.vue'
import StepTimeline from '@/components/StepTimeline.vue'
import ToolPanel from '@/components/ToolPanel.vue'
import Loading from '@/components/Loading.vue'

const route = useRoute()
const router = useRouter()

const messages = ref([])
const isLoading = ref(false)
const agentSteps = ref([])
const currentStep = ref(-1)
const toolCalls = ref([])
const currentConversationId = ref(null)

let messageId = 0

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

  addMessage('assistant', '正在分析你的问题...', true)

  try {
    const result = await sendMessage(text, currentConversationId.value)

    // 首次对话时后端返回新的 conversation_id，保存下来
    if (result.conversation_id && !currentConversationId.value) {
      currentConversationId.value = result.conversation_id
      // 同步到 URL query，使侧边栏高亮当前会话
      router.replace({ path: '/chat', query: { conversation_id: result.conversation_id } })
    }

    agentSteps.value = result.steps || []
    currentStep.value = result.steps ? result.steps.length - 1 : -1
    toolCalls.value = result.tools || []

    updateLastMessage(result.answer || result.message || '抱歉，我暂时无法回答这个问题。')
    const lastMsg = messages.value[messages.value.length - 1]
    if (lastMsg) lastMsg.isStreaming = false

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

function clearMessages() {
  messages.value = []
  agentSteps.value = []
  toolCalls.value = []
  currentStep.value = -1
  messageId = 0
  currentConversationId.value = null
  if (route.query.conversation_id) {
    router.push('/chat')
  }
  ElMessage.success('已清空对话')
}

// 从路由 query 加载历史会话
async function loadConversation(conversationId) {
  if (!conversationId) return
  try {
    const detail = await getConversationDetail(conversationId)
    if (detail && detail.messages) {
      messages.value = detail.messages.map(msg => ({
        id: ++messageId,
        role: msg.role,
        content: msg.content,
        timestamp: msg.created_at,
        isStreaming: false,
      }))
      currentConversationId.value = conversationId
    }
  } catch {
    ElMessage.warning('加载历史会话失败')
    router.push('/chat')
  }
}

// 监听路由 query 变化
watch(
  () => route.query.conversation_id,
  (newId) => {
    if (newId && newId !== currentConversationId.value) {
      loadConversation(newId)
    } else if (!newId && currentConversationId.value) {
      // 切换到新对话
      clearMessages()
    }
  }
)

onMounted(() => {
  const convId = route.query.conversation_id
  if (convId) {
    loadConversation(convId)
  }
})
</script>

<style scoped>
.chat-page {
  display: flex;
  height: 100%;
  overflow: hidden;
}

.chat-left {
  flex: 1;
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--border-color);
  overflow: hidden;
  min-height: 0;
}

.chat-bottom {
  flex-shrink: 0;
}

.thinking-bar {
  padding: 4px 20px;
  background: #fefce8;
  border-top: 1px solid #fde68a;
  flex-shrink: 0;
}

.chat-right {
  width: 340px;
  flex-shrink: 0;
  background: var(--bg-secondary);
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
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
