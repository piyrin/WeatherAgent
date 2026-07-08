<template>
  <div class="message-item" :class="[role, { streaming: isStreaming }]">
    <!-- 头像 -->
    <div class="message-avatar">
      <div class="avatar-circle" :class="role">
        <el-icon v-if="role === 'user'" :size="18"><User /></el-icon>
        <el-icon v-else :size="18"><Cpu /></el-icon>
      </div>
    </div>

    <!-- 消息内容 -->
    <div class="message-body">
      <div class="message-role">
        {{ role === 'user' ? '你' : '天气助手' }}
        <span v-if="timestamp" class="message-time">{{ formatTime(timestamp) }}</span>
      </div>
      <div class="message-content" v-html="renderedContent"></div>
      <MapCard v-if="routeData" :route-data="routeData" />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import MapCard from './MapCard.vue'

const props = defineProps({
  role: {
    type: String,
    required: true,
    validator: (v) => ['user', 'assistant'].includes(v)
  },
  content: {
    type: String,
    default: ''
  },
  timestamp: {
    type: [String, Number, Date],
    default: null
  },
  isStreaming: {
    type: Boolean,
    default: false
  },
  routeData: {
    type: Object,
    default: null
  }
})

const renderedContent = computed(() => {
  return props.content
    .replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre class="code-block"><code>$2</code></pre>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
})

function formatTime(time) {
  if (!time) return ''
  const d = new Date(time)
  const h = String(d.getHours()).padStart(2, '0')
  const m = String(d.getMinutes()).padStart(2, '0')
  return `${h}:${m}`
}
</script>

<style scoped>
.message-item {
  display: flex;
  gap: 12px;
  padding: 16px 20px;
  animation: fadeIn 0.3s ease;
}

.message-item.user {
  flex-direction: row-reverse;
}

.message-item.assistant {
  background: var(--primary-light);
}

.message-item.streaming .message-content::after {
  content: '▊';
  animation: blink 1s step-end infinite;
  color: var(--primary-color);
}

@keyframes blink {
  50% { opacity: 0; }
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

/* 头像 */
.avatar-circle {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.avatar-circle.user {
  background: linear-gradient(135deg, #3b82f6, #60a5fa);
  color: #fff;
}

.avatar-circle.assistant {
  background: linear-gradient(135deg, #10b981, #34d399);
  color: #fff;
}

/* 消息体 */
.message-body {
  max-width: 75%;
  min-width: 0;
}

.message-role {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 6px;
}

.message-time {
  font-weight: 400;
  margin-left: 8px;
  opacity: 0.6;
}

.message-content {
  font-size: 14px;
  line-height: 1.7;
  color: var(--text-primary);
  word-break: break-word;
}

.message-content :deep(.code-block) {
  background: #1f2937;
  color: #e5e7eb;
  padding: 12px 16px;
  border-radius: var(--radius-sm);
  margin: 8px 0;
  font-size: 13px;
  overflow-x: auto;
}

.message-content :deep(strong) {
  color: var(--primary-dark);
}

@media (max-width: 768px) {
  .message-body { max-width: 85%; }
  .message-item { padding: 12px 14px; }
}
</style>
