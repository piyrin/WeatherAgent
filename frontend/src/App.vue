<template>
  <div class="app-container">
    <el-header height="60px" class="app-header">
      <Navbar />
    </el-header>
    <div class="app-body">
      <el-aside v-if="showSidebar" width="220px" class="app-sidebar">
        <Sidebar />
      </el-aside>
      <router-view class="app-main" />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import Navbar from '@/components/Navbar.vue'
import Sidebar from '@/components/Sidebar.vue'

const route = useRoute()
const showSidebar = computed(() => route.name === 'Chat')
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body {
  height: 100%;
  overflow: hidden;
}

#app {
  height: 100%;
  overflow: hidden;
}
</style>

<style scoped>
.app-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.app-header {
  height: 60px;
  padding: 0;
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  flex-shrink: 0;
}

.app-body {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.app-sidebar {
  background: #f9fafb;
  border-right: 1px solid #e5e7eb;
  width: 220px;
  flex-shrink: 0;
  overflow: hidden;
}

.app-main {
  flex: 1;
  overflow: hidden;
}
</style>
