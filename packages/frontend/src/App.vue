<script setup lang="ts">
import { ref } from 'vue'
import ChatBox from './components/ChatBox.vue'
import DataSourceManager from './components/DataSourceManager.vue'
import Sidebar from './components/Sidebar.vue'

const currentDataSourceId = ref<string | null>(null)
const sidebarCollapsed = ref(false)

function onDataSourceSelected(id: string | null) {
  currentDataSourceId.value = id
}

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value
}
</script>

<template>
  <div class="flex h-screen w-screen overflow-hidden">
    <!-- Sidebar -->
    <aside
      class="sidebar flex flex-col h-full flex-shrink-0"
      :class="sidebarCollapsed ? 'sidebar-collapsed' : 'sidebar-expanded'"
      :style="{ background: 'var(--sidebar-bg)' }"
    >
      <div class="flex-1 overflow-hidden flex flex-col sidebar-content" :class="{ 'sidebar-content-hidden': sidebarCollapsed }">
        <!-- Sessions -->
        <Sidebar class="flex-1" />
        <!-- Data Sources -->
        <DataSourceManager @select="onDataSourceSelected" />
      </div>
    </aside>

    <!-- Main Area -->
    <main class="flex-1 flex flex-col min-w-0 relative" :style="{ background: 'var(--main-bg)' }">
      <!-- Toggle Button -->
      <button
        @click="toggleSidebar"
        class="btn absolute top-3 left-3 z-50 p-2 rounded-xl hover:bg-white/10"
        :title="sidebarCollapsed ? 'Show sidebar' : 'Hide sidebar'"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 transition-transform duration-300" :class="{ 'rotate-180': !sidebarCollapsed }" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
        </svg>
      </button>

      <!-- Welcome / Chat -->
      <Transition name="fade" mode="out-in">
        <div v-if="!currentDataSourceId" key="welcome" class="flex-1 flex flex-col items-center justify-center px-4">
          <h1 class="text-4xl font-semibold mb-3 tracking-tight">DeepEye</h1>
          <p class="text-[var(--main-text-muted)] text-center max-w-md leading-relaxed">
            Select or create a data source from the sidebar to start analyzing your data.
          </p>
        </div>
        <ChatBox v-else key="chat" :data-source-id="currentDataSourceId" />
      </Transition>
    </main>
  </div>
</template>

<style scoped>
.sidebar {
  transition: width 0.3s var(--ease-out-expo);
  will-change: width;
}
.sidebar-expanded {
  width: 16rem; /* w-64 */
}
.sidebar-collapsed {
  width: 0;
}

.sidebar-content {
  transition: opacity 0.2s ease 0.1s, transform 0.3s var(--ease-out-expo);
}
.sidebar-content-hidden {
  opacity: 0;
  transform: translateX(-8px);
  transition: opacity 0.15s ease, transform 0.15s ease;
}
</style>
