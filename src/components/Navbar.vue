<template>
  <div class="navbar">
    <div class="navbar-left">
      <router-link to="/" class="logo-link">
        <div class="logo-icon">
          <el-icon :size="24"><Cloudy /></el-icon>
        </div>
        <span class="logo-text">天气出行助手</span>
      </router-link>
    </div>
    <div class="navbar-center">
      <el-menu
        :default-active="activeMenu"
        mode="horizontal"
        :ellipsis="false"
        router
        class="nav-menu"
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
          <span>关于</span>
        </el-menu-item>
      </el-menu>
    </div>
    <div class="navbar-right">
      <el-tag type="info" effect="plain" size="small">LangChain Agent</el-tag>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const activeMenu = computed(() => {
  if (route.path.startsWith('/chat')) return '/chat'
  if (route.path.startsWith('/history')) return '/history'
  if (route.path.startsWith('/about')) return '/about'
  return '/'
})
</script>

<style scoped>
.navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 100%;
  padding: 0 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.navbar-left {
  display: flex;
  align-items: center;
}

.logo-link {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  color: var(--text-primary);
}

.logo-icon {
  width: 38px;
  height: 38px;
  background: linear-gradient(135deg, #3b82f6, #60a5fa);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.logo-text {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.5px;
}

.navbar-center {
  flex: 1;
  display: flex;
  justify-content: center;
}

.nav-menu {
  border-bottom: none !important;
}

.nav-menu .el-menu-item {
  height: 60px;
  line-height: 60px;
  font-size: 14px;
}

.navbar-right {
  display: flex;
  align-items: center;
}

@media (max-width: 768px) {
  .navbar-center {
    display: none;
  }
  .navbar {
    padding: 0 16px;
  }
}
</style>
