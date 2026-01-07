<script setup lang="ts">
import { ref, watch } from 'vue'
import { sandboxApi } from '../api/sandbox'
import { useChatStore } from '../stores/chat'
import { ChevronRight, RefreshCw, Home, FolderOpen } from 'lucide-vue-next'
import FileTreeItem, { type FileNode } from './FileTreeItem.vue'

const props = defineProps<{
  sessionId: string | null
}>()

const emit = defineEmits<{
  selectFile: [path: string]
}>()

// Delete confirmation dialog
const showDeleteConfirm = ref(false)
const deleteTarget = ref<{ path: string; name: string } | null>(null)

const chatStore = useChatStore()

const rootFiles = ref<FileNode[]>([])
const isLoading = ref(false)
const error = ref<string | null>(null)
const sandboxNotCreated = ref(false)
const currentSelectedPath = ref<string | null>(null)

// Track expanded folder paths to preserve state on refresh
const expandedPaths = ref<Set<string>>(new Set())

// Helper function to create a fingerprint of file list for comparison
function getFilesFingerprint(files: FileNode[]): string {
  const sortedFiles = [...files].sort((a, b) => a.path.localeCompare(b.path))
  return sortedFiles.map(f => `${f.path}|${f.type}|${f.size ?? 0}`).join(';')
}

// Check if files have changed (structure or size)
function hasFilesChanged(oldFiles: FileNode[], newFiles: { path: string; type: string; size?: number }[]): boolean {
  if (oldFiles.length !== newFiles.length) return true
  
  const oldFingerprint = getFilesFingerprint(oldFiles)
  const newFingerprint = newFiles
    .sort((a, b) => a.path.localeCompare(b.path))
    .map(f => `${f.path}|${f.type}|${f.size ?? 0}`)
    .join(';')
  
  return oldFingerprint !== newFingerprint
}

// Load files when session changes
watch(() => props.sessionId, async (newSessionId, oldSessionId) => {
  if (newSessionId) {
    if (oldSessionId !== undefined && oldSessionId !== null) {
      await loadRootFiles()
    } else {
      sandboxNotCreated.value = true
      rootFiles.value = []
    }
  } else {
    rootFiles.value = []
    sandboxNotCreated.value = false
    error.value = null
  }
}, { immediate: true })

// Auto-refresh root files when agent completes a task
watch(() => chatStore.isStreaming, async (streaming, wasStreaming) => {
  if (wasStreaming && !streaming && props.sessionId) {
    await new Promise(resolve => setTimeout(resolve, 500))
    await loadRootFiles() 
  }
})

// Refresh when sandbox files change (via event from backend)
// Skip initial trigger (value = 0)
watch(() => chatStore.filesChangedTrigger, async (newVal, oldVal) => {
  if (props.sessionId && oldVal !== undefined && newVal > 0) {
    await refreshWithExpandedState()
  }
})

async function loadRootFiles(preserveExpanded = false) {
  if (!props.sessionId) return
  
  isLoading.value = true
  error.value = null
  sandboxNotCreated.value = false
  
  try {
    const response = await sandboxApi.listFiles(props.sessionId, '/workspace')
    
    // Map files - set isOpen based on expandedPaths if preserving
    rootFiles.value = response.files.map(f => ({
      ...f,
      children: undefined,
      isOpen: preserveExpanded && expandedPaths.value.has(f.path),
      isLoading: false
    })) as FileNode[]
    
    sandboxNotCreated.value = false
  } catch (e: any) {
    if (e?.status === 404) {
      sandboxNotCreated.value = true
      error.value = null
      rootFiles.value = []
    } else {
      error.value = e instanceof Error ? e.message : 'Failed to load files'
      rootFiles.value = []
    }
  } finally {
    isLoading.value = false
  }
}

// Refresh and restore expanded folders (only if files changed)
async function refreshWithExpandedState() {
  if (!props.sessionId) return
  
  try {
    // Fetch new file list first
    const response = await sandboxApi.listFiles(props.sessionId, '/workspace')
    
    // Check if files have actually changed
    if (!hasFilesChanged(rootFiles.value, response.files)) {
      // No changes, skip refresh
      console.debug('[FileExplorer] No changes detected, skipping refresh')
      return
    }
    
    console.debug('[FileExplorer] Changes detected, refreshing...')
    
    // Save current expanded paths
    const pathsToExpand = new Set(expandedPaths.value)
    
    // Update root files with new data
    rootFiles.value = response.files.map(f => ({
      ...f,
      children: undefined,
      isOpen: pathsToExpand.has(f.path),
      isLoading: false
    })) as FileNode[]
    
    // Then load children for expanded folders (in background)
    for (const file of rootFiles.value) {
      if (file.isOpen && file.type === 'directory' && pathsToExpand.has(file.path)) {
        loadFolderChildrenRecursive(file, pathsToExpand)
      }
    }
  } catch (e) {
    console.error('[FileExplorer] Refresh error:', e)
  }
}

async function loadFolderChildrenRecursive(node: FileNode, pathsToExpand: Set<string>) {
  if (!props.sessionId || node.type !== 'directory') return
  
  node.isLoading = true
  try {
    const response = await sandboxApi.listFiles(props.sessionId, node.path)
    node.children = response.files.map(f => ({
      ...f,
      children: undefined,
      isOpen: pathsToExpand.has(f.path),
      isLoading: false
    })) as FileNode[]
    
    // Load expanded children (don't await, let them load in parallel)
    for (const child of node.children) {
      if (child.isOpen && child.type === 'directory') {
        loadFolderChildrenRecursive(child, pathsToExpand)
      }
    }
  } catch (e) {
    console.error('Failed to load folder:', e)
  } finally {
    node.isLoading = false
  }
}

async function loadFolderChildren(node: FileNode) {
  if (!props.sessionId || node.type !== 'directory') return
  
  node.isLoading = true
  try {
    const response = await sandboxApi.listFiles(props.sessionId, node.path)
    node.children = response.files.map(f => ({
      ...f,
      children: undefined,
      isOpen: false,
      isLoading: false
    })) as FileNode[]
  } catch (e) {
    console.error('Failed to load folder:', e)
  } finally {
    node.isLoading = false
  }
}

async function handleToggle(node: FileNode) {
  if (node.isOpen) {
    node.isOpen = false
    expandedPaths.value.delete(node.path)
    return
  }
  
  node.isOpen = true
  expandedPaths.value.add(node.path)
  
  if (!node.children) {
    await loadFolderChildren(node)
  }
}

function handleSelect(path: string) {
  currentSelectedPath.value = path
  emit('selectFile', path)
}

function handleDownload(path: string, _type: 'file' | 'directory') {
  if (!props.sessionId) return
  
  const url = sandboxApi.getDownloadUrl(props.sessionId, path)
  // Create a temporary link and click it to trigger download
  const link = document.createElement('a')
  link.href = url
  link.download = ''
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

function handleDeleteRequest(path: string, name: string) {
  deleteTarget.value = { path, name }
  showDeleteConfirm.value = true
}

async function confirmDelete() {
  if (!props.sessionId || !deleteTarget.value) return
  
  try {
    await sandboxApi.deleteFile(props.sessionId, deleteTarget.value.path)
    showDeleteConfirm.value = false
    deleteTarget.value = null
    // Refresh file list
    await loadRootFiles(true)
  } catch (e) {
    console.error('Failed to delete:', e)
  }
}

function cancelDelete() {
  showDeleteConfirm.value = false
  deleteTarget.value = null
}
</script>

<template>
  <div class="h-full flex flex-col bg-[#1e1e1e] select-none">
    <!-- Header - IDE Style -->
    <div class="h-9 flex items-center justify-between px-3 bg-[#252526] border-b border-[#3c3c3c]">
      <div class="flex items-center gap-1.5 text-xs text-[#cccccc]">
        <Home :size="12" class="text-[#75beff]" />
        <ChevronRight :size="10" class="text-[#808080]" />
        <span class="font-medium">workspace</span>
      </div>
      <button
        v-if="sessionId"
        @click="() => loadRootFiles(true)"
        :disabled="isLoading"
        class="p-1 hover:bg-[#3c3c3c] rounded transition-colors"
        title="Refresh"
      >
        <RefreshCw :size="12" :class="['text-[#808080] hover:text-[#cccccc]', { 'animate-spin': isLoading }]" />
      </button>
    </div>

    <!-- Files List -->
    <div class="flex-1 overflow-y-auto ide-scrollbar">
      <!-- Empty State -->
      <div v-if="!sessionId" class="h-full flex flex-col items-center justify-center p-4 text-center">
        <FolderOpen :size="32" class="text-[#606060] mb-2" />
        <p class="text-xs text-[#808080]">No active session</p>
        <p class="text-[10px] text-[#606060] mt-1">Start a chat to see files</p>
      </div>

      <!-- Loading Root -->
      <div v-else-if="isLoading && rootFiles.length === 0" class="h-full flex flex-col items-center justify-center p-4">
        <div class="w-6 h-6 rounded-full border border-[#606060] border-t-[#75beff] animate-spin"></div>
        <p class="text-[10px] text-[#808080] mt-2">Loading...</p>
      </div>

      <!-- Sandbox Not Created -->
      <div v-else-if="sandboxNotCreated" class="h-full flex flex-col items-center justify-center p-4 text-center">
        <FolderOpen :size="32" class="text-[#ccaa00] mb-2" />
        <p class="text-xs text-[#cccccc]">Workspace not ready</p>
        <p class="text-[10px] text-[#808080] mt-1 max-w-[140px]">
          Run code with AI agent, or click refresh
        </p>
      </div>

      <!-- Error -->
      <div v-else-if="error" class="h-full flex flex-col items-center justify-center p-4 text-center">
        <div class="w-8 h-8 rounded bg-[#5a1d1d] flex items-center justify-center mb-2">
          <svg class="w-4 h-4 text-[#f48771]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </div>
        <p class="text-xs text-[#f48771]">Failed to load</p>
        <p class="text-[10px] text-[#808080] mt-1">{{ error }}</p>
      </div>

      <!-- File Tree -->
      <div v-else-if="rootFiles.length > 0" class="py-0.5">
        <FileTreeItem
          v-for="file in rootFiles"
          :key="file.path"
          :file="file"
          :selected-path="currentSelectedPath"
          @toggle="handleToggle"
          @select="handleSelect"
          @download="handleDownload"
          @delete="handleDeleteRequest"
        />
      </div>

      <!-- Empty Root -->
      <div v-else class="h-full flex flex-col items-center justify-center p-4 text-center">
        <FolderOpen :size="32" class="text-[#606060] mb-2" />
        <p class="text-xs text-[#808080]">Empty directory</p>
        <p class="text-[10px] text-[#606060] mt-1">No files in /workspace</p>
      </div>
    </div>

    <!-- Delete Confirmation Dialog -->
    <Teleport to="body">
      <Transition name="fade">
        <div v-if="showDeleteConfirm" class="delete-overlay" @click.self="cancelDelete">
          <div class="delete-dialog">
            <div class="delete-title">Confirm Delete</div>
            <div class="delete-message">
              Are you sure you want to delete <span class="font-medium text-white">{{ deleteTarget?.name }}</span>?
            </div>
            <div class="delete-actions">
              <button class="delete-btn delete-btn-cancel" @click="cancelDelete">Cancel</button>
              <button class="delete-btn delete-btn-confirm" @click="confirmDelete">Delete</button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.ide-scrollbar::-webkit-scrollbar {
  width: 10px;
}

.ide-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}

.ide-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(121, 121, 121, 0.4);
  border-radius: 0;
  border: 3px solid transparent;
  background-clip: padding-box;
}

.ide-scrollbar::-webkit-scrollbar-thumb:hover {
  background: rgba(121, 121, 121, 0.7);
  border: 3px solid transparent;
  background-clip: padding-box;
}

/* Delete confirmation dialog */
.delete-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.delete-dialog {
  background: #252526;
  border: 1px solid #454545;
  border-radius: 8px;
  padding: 20px;
  min-width: 300px;
  max-width: 400px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
}

.delete-title {
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
  margin-bottom: 12px;
}

.delete-message {
  font-size: 13px;
  color: #cccccc;
  margin-bottom: 20px;
  line-height: 1.5;
}

.delete-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.delete-btn {
  padding: 6px 16px;
  border-radius: 4px;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.15s;
}

.delete-btn-cancel {
  background: transparent;
  border: 1px solid #454545;
  color: #cccccc;
}

.delete-btn-cancel:hover {
  background: #3c3c3c;
}

.delete-btn-confirm {
  background: #c53030;
  border: none;
  color: white;
}

.delete-btn-confirm:hover {
  background: #e53e3e;
}

/* Fade animation */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
