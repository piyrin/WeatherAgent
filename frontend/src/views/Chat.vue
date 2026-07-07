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
import { ref, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
// 当前使用 Mock 服务进行开发和演示
// 当后端开发完成后，只需将下面的 import 改为：
//   import { sendMessage } from '@/api/chat.js'
// 无需修改其他代码
import { sendMessageMock } from '@/mock/chatMock.js'
import ChatBox from '@/components/ChatBox.vue'
import InputPanel from '@/components/InputPanel.vue'
import StepTimeline from '@/components/StepTimeline.vue'
import ToolPanel from '@/components/ToolPanel.vue'
import Loading from '@/components/Loading.vue'

const messages = ref([])
const isLoading = ref(false)
const agentSteps = ref([])
const currentStep = ref(-1)
const toolCalls = ref([])

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

  // 添加 AI 占位消息
  addMessage('assistant', '正在分析你的问题...', true)

  try {
    // 使用 Mock 服务，传入 onStepUpdate 回调实现步骤的流式更新
    // 当后端完成后，替换为：
    //   const result = await sendMessage(text)
    //   agentSteps.value = result.steps || []
    //   toolCalls.value = result.tools || []
    //   updateLastMessage(result.answer)

    const result = await sendMessageMock(text, (updatedSteps) => {
      // 此回调在 Mock 服务中每个步骤执行时被调用
      // 用于实现 Timeline 的实时更新效果
      agentSteps.value = updatedSteps
      currentStep.value = updatedSteps.findIndex(s => s.status === 'running')
    })

    // 更新完整结果
    agentSteps.value = result.steps || []
    currentStep.value = result.steps ? result.steps.length - 1 : -1
    toolCalls.value = result.tools || []

    // 更新最终回答
    updateLastMessage(result.answer || '抱歉，我暂时无法回答这个问题。')
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
  ElMessage.success('已清空对话')
}
</script>

<style scoped>
.chat-page {
  display: flex;
  height: 100%;
}

/* 左侧聊天区 */
.chat-left {
  flex:1;
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--border-color);
  min-width: 0;
}

.chat-bottom {
  flex-shrink: 0;
}

.thinking-bar {
  padding: 4px 20px;
  background: #fefce8;
  border-top: 1px solid #fde68a;
}

/* 右侧面板 */
.chat-right {
  width: 340px;
  flex-shrink: 0;
  padding: 16px;
  overflow-y: auto;
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
