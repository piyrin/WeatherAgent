<template>
  <div class="chat-box" ref="chatContainer">
    <!-- 空状态 -->
    <div v-if="messages.length === 0" class="chat-empty">
      <div class="empty-icon">
        <el-icon :size="48"><ChatDotRound /></el-icon>
      </div>
      <h3>开始对话</h3>
      <p class="empty-hint">输入天气或出行问题，例如：</p>
      <div class="example-chips">
        <span
          v-for="example in examples"
          :key="example"
          class="example-chip"
          @click="$emit('example-click', example)"
        >{{ example }}</span>
      </div>
    </div>

    <!-- 消息列表 -->
    <div v-else class="chat-messages">
      <MessageItem
        v-for="msg in messages"
        :key="msg.id"
        :role="msg.role"
        :content="msg.content"
        :timestamp="msg.timestamp"
        :is-streaming="msg.isStreaming || false"
      />
      <div ref="scrollAnchor"></div>
    </div>

    <!-- 清空按钮 -->
    <div v-if="messages.length > 0" class="chat-actions">
      <el-button text size="small" type="info" @click="$emit('clear')">
        <el-icon><Delete /></el-icon>
        清空对话
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import MessageItem from './MessageItem.vue'

const props = defineProps({
  messages: {
    type: Array,
    default: () => []
  }
})

defineEmits(['clear', 'example-click'])

const chatContainer = ref(null)
const scrollAnchor = ref(null)

const examples = [
  '明天去武汉大学，需要带伞吗？',
  '北京今天天气怎么样？',
  '周末去爬长城合适吗？',
  '上海未来三天会下雨吗？'
]

function scrollToBottom() {
  nextTick(() => {
    scrollAnchor.value?.scrollIntoView({ behavior: 'smooth' })
  })
}

watch(() => props.messages.length, scrollToBottom)
watch(() => props.messages, scrollToBottom, { deep: true })
</script>

<style scoped>
.chat-box {
  flex: 1;
  overflow-y: auto;
  position: relative;
}

/* 空状态 */
.chat-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 40px 20px;
}

.empty-icon {
  width: 80px;
  height: 80px;
  border-radius: 20px;
  background: var(--primary-light);
  color: var(--primary-color);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
}

.chat-empty h3 {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 8px;
}

.empty-hint {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 16px;
}

.example-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  max-width: 480px;
}

.example-chip {
  padding: 8px 16px;
  border: 1px solid var(--border-color);
  border-radius: 20px;
  font-size: 13px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.example-chip:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
  background: var(--primary-light);
}

/* 消息区域 */
.chat-messages {
  min-height: 100%;
}

.chat-actions {
  text-align: center;
  padding: 8px;
}
</style>
