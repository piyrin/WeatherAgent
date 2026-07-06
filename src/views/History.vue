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
    <div v-else-if="records.length === 0" class="history-empty">
      <el-empty description="暂无历史记录">
        <router-link to="/chat">
          <el-button type="primary">开始对话</el-button>
        </router-link>
      </el-empty>
    </div>

    <!-- 记录列表 -->
    <div v-else class="history-list">
      <el-card
        v-for="record in records"
        :key="record.id"
        shadow="never"
        class="history-card"
      >
        <div class="record-header">
          <span class="record-time">{{ formatDate(record.timestamp) }}</span>
          <el-button
            text
            type="danger"
            size="small"
            @click="handleDelete(record.id)"
          >
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
        <div class="record-question">
          <el-tag type="info" size="small" effect="plain">问题</el-tag>
          <p>{{ record.question }}</p>
        </div>
        <div class="record-answer">
          <el-tag type="success" size="small" effect="plain">回答</el-tag>
          <p>{{ record.answer }}</p>
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
import { ElMessage, ElMessageBox } from 'element-plus'
import { getHistory, deleteHistory, clearHistory } from '@/api/history.js'
import Loading from '@/components/Loading.vue'

const records = ref([])
const loading = ref(true)
const currentPage = ref(1)
const total = ref(0)
const pageSize = 10

onMounted(() => fetchRecords())

async function fetchRecords() {
  loading.value = true
  try {
    const res = await getHistory({ page: currentPage.value, size: pageSize })
    records.value = res.records || []
    total.value = res.total || 0
  } catch {
    records.value = []
  } finally {
    loading.value = false
  }
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

.record-question,
.record-answer {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 10px;
}

.record-question p,
.record-answer p {
  font-size: 14px;
  color: var(--text-primary);
  line-height: 1.6;
  flex: 1;
}

.history-pagination {
  display: flex;
  justify-content: center;
  margin-top: 24px;
}
</style>
