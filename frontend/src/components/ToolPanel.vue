<template>
  <div class="tool-panel">
    <h4 class="panel-title">
      <el-icon><Setting /></el-icon>
      工具调用记录
    </h4>

    <div v-if="tools.length === 0" class="panel-empty">
      <el-icon :size="20"><FolderOpened /></el-icon>
      <p>暂无工具调用记录</p>
    </div>

    <TransitionGroup name="tool-list" tag="div" class="tool-list">
      <el-card
        v-for="(tool, index) in tools"
        :key="index"
        shadow="never"
        class="tool-card"
      >
        <template #header>
          <div class="tool-card-header">
            <el-tag
              :type="getTagType(index)"
              size="small"
              effect="plain"
            >{{ tool.name || 'Tool' }}</el-tag>
            <span class="tool-badge">调用 #{{ index + 1 }}</span>
          </div>
        </template>

        <div class="tool-detail">
          <div class="tool-section">
            <span class="tool-label">输入参数</span>
            <div class="tool-value input-value">{{ formatValue(tool.input) }}</div>
          </div>
          <el-divider class="tool-divider" />
          <div class="tool-section">
            <span class="tool-label">返回结果</span>
            <div class="tool-value output-value">{{ formatValue(tool.output) }}</div>
          </div>
        </div>
      </el-card>
    </TransitionGroup>
  </div>
</template>

<script setup>
defineProps({
  tools: {
    type: Array,
    default: () => []
  }
})

function getTagType(index) {
  const types = ['primary', 'success', 'warning', 'info', 'danger']
  return types[index % types.length]
}

function formatValue(value) {
  if (!value) return '-'
  if (typeof value === 'object') return JSON.stringify(value, null, 2)
  return String(value)
}
</script>

<style scoped>
.tool-panel {
  background: #fff;
  border-radius: var(--radius);
  border: 1px solid var(--border-color);
  padding: 18px;
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 16px;
}

.panel-empty {
  text-align: center;
  padding: 24px 12px;
  color: var(--text-secondary);
  font-size: 13px;
}

.panel-empty .el-icon {
  color: #d1d5db;
  margin-bottom: 8px;
}

.tool-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.tool-card {
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
}

.tool-card :deep(.el-card__header) {
  padding: 10px 14px;
  background: #fafafa;
  border-bottom: 1px solid var(--border-color);
}

.tool-card :deep(.el-card__body) {
  padding: 12px 14px;
}

.tool-card-header {
  display: flex;
  align-items: center;
  gap: 10px;
}

.tool-badge {
  font-size: 11px;
  color: var(--text-secondary);
}

.tool-detail {
  font-size: 13px;
}

.tool-section {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.tool-label {
  font-size: 11px;
  color: var(--text-secondary);
  font-weight: 600;
  text-transform: uppercase;
}

.tool-value {
  color: var(--text-primary);
  line-height: 1.5;
}

.input-value {
  color: var(--primary-color);
}

.output-value {
  color: var(--success-color);
}

.tool-divider {
  margin: 10px 0;
}

/* 动画 */
.tool-list-enter-active {
  transition: all 0.4s ease;
}

.tool-list-enter-from {
  opacity: 0;
  transform: translateX(20px);
}
</style>
