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
import { sendMessage } from '@/api/chat.js'
import ChatBox from '@/components/ChatBox.vue'
import InputPanel from '@/components/InputPanel.vue'
import StepTimeline from '@/components/StepTimeline.vue'
import ToolPanel from '@/components/ToolPanel.vue'
import Loading from '@/components/Loading.vue'

const messages = ref([])
const isLoading = ref(false)
const agentSteps = ref([])
const currentStep = ref(0)
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

  // 模拟 Agent 步骤展示
  const mockSteps = ['理解用户问题', '任务规划与分解', '调用天气工具', '调用日期解析工具', '生成最终回答']
  const stepsPerTick = 1200

  isLoading.value = true
  agentSteps.value = []

  // 逐步展示 steps
  let stepIndex = 0
  const stepTimer = setInterval(() => {
    if (stepIndex < mockSteps.length) {
      agentSteps.value = [...agentSteps.value, mockSteps[stepIndex]]
      currentStep.value = stepIndex
      stepIndex++
    } else {
      clearInterval(stepTimer)
    }
  }, stepsPerTick)

  // 添加 AI 占位消息
  addMessage('assistant', '正在分析你的问题...', true)

  try {
    const result = await sendMessage(text)

    // 确保所有步骤展示完毕
    clearInterval(stepTimer)
    agentSteps.value = result.steps || mockSteps
    currentStep.value = agentSteps.value.length - 1

    // 更新工具调用
    toolCalls.value = result.tools || []

    // 等一小段让用户看到最后步骤
    await new Promise(r => setTimeout(r, 400))

    // 更新最终回答
    updateLastMessage(result.answer || '抱歉，我暂时无法回答这个问题。')
    const lastMsg = messages.value[messages.value.length - 1]
    if (lastMsg) lastMsg.isStreaming = false

  } catch (error) {
    clearInterval(stepTimer)
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
  currentStep.value = 0
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
  flex: 1;
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
