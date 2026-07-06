<template>
  <div class="sidebar">
    <div class="sidebar-title">导航菜单</div>
    <el-menu
      :default-active="activeMenu"
      router
      class="sidebar-menu"
    >
      <el-menu-item index="/chat">
        <el-icon><ChatDotRound /></el-icon>
        <span>智能聊天</span>
      </el-menu-item>
      <el-menu-item index="/history">
        <el-icon><Clock /></el-icon>
        <span>历史记录</span>
      </el-menu-item>
      <el-menu-item index="/about">
        <el-icon><InfoFilled /></el-icon>
        <span>关于项目</span>
      </el-menu-item>
    </el-menu>

    <div class="sidebar-footer">
      <div class="status-dot"></div>
      <span class="status-text">后端服务：{{ backendStatus }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getHistory } from '@/api/history.js'

const route = useRoute()
const backendStatus = ref('检测中...')

const activeMenu = computed(() => {
  if (route.path.startsWith('/chat')) return '/chat'
  if (route.path.startsWith('/history')) return '/history'
  if (route.path.startsWith('/about')) return '/about'
  return '/chat'
})

onMounted(async () => {
  try {
    await getHistory({ page: 1, size: 1 })
    backendStatus.value = '已连接'
  } catch {
    backendStatus.value = '未连接'
  }
})
</script>

<style scoped>
.sidebar {
  padding: 16px 12px;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.sidebar-title {
  font-size: 12px;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 1px;
  padding: 0 12px 12px;
  font-weight: 600;
}

.sidebar-menu {
  border-right: none !important;
  flex: 1;
}

.sidebar-menu .el-menu-item {
  border-radius: var(--radius-sm);
  margin-bottom: 2px;
  height: 44px;
  line-height: 44px;
}

.sidebar-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  font-size: 13px;
  color: var(--text-secondary);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--success-color);
  flex-shrink: 0;
}

.status-text {
  font-size: 12px;
}
</style>
