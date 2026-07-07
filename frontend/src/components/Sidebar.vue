<template>
  <div class="sidebar">
    <!-- 开启新对话按钮 -->
    <div class="sidebar-header">
      <el-button
        type="primary"
        class="new-chat-btn"
        @click="handleNewChat"
      >
        <el-icon><Plus /></el-icon>
        <span>开启新对话</span>
      </el-button>
    </div>

    <!-- 历史记录列表 -->
    <div class="sidebar-body">
      <div class="history-title">历史记录</div>

      <!-- 加载中 -->
      <div v-if="loading" class="history-loading">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>加载中...</span>
      </div>

      <!-- 空状态 -->
      <div v-else-if="conversations.length === 0" class="history-empty">
        <el-empty
          description="暂无历史记录"
          :image-size="48"
        />
      </div>

      <!-- 记录列表 -->
      <div v-else class="history-list">
        <div
          v-for="conv in conversations"
          :key="conv.id"
          class="history-item"
          :class="{ 'is-active': activeId === conv.id }"
          @click="handleSelect(conv.id)"
        >
          <div class="history-item-content">
            <div class="history-item-preview">{{ getPreview(conv) }}</div>
            <div class="history-item-date">{{ formatDate(conv.updated_at) }}</div>
          </div>
          <el-button
            class="history-item-delete"
            text
            size="small"
            type="danger"
            @click.stop="handleDelete(conv.id)"
          >
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
      </div>
    </div>

    <!-- 底部：后端状态 -->
    <div class="sidebar-footer">
      <div class="status-dot" :class="{ 'is-disconnected': backendStatus !== '已连接' }"></div>
      <span class="status-text">{{ backendStatus }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete, Loading } from '@element-plus/icons-vue'
import { getHistory, deleteHistory } from '@/api/history.js'

const router = useRouter()
const route = useRoute()

const conversations = ref([])
const loading = ref(true)
const backendStatus = ref('检测中...')
const total = ref(0)

// 当前活跃的会话 ID（从路由 query 读取）
const activeId = computed(() => route.query.conversation_id || null)

// 加载历史列表
async function fetchConversations() {
  loading.value = true
  try {
    const res = await getHistory({ page: 1, page_size: 50 })
    conversations.value = res.conversations || []
    total.value = res.total || 0
    backendStatus.value = '已连接'
  } catch {
    conversations.value = []
    backendStatus.value = '未连接'
  } finally {
    loading.value = false
  }
}

// 获取预览文本：优先用 title（非默认值），否则用 last_message
function getPreview(conv) {
  if (conv.title && conv.title !== '新对话') {
    return conv.title.length > 15 ? conv.title.slice(0, 15) + '...' : conv.title
  }
  if (conv.last_message) {
    return conv.last_message.length > 15 ? conv.last_message.slice(0, 15) + '...' : conv.last_message
  }
  return '（空对话）'
}

// 格式化日期
function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const now = new Date()
  const diff = now - d
  const oneDay = 86400000

  if (diff < oneDay) {
    return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  } else if (diff < 2 * oneDay) {
    return '昨天'
  } else if (diff < 7 * oneDay) {
    const days = ['日', '一', '二', '三', '四', '五', '六']
    return '周' + days[d.getDay()]
  } else {
    return `${d.getMonth() + 1}/${d.getDate()}`
  }
}

// 开启新对话
function handleNewChat() {
  router.push('/chat')
}

// 选中历史记录
function handleSelect(conversationId) {
  router.push({ path: '/chat', query: { conversation_id: conversationId } })
}

// 删除历史记录
async function handleDelete(id) {
  try {
    await ElMessageBox.confirm('确定删除这条记录吗？', '确认删除', {
      type: 'warning',
      confirmButtonText: '确定',
      cancelButtonText: '取消',
    })
    await deleteHistory(id)
    ElMessage.success('已删除')
    // 如果删除的是当前活跃会话，跳转到新对话
    if (activeId.value === id) {
      router.push('/chat')
    }
    await fetchConversations()
  } catch {
    // 用户取消
  }
}

// 监听路由变化：刷新历史列表（新对话创建、切换会话等）
watch(
  () => route.fullPath,
  () => {
    if (route.path === '/chat') {
      fetchConversations()
    }
  }
)

onMounted(() => fetchConversations())
</script>

<style scoped>
.sidebar {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

/* ---- 顶部按钮 ---- */
.sidebar-header {
  padding: 12px;
  flex-shrink: 0;
}

.new-chat-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 500;
}

/* ---- 历史区域 ---- */
.sidebar-body {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.history-title {
  font-size: 12px;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 1px;
  padding: 0 16px 8px;
  font-weight: 600;
  flex-shrink: 0;
}

.history-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 24px;
  font-size: 13px;
  color: var(--text-secondary);
}

.history-empty {
  padding: 8px;
}

.history-list {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 0 8px;
}

/* ---- 单条记录 ---- */
.history-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background 0.15s ease;
  margin-bottom: 2px;
  position: relative;
}

.history-item:hover {
  background: #e8f0fe;
}

.history-item.is-active {
  background: var(--primary-light);
}

.history-item-content {
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

.history-item-preview {
  font-size: 13px;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.4;
  margin-bottom: 2px;
}

.history-item-date {
  font-size: 11px;
  color: var(--text-secondary);
}

.history-item-delete {
  opacity: 0;
  transition: opacity 0.15s ease;
  flex-shrink: 0;
  margin-left: 4px;
}

.history-item:hover .history-item-delete {
  opacity: 1;
}

/* ---- 底部状态 ---- */
.sidebar-footer {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 16px;
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
  font-size: 11px;
}
</style>
