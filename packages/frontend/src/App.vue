<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import ChatBox from './components/ChatBox.vue'
import DataSourceManager from './components/DataSourceManager.vue'
import Sidebar from './components/Sidebar.vue'
import FileExplorer from './components/FileExplorer.vue'
import FileViewer from './components/FileViewer.vue'
import { useChatStore } from './stores/chat'

const currentDataSourceId = ref<string | null>(null)
const sidebarCollapsed = ref(false)
const filesPanelCollapsed = ref(true)
const selectedFile = ref<string | null>(null)

// Resizable panel ratios (percentage based)
const filesPanelRatio = ref(40) // 40% of main area
const explorerRatio = ref(35)  // 35% of files panel
const MIN_PANEL_RATIO = 25
const MAX_PANEL_RATIO = 60
const MIN_EXPLORER_RATIO = 20
const MAX_EXPLORER_RATIO = 50

// Drag state
const isDraggingPanel = ref(false)
const isDraggingExplorer = ref(false)
const mainAreaRef = ref<HTMLElement | null>(null)
const filesPanelRef = ref<HTMLElement | null>(null)

const chatStore = useChatStore()

// Auto-open files panel when sandbox starts
watch(() => chatStore.sandboxStartedTrigger, () => {
  if (chatStore.sandboxStartedTrigger > 0 && currentDataSourceId.value) {
    const wasCollapsed = filesPanelCollapsed.value
    filesPanelCollapsed.value = false
    // Trigger refresh if we just opened the panel
    if (wasCollapsed) {
      chatStore.notifyFilesChanged()
    }
  }
})

function onDataSourceSelected(id: string | null) {
  currentDataSourceId.value = id
}

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value
}

function toggleFilesPanel() {
  const wasCollapsed = filesPanelCollapsed.value
  filesPanelCollapsed.value = !filesPanelCollapsed.value
  // Trigger a refresh when opening the panel
  if (wasCollapsed) {
    chatStore.notifyFilesChanged()
  }
}

function handleFileSelect(path: string) {
  selectedFile.value = path
}

function closeFileViewer() {
  selectedFile.value = null
}

// Panel resize handlers (percentage based)
function startPanelDrag(_e: MouseEvent) {
  isDraggingPanel.value = true
  document.addEventListener('mousemove', onPanelDrag)
  document.addEventListener('mouseup', stopPanelDrag)
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
}

function onPanelDrag(e: MouseEvent) {
  if (!isDraggingPanel.value || !mainAreaRef.value) return
  const mainRect = mainAreaRef.value.getBoundingClientRect()
  const mainWidth = mainRect.width
  const relativeX = e.clientX - mainRect.left
  const newRatio = ((mainWidth - relativeX) / mainWidth) * 100
  filesPanelRatio.value = Math.max(MIN_PANEL_RATIO, Math.min(MAX_PANEL_RATIO, newRatio))
}

function stopPanelDrag() {
  isDraggingPanel.value = false
  document.removeEventListener('mousemove', onPanelDrag)
  document.removeEventListener('mouseup', stopPanelDrag)
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
}

// Explorer resize handlers (percentage based)
function startExplorerDrag(_e: MouseEvent) {
  isDraggingExplorer.value = true
  document.addEventListener('mousemove', onExplorerDrag)
  document.addEventListener('mouseup', stopExplorerDrag)
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
}

function onExplorerDrag(e: MouseEvent) {
  if (!isDraggingExplorer.value || !filesPanelRef.value) return
  const panelRect = filesPanelRef.value.getBoundingClientRect()
  const panelWidth = panelRect.width
  const relativeX = e.clientX - panelRect.left
  const newRatio = (relativeX / panelWidth) * 100
  explorerRatio.value = Math.max(MIN_EXPLORER_RATIO, Math.min(MAX_EXPLORER_RATIO, newRatio))
}

function stopExplorerDrag() {
  isDraggingExplorer.value = false
  document.removeEventListener('mousemove', onExplorerDrag)
  document.removeEventListener('mouseup', stopExplorerDrag)
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
}

// Check if any dragging is happening
const isDragging = computed(() => isDraggingPanel.value || isDraggingExplorer.value)

const filesPanelStyle = computed(() => ({
  flex: filesPanelCollapsed.value ? '0 0 0' : `0 0 ${filesPanelRatio.value}%`
}))

const explorerStyle = computed(() => ({
  flex: `0 0 ${explorerRatio.value}%`
}))

const chatAreaStyle = computed(() => ({
  flex: filesPanelCollapsed.value ? '1 1 100%' : `1 1 ${100 - filesPanelRatio.value}%`
}))
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
    <main ref="mainAreaRef" class="flex-1 flex min-w-0 relative" :style="{ background: 'var(--main-bg)' }">
      <!-- Chat Area -->
      <div class="flex flex-col min-w-0 relative" :style="chatAreaStyle">
        <!-- Top Control Bar -->
        <div class="absolute top-3 left-3 right-3 z-50 flex items-center justify-between pointer-events-none">
          <!-- Toggle Sidebar Button -->
          <button
            @click="toggleSidebar"
            class="btn p-2 rounded-xl hover:bg-white/10 pointer-events-auto"
            :title="sidebarCollapsed ? 'Show sidebar' : 'Hide sidebar'"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 transition-transform duration-300" :class="{ 'rotate-180': !sidebarCollapsed }" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
            </svg>
          </button>

          <!-- Toggle Files Panel Button -->
          <button
            v-if="currentDataSourceId && chatStore.sessionId"
            @click="toggleFilesPanel"
            class="btn p-2 rounded-xl hover:bg-white/10 pointer-events-auto"
            :title="filesPanelCollapsed ? 'Show files' : 'Hide files'"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
            </svg>
          </button>
        </div>

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
      </div>

      <!-- Files Panel -->
      <aside
        v-if="currentDataSourceId && chatStore.sessionId"
        ref="filesPanelRef"
        class="files-panel flex relative"
        :class="{ 'no-transition': isDragging }"
        :style="filesPanelStyle"
      >
        <!-- Panel Resize Handle (left edge) -->
        <div
          v-if="!filesPanelCollapsed"
          class="resize-handle-panel"
          :class="{ 'resize-active': isDraggingPanel }"
          @mousedown="startPanelDrag"
        ></div>

        <div class="files-content flex h-full flex-1 overflow-hidden" :class="{ 'files-content-hidden': filesPanelCollapsed }">
          <!-- File Explorer -->
          <div class="h-full relative min-w-0" :class="{ 'no-transition': isDragging }" :style="explorerStyle">
            <FileExplorer
              :session-id="chatStore.sessionId"
              @select-file="handleFileSelect"
            />
            <!-- Explorer Resize Handle -->
            <div
              class="resize-handle-explorer"
              :class="{ 'resize-active': isDraggingExplorer }"
              @mousedown="startExplorerDrag"
            ></div>
          </div>

          <!-- File Viewer -->
          <div class="flex-1 h-full min-w-0 border-l border-[#3c3c3c]">
            <FileViewer
              :session-id="chatStore.sessionId"
              :file-path="selectedFile"
              @close="closeFileViewer"
            />
          </div>
        </div>
      </aside>
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

.files-panel {
  background: #1e1e1e;
  border-left: 1px solid #3c3c3c;
  overflow: hidden;
  transition: flex 0.25s ease;
}

.files-panel.no-transition,
.files-panel.no-transition .files-content {
  transition: none !important;
}

.files-content {
  transition: opacity 0.2s ease;
}
.files-content-hidden {
  opacity: 0;
  pointer-events: none;
}

/* Panel resize handle (left edge of the entire panel) */
.resize-handle-panel {
  position: absolute;
  left: -3px;
  top: 0;
  bottom: 0;
  width: 6px;
  cursor: col-resize;
  z-index: 100;
  background: transparent;
  transition: background 0.15s;
}

.resize-handle-panel:hover,
.resize-handle-panel.resize-active {
  background: #007acc;
}

/* Explorer resize handle (right edge of file explorer) */
.resize-handle-explorer {
  position: absolute;
  right: -2px;
  top: 0;
  bottom: 0;
  width: 4px;
  cursor: col-resize;
  z-index: 50;
  background: transparent;
  transition: background 0.15s;
}

.resize-handle-explorer:hover,
.resize-handle-explorer.resize-active {
  background: #007acc;
}
</style>
