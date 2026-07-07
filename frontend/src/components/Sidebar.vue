<template>
  <div class="sidebar">
    <!-- 开启新对话按钮 -->
    <div class="sidebar-top">
      <el-button
        type="primary"
        :icon="Plus"
        class="new-chat-btn"
        @click="$emit('new-chat')"
      >
        开启新对话
      </el-button>
    </div>

    <!-- 分隔线 -->
    <div class="sidebar-divider">
      <span class="divider-text">历史记录</span>
    </div>

    <!-- 历史记录列表 -->
    <div class="history-list" ref="historyListRef">
      <!-- 加载中 -->
      <div v-if="loading" class="history-loading">
        <el-icon class="is-loading" :size="18"><Loading /></el-icon>
        <span>加载中...</span>
      </div>

      <!-- 空状态 -->
      <div v-else-if="conversations.length === 0" class="history-empty">
        <el-icon :size="18"><ChatLineSquare /></el-icon>
        <p>暂无历史记录</p>
      </div>

      <!-- 记录列表 -->
      <div
        v-for="conv in conversations"
        :key="conv.id"
        class="history-item"
        :class="{ 'is-active': conv.id === currentId }"
        @click="$emit('select-conversation', conv.id)"
      >
        <div class="history-item-icon">
          <el-icon :size="14"><ChatDotSquare /></el-icon>
        </div>
        <div class="history-item-content">
          <div class="history-item-title">
            {{ getDisplayTitle(conv) }}
          </div>
          <div class="history-item-meta">
            <span class="history-item-date">{{ formatDate(conv.created_at) }}</span>
            <span class="history-item-count">{{ conv.message_count || 0 }} 条消息</span>
          </div>
        </div>
        <el-button
          class="history-item-delete"
          text
          size="small"
          type="danger"
          :icon="Delete"
          @click.stop="$emit('delete-conversation', conv.id)"
        />
      </div>
    </div>

    <!-- 底部：后端状态 -->
    <div class="sidebar-footer">
      <div class="status-dot" :class="{ 'is-disconnected': backendStatus !== '已连接' }"></div>
      <span class="status-text">后端：{{ backendStatus }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Plus, Delete, Loading, ChatLineSquare, ChatDotSquare } from '@element-plus/icons-vue'
import { getHistory } from '@/api/history.js'

const props = defineProps({
  conversations: {
    type: Array,
    default: () => []
  },
  currentId: {
    type: String,
    default: null
  },
  loading: {
    type: Boolean,
    default: false
  }
})

defineEmits(['new-chat', 'select-conversation', 'delete-conversation'])

const backendStatus = ref('检测中...')
const historyListRef = ref(null)

onMounted(async () => {
  try {
    await getHistory({ page: 1, size: 1 })
    backendStatus.value = '已连接'
  } catch {
    backendStatus.value = '未连接'
  }
})

function getDisplayTitle(conv) {
  // 优先使用 first_user_message，其次 title，最后 fallback
  if (conv.first_user_message) {
    const maxLen = 15
    const text = conv.first_user_message
    return text.length > maxLen ? text.slice(0, maxLen) + '...' : text
  }
  if (conv.title && conv.title !== '新对话') {
    return conv.title
  }
  return '新对话'
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const now = new Date()
  const diffMs = now - d
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

  if (diffDays === 0) {
    const h = String(d.getHours()).padStart(2, '0')
    const m = String(d.getMinutes()).padStart(2, '0')
    return `今天 ${h}:${m}`
  } else if (diffDays === 1) {
    const h = String(d.getHours()).padStart(2, '0')
    const m = String(d.getMinutes()).padStart(2, '0')
    return `昨天 ${h}:${m}`
  } else if (diffDays < 7) {
    return `${diffDays} 天前`
  } else {
    const month = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    return `${month}-${day}`
  }
}
</script>

<style scoped>
.sidebar {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

/* 顶部新对话按钮 */
.sidebar-top {
  padding: 12px;
  flex: 0 0 auto;
}

.new-chat-btn {
  width: 100%;
  border-radius: var(--radius-sm);
  font-weight: 500;
}

/* 分隔线 */
.sidebar-divider {
  padding: 0 14px 8px;
  flex: 0 0 auto;
}

.divider-text {
  font-size: 11px;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  font-weight: 600;
}

/* 历史记录列表 - 可滚动 */
.history-list {
  flex: 1 1 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 0 8px;
  min-height: 0;
}

.history-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 24px 12px;
  font-size: 13px;
  color: var(--text-secondary);
}

.history-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 24px 12px;
  font-size: 13px;
  color: var(--text-secondary);
}

/* 单条历史记录 */
.history-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 10px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background 0.15s ease;
  margin-bottom: 2px;
}

.history-item:hover {
  background: #e8f0fe;
}

.history-item.is-active {
  background: var(--primary-light);
}

.history-item.is-active .history-item-title {
  color: var(--primary-color);
  font-weight: 600;
}

.history-item-icon {
  flex-shrink: 0;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
}

.history-item.is-active .history-item-icon {
  color: var(--primary-color);
}

.history-item-content {
  flex: 1;
  min-width: 0;
}

.history-item-title {
  font-size: 13px;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.4;
}

.history-item-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 2px;
}

.history-item-date {
  font-size: 11px;
  color: var(--text-secondary);
}

.history-item-count {
  font-size: 11px;
  color: #c0c4cc;
}

.history-item-delete {
  opacity: 0;
  transition: opacity 0.15s ease;
  flex-shrink: 0;
}

.history-item:hover .history-item-delete {
  opacity: 1;
}

/* 底部状态 */
.sidebar-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  font-size: 12px;
  color: var(--text-secondary);
  border-top: 1px solid var(--border-color);
  flex-shrink: 0;
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--success-color);
  flex-shrink: 0;
}

.status-dot.is-disconnected {
  background: var(--error-color);
}

.status-text {
  font-size: 12px;
}
</style>
