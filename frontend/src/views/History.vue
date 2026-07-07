<template>
  <div class="history-page">
    <div class="history-header">
      <h2 class="page-title">
        <el-icon><Clock /></el-icon>
        历史记录
      </h2>
      <div class="header-actions">
        <el-button
          type="danger"
          plain
          size="small"
          :disabled="!records.length"
          @click="handleClearAll"
        >
          <el-icon><Delete /></el-icon>
          清空全部
        </el-button>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="history-loading">
      <Loading text="加载中..." />
    </div>

    <!-- 空状态 -->
    <div v-else-if="conversations.length === 0" class="history-empty">
      <el-empty description="暂无历史记录">
        <router-link to="/chat">
          <el-button type="primary">开始对话</el-button>
        </router-link>
      </el-empty>
    </div>

    <!-- 记录列表 -->
    <div v-else class="history-list">
      <el-card
        v-for="conv in conversations"
        :key="conv.id"
        shadow="never"
        class="history-card"
        @click="goToChat(conv.id)"
      >
        <div class="record-header">
          <span class="record-time">{{ formatDate(conv.updated_at) }}</span>
          <el-button
            text
            type="danger"
            size="small"
            @click.stop="handleDelete(conv.id)"
          >
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
        <div class="record-title">
          <el-tag type="info" size="small" effect="plain">问题</el-tag>
          <p>{{ conv.title }}</p>
        </div>
        <div class="record-last-message">
          <el-tag type="success" size="small" effect="plain">最新回复</el-tag>
          <p>{{ conv.last_message || '-' }}</p>
        </div>
        <div class="record-meta">
          <span>消息数: {{ conv.message_count }}</span>
        </div>
      </el-card>
    </div>

    <!-- 分页 -->
    <div v-if="total > pageSize" class="history-pagination">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next"
        @current-change="fetchRecords"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getHistory, deleteHistory, clearHistory } from '@/api/history.js'
import Loading from '@/components/Loading.vue'

const router = useRouter()

const conversations = ref([])
const loading = ref(true)
const currentPage = ref(1)
const total = ref(0)
const pageSize = 10

onMounted(() => fetchRecords())

async function fetchRecords() {
  loading.value = true
  try {
    const res = await getHistory({ page: currentPage.value, page_size: pageSize })
    conversations.value = res.conversations || []
    total.value = res.total || 0
    currentPage.value = res.page || 1
  } catch {
    conversations.value = []
  } finally {
    loading.value = false
  }
}

function goToChat(conversationId) {
  router.push({ path: '/chat', query: { conversation_id: conversationId } })
}

async function handleDelete(id) {
  try {
    await ElMessageBox.confirm('确定删除这条记录吗？', '确认删除', {
      type: 'warning'
    })
    await deleteHistory(id)
    ElMessage.success('删除成功')
    fetchRecords()
  } catch {
    // 用户取消
  }
}

async function handleClearAll() {
  try {
    await ElMessageBox.confirm('确定要清空所有历史记录吗？此操作不可恢复。', '危险操作', {
      type: 'error',
      confirmButtonText: '确定清空',
      cancelButtonText: '取消'
    })
    await clearHistory()
    ElMessage.success('已清空全部记录')
    records.value = []
    total.value = 0
  } catch {
    // 用户取消
  }
}

function formatDate(date) {
  if (!date) return '-'
  const d = new Date(date)
  return d.toLocaleString('zh-CN')
}
</script>

<style scoped>
.history-page {
  max-width: 900px;
  margin: 0 auto;
  padding: 24px;
}

.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 8px;
}

.history-loading {
  padding: 60px;
}

.history-empty {
  padding: 40px;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.history-card {
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
}

.history-card :deep(.el-card__body) {
  padding: 18px;
}

.record-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.record-time {
  font-size: 12px;
  color: var(--text-secondary);
}

.record-title,
.record-last-message {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 10px;
}

.record-title p,
.record-last-message p {
  font-size: 14px;
  color: var(--text-primary);
  line-height: 1.6;
  flex: 1;
}

.record-meta {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-color);
  font-size: 12px;
  color: var(--text-secondary);
}

.history-pagination {
  display: flex;
  justify-content: center;
  margin-top: 24px;
}
</style>
