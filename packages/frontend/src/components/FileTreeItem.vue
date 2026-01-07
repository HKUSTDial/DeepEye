<script setup lang="ts">
import { computed, ref } from 'vue'
import type { FileInfo } from '../api/sandbox'
import { Loader2, Download, Trash2 } from 'lucide-vue-next'

export interface FileNode extends FileInfo {
  children?: FileNode[]
  isOpen?: boolean
  isLoading?: boolean
}

const props = withDefaults(defineProps<{
  file: FileNode
  depth?: number
  selectedPath?: string | null
}>(), {
  depth: 0,
  selectedPath: null
})

const emit = defineEmits<{
  (e: 'toggle', node: FileNode): void
  (e: 'select', path: string): void
  (e: 'download', path: string, type: 'file' | 'directory'): void
  (e: 'delete', path: string, name: string): void
}>()

// Context menu state
const showContextMenu = ref(false)
const contextMenuPos = ref({ x: 0, y: 0 })

function handleContextMenu(e: MouseEvent) {
  e.preventDefault()
  e.stopPropagation()
  contextMenuPos.value = { x: e.clientX, y: e.clientY }
  showContextMenu.value = true
  
  // Close menu on click outside
  const closeMenu = () => {
    showContextMenu.value = false
    document.removeEventListener('click', closeMenu)
    document.removeEventListener('contextmenu', closeMenu)
  }
  setTimeout(() => {
    document.addEventListener('click', closeMenu)
    document.addEventListener('contextmenu', closeMenu)
  }, 0)
}

function handleDownload() {
  showContextMenu.value = false
  emit('download', props.file.path, props.file.type as 'file' | 'directory')
}

function handleDelete() {
  showContextMenu.value = false
  emit('delete', props.file.path, props.file.name)
}

const paddingLeft = computed(() => `${props.depth * 12 + 8}px`)
const isSelected = computed(() => props.selectedPath === props.file.path)

// File icon colors based on extension
function getIconColor(ext: string | undefined): string {
  const e = ext?.toLowerCase()
  if (!e) return '#cccccc'
  
  const colorMap: Record<string, string> = {
    // Python
    'py': '#3572A5',
    // JavaScript/TypeScript
    'js': '#f1e05a',
    'jsx': '#f1e05a',
    'ts': '#3178c6',
    'tsx': '#3178c6',
    // Web
    'html': '#e34c26',
    'css': '#563d7c',
    'vue': '#41b883',
    'svelte': '#ff3e00',
    // Data
    'json': '#cbcb41',
    'yaml': '#cb171e',
    'yml': '#cb171e',
    'xml': '#e34c26',
    'csv': '#217346',
    'xlsx': '#217346',
    // Markdown
    'md': '#083fa1',
    'txt': '#cccccc',
    // Config
    'toml': '#9c4121',
    'ini': '#cccccc',
    'env': '#ecd53f',
    // Shell
    'sh': '#89e051',
    'bash': '#89e051',
    // Images
    'png': '#a074c4',
    'jpg': '#a074c4',
    'jpeg': '#a074c4',
    'gif': '#a074c4',
    'svg': '#ffb13b',
    // Archives
    'zip': '#ec915c',
    'tar': '#ec915c',
    'gz': '#ec915c',
  }
  
  return colorMap[e] || '#cccccc'
}

const folderColor = computed(() => props.file.isOpen ? '#dcb67a' : '#c09553')
</script>

<template>
  <div class="select-none relative">
    <!-- Item Row -->
    <div
      @click="file.type === 'directory' ? emit('toggle', file) : emit('select', file.path)"
      @contextmenu="handleContextMenu"
      class="group flex items-center h-[22px] cursor-pointer"
      :class="[
        isSelected ? 'bg-[#094771]' : 'hover:bg-[#2a2d2e]'
      ]"
      :style="{ paddingLeft }"
    >
      <!-- Arrow for Directory -->
      <div class="w-4 h-4 flex items-center justify-center flex-shrink-0">
        <Loader2 v-if="file.isLoading" :size="10" class="animate-spin text-[#808080]" />
        <svg
          v-else-if="file.type === 'directory'"
          class="w-3 h-3 text-[#c5c5c5] transition-transform duration-150"
          :class="{ 'rotate-90': file.isOpen }"
          fill="currentColor"
          viewBox="0 0 16 16"
        >
          <path d="M6 4v8l4-4-4-4z" />
        </svg>
      </div>

      <!-- Folder/File Icon -->
      <div class="w-4 h-4 flex items-center justify-center flex-shrink-0 mr-1">
        <!-- Folder Icon -->
        <svg v-if="file.type === 'directory'" class="w-4 h-4" viewBox="0 0 24 24" fill="none">
          <path
            v-if="file.isOpen"
            d="M20 19H4a2 2 0 01-2-2V7a2 2 0 012-2h5l2 2h9a2 2 0 012 2v8a2 2 0 01-2 2z"
            :fill="folderColor"
          />
          <path
            v-else
            d="M10 4H4a2 2 0 00-2 2v12a2 2 0 002 2h16a2 2 0 002-2V8a2 2 0 00-2-2h-8l-2-2z"
            :fill="folderColor"
          />
        </svg>
        <!-- File Icon -->
        <svg v-else class="w-4 h-4" viewBox="0 0 24 24" fill="none">
          <path 
            d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6z" 
            fill="#3c3c3c"
            stroke="#808080"
            stroke-width="1"
          />
          <path d="M14 2v6h6" fill="#3c3c3c" stroke="#808080" stroke-width="1" />
          <rect x="8" y="12" width="8" height="1.5" rx="0.5" :fill="getIconColor(file.extension)" />
          <rect x="8" y="15" width="5" height="1.5" rx="0.5" :fill="getIconColor(file.extension)" />
        </svg>
      </div>

      <!-- Name -->
      <span 
        class="text-[13px] truncate leading-[22px]"
        :class="[
          isSelected ? 'text-white' : 'text-[#cccccc]'
        ]"
      >
        {{ file.name }}
      </span>
    </div>

    <!-- Children -->
    <div v-if="file.isOpen && file.children">
      <FileTreeItem
        v-for="child in file.children"
        :key="child.path"
        :file="child"
        :depth="depth + 1"
        :selected-path="selectedPath"
        @toggle="emit('toggle', $event)"
        @select="emit('select', $event)"
        @download="(path: string, type: 'file' | 'directory') => emit('download', path, type)"
        @delete="(path: string, name: string) => emit('delete', path, name)"
      />
      <!-- Empty folder message -->
      <div 
        v-if="file.children.length === 0 && !file.isLoading" 
        class="h-[22px] flex items-center text-[11px] text-[#6e6e6e] italic"
        :style="{ paddingLeft: `${(depth + 1) * 12 + 24}px` }"
      >
        (empty)
      </div>
    </div>

    <!-- Context Menu -->
    <Teleport to="body">
      <Transition name="menu-fade">
        <div
          v-if="showContextMenu"
          class="context-menu"
          :style="{ left: contextMenuPos.x + 'px', top: contextMenuPos.y + 'px' }"
        >
          <div class="context-menu-item" @click="handleDownload">
            <Download :size="14" />
            <span>{{ file.type === 'directory' ? 'Download as ZIP' : 'Download' }}</span>
          </div>
          <div class="context-menu-divider"></div>
          <div class="context-menu-item context-menu-item-danger" @click="handleDelete">
            <Trash2 :size="14" />
            <span>Delete</span>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.context-menu {
  position: fixed;
  z-index: 9999;
  min-width: 160px;
  background: #252526;
  border: 1px solid #454545;
  border-radius: 6px;
  padding: 4px 0;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
}

.context-menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  font-size: 13px;
  color: #cccccc;
  cursor: pointer;
  transition: background 0.1s;
}

.context-menu-item:hover {
  background: #094771;
}

.context-menu-item-danger:hover {
  background: #5a1d1d;
  color: #f48771;
}

.context-menu-divider {
  height: 1px;
  background: #454545;
  margin: 4px 0;
}

/* Menu fade animation */
.menu-fade-enter-active,
.menu-fade-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.menu-fade-enter-from,
.menu-fade-leave-to {
  opacity: 0;
  transform: scale(0.95);
}
</style>
