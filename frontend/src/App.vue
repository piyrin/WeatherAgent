<template>
  <div class="app-container">
    <el-container>
      <el-header height="60px" class="app-header">
        <Navbar />
      </el-header>
      <el-container class="app-body">
        <el-aside v-if="showSidebar" width="220px" class="app-sidebar">
          <Sidebar />
        </el-aside>
        <el-main class="app-main">
          <router-view v-slot="{ Component }">
            <transition name="fade" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import Navbar from '@/components/Navbar.vue'
import Sidebar from '@/components/Sidebar.vue'

const route = useRoute()

const showSidebar = computed(() => {
  return route.name !== 'Home'
})
</script>

<style scoped>
.app-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  padding: 0;
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  z-index: 100;
}

.app-body {
  flex: 1;
  overflow: hidden;
}

.app-sidebar {
  background: #f9fafb;
  border-right: 1px solid #e5e7eb;
  overflow-y: auto;
}

.app-main {
  background: #ffffff;
  padding: 0;
  overflow-y: auto;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
