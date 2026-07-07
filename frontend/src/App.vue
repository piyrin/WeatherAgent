<template>
  <div class="app-container">
    <header class="app-header">
      <Navbar />
    </header>
    <div class="app-body">
      <aside v-if="showSidebar" class="app-sidebar">
        <Sidebar
          :conversations="store.conversations"
          :current-id="store.currentConversationId"
          :loading="store.loading"
          @new-chat="onNewChat"
          @select-conversation="onSelectConversation"
          @delete-conversation="onDeleteConversation"
        />
      </aside>
      <main class="app-main" :class="{ 'app-main--locked': showSidebar }">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" ref="currentViewRef" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import Navbar from '@/components/Navbar.vue'
import Sidebar from '@/components/Sidebar.vue'
import { useConversationStore } from '@/stores/conversation.js'

const route = useRoute()
const store = useConversationStore()
const currentViewRef = ref(null)

const showSidebar = computed(() => {
  return route.name === 'Chat'
})

function onNewChat() {
  store.newConversation()
}

function onSelectConversation(id) {
  store.selectConversation(id)
}

function onDeleteConversation(id) {
  currentViewRef.value?.handleDeleteConversation?.(id)
}
</script>

<style scoped>
/* ========== 根容器 — 硬编码 100vh ========== */
.app-container {
  width: 100vw;
  height: 100vh;
  overflow: hidden;
}

/* ========== 顶栏 — 硬编码 60px ========== */
.app-header {
  height: 60px;
  padding: 0;
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  z-index: 100;
  overflow: hidden;
}

/* ========== 主体 — calc 硬编码高度 ========== */
.app-body {
  height: calc(100vh - 60px);
  display: flex;
  flex-direction: row;
  overflow: hidden;
}

/* ========== 侧边栏 — 硬编码高度 + 禁止自身滚动 ========== */
.app-sidebar {
  width: 260px;
  flex-shrink: 0;
  height: 100%;
  overflow: hidden;
  background: #f9fafb;
  border-right: 1px solid #e5e7eb;
}

/* ========== 主区域 ========== */
.app-main {
  flex: 1;
  height: 100%;
  min-width: 0;
  background: #ffffff;
  padding: 0;
  overflow-y: auto;
}

.app-main--locked {
  overflow: hidden;
}

/* ========== 过渡动画 ========== */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
