<template>
  <div class="step-timeline">
    <h4 class="panel-title">
      <el-icon><Connection /></el-icon>
      Agent 执行过程
    </h4>

    <div v-if="normalizedSteps.length === 0" class="timeline-empty">
      <el-icon :size="20"><Clock /></el-icon>
      <p>发送消息后将在此展示Agent执行步骤</p>
    </div>

    <el-timeline v-else>
      <el-timeline-item
        v-for="(step, index) in normalizedSteps"
        :key="step.id || index"
        :timestamp="getTimestamp(step, index)"
        :color="getStatusColor(step.status)"
        :hollow="step.status === 'running'"
        :type="getTimelineType(step.status)"
        :icon="getStepIcon(step)"
        placement="top"
      >
        <div class="timeline-step" :class="`status-${step.status}`">
          <!-- 步骤名称 -->
          <span class="step-name">{{ step.name }}</span>

          <!-- 工具信息 -->
          <div v-if="step.toolName" class="step-tool">
            <el-tag size="small" :type="getToolTagType(step.status)" effect="plain">
              <el-icon v-if="step.status === 'running'" class="is-loading"><Loading /></el-icon>
              {{ step.toolName }}
            </el-tag>
            <span v-if="step.retryCount > 0" class="retry-badge">重试 {{ step.retryCount }} 次</span>
          </div>

          <!-- 工具输入输出（可折叠） -->
          <div v-if="step.toolInput || step.toolOutput" class="step-detail">
            <el-collapse v-model="expandedSteps" class="step-collapse">
              <el-collapse-item
                v-if="step.toolInput"
                title="输入参数"
                :name="`${index}-input`"
              >
                <pre class="detail-code">{{ formatJson(step.toolInput) }}</pre>
              </el-collapse-item>
              <el-collapse-item
                v-if="step.toolOutput"
                title="返回结果"
                :name="`${index}-output`"
              >
                <pre class="detail-code">{{ formatJson(step.toolOutput) }}</pre>
              </el-collapse-item>
            </el-collapse>
          </div>

          <!-- 错误信息 -->
          <div v-if="step.error" class="step-error">
            <el-alert type="error" :closable="false" show-icon>
              {{ step.error }}
            </el-alert>
          </div>
        </div>
      </el-timeline-item>
    </el-timeline>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Loading, Check, Warning, RefreshRight } from '@element-plus/icons-vue'

const props = defineProps({
  // steps 支持两种格式：
  // 1. 简化格式（向后兼容）：string[] -> 自动转换为 Step 对象
  // 2. 完整格式：Step[]
  // Step 对象结构：
  //   - id?: string
  //   - name: string           // 步骤显示名称
  //   - status?: 'pending' | 'running' | 'completed' | 'failed' | 'retrying'
  //   - type?: 'understand' | 'plan' | 'tool_call' | 'observe' | 'answer' | string
  //   - toolName?: string      // 工具名称（type=tool_call 时）
  //   - toolInput?: any       // 工具输入
  //   - toolOutput?: any      // 工具输出
  //   - error?: string         // 错误信息
  //   - retryCount?: number    // 重试次数
  steps: {
    type: Array,
    default: () => []
  },
  currentStep: {
    type: Number,
    default: -1
  },
  isRunning: {
    type: Boolean,
    default: false
  }
})

const expandedSteps = ref([])

// 标准化 steps：将 string[] 转换为 Step 对象（向后兼容）
const normalizedSteps = computed(() => {
  if (!props.steps || props.steps.length === 0) return []
  return props.steps.map((step, index) => {
    if (typeof step === 'string') {
      // 简化格式：根据字符串内容推断状态和类型
      return {
        name: step,
        status: index < props.currentStep ? 'completed'
                : index === props.currentStep ? (props.isRunning ? 'running' : 'completed')
                : 'pending',
        type: inferTypeFromName(step)
      }
    }
    // 完整格式：确保有 status
    return {
      status: 'completed',
      type: 'unknown',
      ...step,
      status: step.status || (index < props.currentStep ? 'completed'
                : index === props.currentStep ? (props.isRunning ? 'running' : 'completed')
                : 'pending')
    }
  })
})

function inferTypeFromName(name) {
  if (/理解|理解用户|分析/.test(name)) return 'understand'
  if (/规划|计划|分解/.test(name)) return 'plan'
  if (/调用|工具|tool/i.test(name)) return 'tool_call'
  if (/观察|结果|观察结果/.test(name)) return 'observe'
  if (/生成|回答|回复|总结/.test(name)) return 'answer'
  return 'unknown'
}

function getTimestamp(step, index) {
  if (index === 0) return '开始'
  const statusMap = {
    'running': '执行中',
    'completed': '完成',
    'failed': '失败',
    'retrying': '重试中'
  }
  return statusMap[step.status] || `步骤 ${index + 1}`
}

function getStatusColor(status) {
  const colorMap = {
    'pending': '#d1d5db',
    'running': '#3b82f6',
    'completed': '#10b981',
    'failed': '#ef4444',
    'retrying': '#f59e0b'
  }
  return colorMap[status] || '#d1d5db'
}

function getTimelineType(status) {
  if (status === 'running') return 'primary'
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'danger'
  if (status === 'retrying') return 'warning'
  return 'info'
}

function getStepIcon(step) {
  if (step.status === 'running') return Loading
  if (step.status === 'completed') return Check
  if (step.status === 'failed') return Warning
  if (step.status === 'retrying') return RefreshRight
  return null
}

function getToolTagType(status) {
  const typeMap = {
    'running': 'primary',
    'completed': 'success',
    'failed': 'danger',
    'retrying': 'warning'
  }
  return typeMap[status] || 'info'
}

function formatJson(value) {
  if (value === null || value === undefined) return '-'
  if (typeof value === 'string') {
    try { return JSON.stringify(JSON.parse(value), null, 2) }
    catch (e) { return value }
  }
  if (typeof value === 'object') return JSON.stringify(value, null, 2)
  return String(value)
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
}

.step-name {
  font-weight: 500;
  color: var(--text-primary);
}

.step-tool {
  margin-top: 6px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.retry-badge {
  font-size: 11px;
  color: #f59e0b;
  background: #fef3c7;
  padding: 1px 6px;
  border-radius: 10px;
}

.step-detail {
  margin-top: 8px;
}

.step-collapse {
  border: none;
}

.step-collapse :deep(.el-collapse-item__header) {
  font-size: 12px;
  color: var(--text-secondary);
  padding: 0;
  height: 28px;
  line-height: 28px;
  background: transparent;
}

.step-collapse :deep(.el-collapse-item__content) {
  padding: 8px 0;
}

.detail-code {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 12px;
  line-height: 1.5;
  overflow-x: auto;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
}

.step-error {
  margin-top: 8px;
}

/* 状态样式 */
.status-running .step-name {
  color: #3b82f6;
}

.status-completed .step-name {
  color: #10b981;
}

.status-failed .step-name {
  color: #ef4444;
}

.status-retrying .step-name {
  color: #f59e0b;
}
</style>
