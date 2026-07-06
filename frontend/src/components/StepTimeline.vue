<template>
  <div class="step-timeline">
    <h4 class="panel-title">
      <el-icon><Connection /></el-icon>
      Agent 执行过程
    </h4>

    <div v-if="steps.length === 0" class="timeline-empty">
      <el-icon :size="20"><Clock /></el-icon>
      <p>发送消息后将在此展示Agent执行步骤</p>
    </div>

    <el-timeline v-else>
      <el-timeline-item
        v-for="(step, index) in steps"
        :key="index"
        :timestamp="getTimestamp(index)"
        :color="getColor(index)"
        :hollow="index === steps.length - 1 && isRunning"
        :type="index === steps.length - 1 && isRunning ? 'success' : 'primary'"
        :icon="index === steps.length - 1 && isRunning ? Loading : null"
        placement="top"
      >
        <div class="timeline-step" :class="{ active: index <= currentStep }">
          <span class="step-dot" v-if="index < steps.length - 1"></span>
          {{ step }}
        </div>
      </el-timeline-item>
    </el-timeline>
  </div>
</template>

<script setup>
defineProps({
  steps: {
    type: Array,
    default: () => []
  },
  currentStep: {
    type: Number,
    default: 0
  },
  isRunning: {
    type: Boolean,
    default: false
  }
})

function getTimestamp(index) {
  if (index === 0) return '开始'
  return `步骤 ${index + 1}`
}

function getColor(index) {
  const colors = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b']
  return colors[index % colors.length]
}
</script>

<style scoped>
.step-timeline {
  background: #fff;
  border-radius: var(--radius);
  border: 1px solid var(--border-color);
  padding: 18px;
  margin-bottom: 16px;
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

.timeline-empty {
  text-align: center;
  padding: 24px 12px;
  color: var(--text-secondary);
  font-size: 13px;
}

.timeline-empty .el-icon {
  color: #d1d5db;
  margin-bottom: 8px;
}

.timeline-step {
  font-size: 13px;
  color: var(--text-secondary);
  transition: color 0.3s;
}

.timeline-step.active {
  color: var(--text-primary);
  font-weight: 600;
}

.step-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--primary-color);
  margin-right: 6px;
  vertical-align: middle;
}
</style>
