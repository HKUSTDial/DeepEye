<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { sandboxApi, type FileContentResponse } from '../api/sandbox'
import VueMarkdown from 'vue-markdown-render'
import { useCodeHighlight } from '../composables/useCodeHighlight'
import { X, FileCode, FileText as FileTextIcon } from 'lucide-vue-next'

// markdown-it options for GFM (GitHub Flavored Markdown)
const markdownOptions = {
  html: true,        // Enable HTML tags in source
  linkify: true,     // Autoconvert URL-like text to links
  typographer: true, // Enable smartquotes and other typographic replacements
  breaks: true,      // Convert '\n' in paragraphs into <br>
}

const props = defineProps<{
  sessionId: string | null
  filePath: string | null
}>()

const emit = defineEmits<{
  close: []
}>()

const fileContent = ref<FileContentResponse | null>(null)
const isLoading = ref(false)
const error = ref<string | null>(null)
const highlightedCode = ref<string>('')

const { highlight, isInitializing: isHighlighterLoading } = useCodeHighlight()

// Watch for file path changes
watch(() => [props.sessionId, props.filePath], async ([sessionId, path]) => {
  if (sessionId && path) {
    await loadFile(sessionId as string, path as string)
  } else {
    fileContent.value = null
    highlightedCode.value = ''
  }
}, { immediate: true })

async function loadFile(sessionId: string, path: string) {
  isLoading.value = true
  error.value = null
  highlightedCode.value = ''
  
  try {
    const content = await sandboxApi.getFileContent(sessionId, path)
    fileContent.value = content
    
    // Highlight code if it's a code file
    if (content.content_type === 'text') {
      const ext = fileExtension.value || ''
      if (['py', 'js', 'ts', 'jsx', 'tsx', 'json', 'html', 'css', 'xml', 'yaml', 'yml', 'vue', 'sh', 'bash', 'sql'].includes(ext)) {
        highlightedCode.value = await highlight(content.content, ext)
      }
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load file'
    fileContent.value = null
  } finally {
    isLoading.value = false
  }
}

const fileName = computed(() => {
  return props.filePath?.split('/').pop() || ''
})

const fileExtension = computed(() => {
  const name = fileName.value
  return name.includes('.') ? name.split('.').pop()?.toLowerCase() : ''
})

const viewerType = computed(() => {
  if (!fileContent.value) return 'none'
  
  if (fileContent.value.content_type === 'image') {
    return 'image'
  }
  
  const ext = fileExtension.value
  
  if (ext === 'md') return 'markdown'
  if (ext === 'csv') return 'csv'
  if (['py', 'js', 'ts', 'jsx', 'tsx', 'json', 'html', 'css', 'xml', 'yaml', 'yml'].includes(ext || '')) {
    return 'code'
  }
  
  return 'text'
})

// Parse CSV content
const csvData = computed(() => {
  if (viewerType.value !== 'csv' || !fileContent.value) return null
  
  const lines = fileContent.value.content.trim().split('\n')
  if (lines.length === 0 || !lines[0]) return null
  
  const headers = lines[0].split(',').map(h => h.trim())
  const rows = lines.slice(1).map(line => 
    line.split(',').map(cell => cell.trim())
  )
  
  return { headers, rows }
})

// Code lines for line numbers
const codeLines = computed(() => {
  if (!fileContent.value) return []
  return fileContent.value.content.split('\n')
})

// File icon color
const iconColor = computed(() => {
  const ext = fileExtension.value
  const colorMap: Record<string, string> = {
    'py': '#3572A5',
    'js': '#f1e05a',
    'ts': '#3178c6',
    'json': '#cbcb41',
    'html': '#e34c26',
    'css': '#563d7c',
    'vue': '#41b883',
    'md': '#083fa1',
    'csv': '#217346',
  }
  return colorMap[ext || ''] || '#75beff'
})
</script>

<template>
  <div class="h-full flex flex-col bg-[#1e1e1e]">
    <!-- Tab Bar -->
    <div v-if="filePath" class="h-9 flex items-center bg-[#252526] border-b border-[#3c3c3c]">
      <!-- File Tab -->
      <div class="h-full flex items-center gap-2 px-3 bg-[#1e1e1e] border-r border-[#3c3c3c] max-w-[200px]">
        <FileCode :size="14" :style="{ color: iconColor }" />
        <span class="text-[13px] text-[#cccccc] truncate">{{ fileName }}</span>
        <button
          @click="emit('close')"
          class="ml-1 p-0.5 hover:bg-[#3c3c3c] rounded transition-colors opacity-60 hover:opacity-100"
          title="Close"
        >
          <X :size="14" class="text-[#cccccc]" />
        </button>
      </div>
    </div>

    <!-- Breadcrumb -->
    <div v-if="filePath" class="h-6 flex items-center px-3 bg-[#1e1e1e] border-b border-[#3c3c3c]/50 text-[11px] text-[#808080]">
      <span class="truncate font-mono">{{ filePath }}</span>
    </div>

    <!-- Content -->
    <div class="flex-1 overflow-hidden flex flex-col">
      <!-- Loading -->
      <div v-if="isLoading" class="h-full flex flex-col items-center justify-center">
        <div class="w-8 h-8 rounded-full border border-[#606060] border-t-[#75beff] animate-spin"></div>
        <p class="text-xs text-[#808080] mt-3">Loading...</p>
      </div>

      <!-- Error -->
      <div v-else-if="error" class="h-full flex flex-col items-center justify-center p-6">
        <div class="w-10 h-10 rounded bg-[#5a1d1d] flex items-center justify-center mb-3">
          <svg class="w-5 h-5 text-[#f48771]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </div>
        <p class="text-sm text-[#f48771]">Failed to load file</p>
        <p class="text-xs text-[#808080] mt-2 text-center">{{ error }}</p>
      </div>

      <!-- Image Viewer -->
      <div v-else-if="viewerType === 'image' && fileContent" class="h-full flex items-center justify-center p-6 bg-[#1e1e1e] overflow-auto">
        <img
          :src="`data:image/${fileExtension};base64,${fileContent.content}`"
          :alt="fileName"
          class="max-w-full max-h-full object-contain"
        />
      </div>

      <!-- Markdown Viewer -->
      <div v-else-if="viewerType === 'markdown' && fileContent" class="flex-1 overflow-auto p-6 bg-[#1e1e1e]">
        <VueMarkdown 
          :source="fileContent.content" 
          :options="markdownOptions"
          class="markdown-body"
        />
      </div>

      <!-- CSV Viewer -->
      <div v-else-if="viewerType === 'csv' && csvData" class="flex-1 overflow-auto bg-[#1e1e1e]">
        <table class="w-full text-[13px] border-collapse">
          <thead class="sticky top-0 z-10">
            <tr class="bg-[#252526]">
              <th class="px-3 py-2 text-left font-semibold text-[#4fc1ff] border-b border-r border-[#3c3c3c] whitespace-nowrap">#</th>
              <th
                v-for="(header, idx) in csvData.headers"
                :key="idx"
                class="px-3 py-2 text-left font-semibold text-[#4fc1ff] border-b border-r border-[#3c3c3c] whitespace-nowrap"
              >
                {{ header }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, rowIdx) in csvData.rows" :key="rowIdx" class="hover:bg-[#2a2d2e] transition-colors">
              <td class="px-3 py-1.5 text-[#858585] border-r border-[#3c3c3c]/50 font-mono text-right">{{ rowIdx + 1 }}</td>
              <td
                v-for="(cell, cellIdx) in row"
                :key="cellIdx"
                class="px-3 py-1.5 text-[#cccccc] border-r border-[#3c3c3c]/50"
              >
                {{ cell }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Code Viewer with Line Numbers -->
      <div v-else-if="viewerType === 'code' && fileContent" class="flex-1 overflow-auto ide-code-viewer">
        <!-- Loading highlighter -->
        <div v-if="isHighlighterLoading && !highlightedCode" class="h-full flex flex-col items-center justify-center">
          <div class="w-6 h-6 rounded-full border border-[#606060] border-t-[#75beff] animate-spin"></div>
          <p class="text-xs text-[#808080] mt-2">Loading syntax highlighter...</p>
        </div>
        <!-- Highlighted code -->
        <div v-else-if="highlightedCode" class="code-with-lines">
          <div v-html="highlightedCode" class="shiki-wrapper"></div>
        </div>
        <!-- Fallback plain code with line numbers (single scroll container) -->
        <div v-else class="text-viewer">
          <table class="text-viewer-table">
            <tbody>
              <tr v-for="(line, idx) in codeLines" :key="idx" class="text-line">
                <td class="line-number">{{ idx + 1 }}</td>
                <td class="line-content"><pre>{{ line }}</pre></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Text Viewer with Line Numbers (single scroll container) -->
      <div v-else-if="viewerType === 'text' && fileContent" class="flex-1 overflow-auto text-viewer">
        <table class="text-viewer-table">
          <tbody>
            <tr v-for="(line, idx) in codeLines" :key="idx" class="text-line">
              <td class="line-number">{{ idx + 1 }}</td>
              <td class="line-content"><pre>{{ line }}</pre></td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- No File Selected -->
      <div v-else class="h-full flex flex-col items-center justify-center p-6 bg-[#1e1e1e]">
        <FileTextIcon :size="48" class="text-[#404040] mb-4" />
        <p class="text-sm text-[#808080]">Select a file to preview</p>
        <p class="text-xs text-[#606060] mt-1">Click a file on the left</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ============ GitHub Flavored Markdown Styles ============ */
.markdown-body {
  color: #c9d1d9;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif;
  font-size: 14px;
  line-height: 1.6;
  word-wrap: break-word;
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4),
.markdown-body :deep(h5),
.markdown-body :deep(h6) {
  margin-top: 24px;
  margin-bottom: 16px;
  font-weight: 600;
  line-height: 1.25;
  color: #e6edf3;
}

.markdown-body :deep(h1) {
  font-size: 2em;
  padding-bottom: 0.3em;
  border-bottom: 1px solid #30363d;
}

.markdown-body :deep(h2) {
  font-size: 1.5em;
  padding-bottom: 0.3em;
  border-bottom: 1px solid #30363d;
}

.markdown-body :deep(h3) { font-size: 1.25em; }
.markdown-body :deep(h4) { font-size: 1em; }
.markdown-body :deep(h5) { font-size: 0.875em; }
.markdown-body :deep(h6) { font-size: 0.85em; color: #8b949e; }

.markdown-body :deep(p) {
  margin-top: 0;
  margin-bottom: 16px;
}

.markdown-body :deep(a) {
  color: #58a6ff;
  text-decoration: none;
}

.markdown-body :deep(a:hover) {
  text-decoration: underline;
}

.markdown-body :deep(strong) {
  font-weight: 600;
  color: #e6edf3;
}

.markdown-body :deep(em) {
  font-style: italic;
}

.markdown-body :deep(code) {
  padding: 0.2em 0.4em;
  margin: 0;
  font-size: 85%;
  white-space: break-spaces;
  background-color: rgba(110, 118, 129, 0.4);
  border-radius: 6px;
  font-family: ui-monospace, SFMono-Regular, SF Mono, Menlo, Consolas, Liberation Mono, monospace;
}

.markdown-body :deep(pre) {
  padding: 16px;
  overflow: auto;
  font-size: 85%;
  line-height: 1.45;
  color: #c9d1d9;
  background-color: #161b22;
  border-radius: 6px;
  margin-bottom: 16px;
}

.markdown-body :deep(pre code) {
  padding: 0;
  margin: 0;
  font-size: 100%;
  word-break: normal;
  white-space: pre;
  background: transparent;
  border: 0;
}

.markdown-body :deep(blockquote) {
  padding: 0 1em;
  color: #8b949e;
  border-left: 0.25em solid #30363d;
  margin: 0 0 16px 0;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  margin-top: 0;
  margin-bottom: 16px;
  padding-left: 2em;
}

.markdown-body :deep(li) {
  margin-top: 0.25em;
}

.markdown-body :deep(li + li) {
  margin-top: 0.25em;
}

/* Nested lists */
.markdown-body :deep(ul ul),
.markdown-body :deep(ul ol),
.markdown-body :deep(ol ul),
.markdown-body :deep(ol ol) {
  margin-top: 0;
  margin-bottom: 0;
}

/* Task lists */
.markdown-body :deep(input[type="checkbox"]) {
  margin: 0 0.2em 0.25em -1.4em;
  vertical-align: middle;
}

/* Tables */
.markdown-body :deep(table) {
  border-spacing: 0;
  border-collapse: collapse;
  margin-top: 0;
  margin-bottom: 16px;
  display: block;
  width: max-content;
  max-width: 100%;
  overflow: auto;
}

.markdown-body :deep(th) {
  font-weight: 600;
  padding: 6px 13px;
  border: 1px solid #30363d;
  background-color: #161b22;
}

.markdown-body :deep(td) {
  padding: 6px 13px;
  border: 1px solid #30363d;
}

.markdown-body :deep(tr) {
  background-color: #0d1117;
  border-top: 1px solid #21262d;
}

.markdown-body :deep(tr:nth-child(2n)) {
  background-color: #161b22;
}

/* Horizontal rule */
.markdown-body :deep(hr) {
  height: 0.25em;
  padding: 0;
  margin: 24px 0;
  background-color: #30363d;
  border: 0;
}

/* Images */
.markdown-body :deep(img) {
  max-width: 100%;
  box-sizing: content-box;
  background-color: #0d1117;
  border-radius: 6px;
}

/* Keyboard */
.markdown-body :deep(kbd) {
  display: inline-block;
  padding: 3px 5px;
  font: 11px ui-monospace, SFMono-Regular, SF Mono, Menlo, Consolas, Liberation Mono, monospace;
  line-height: 10px;
  color: #c9d1d9;
  vertical-align: middle;
  background-color: #161b22;
  border: solid 1px rgba(110, 118, 129, 0.4);
  border-bottom-color: rgba(110, 118, 129, 0.4);
  border-radius: 6px;
  box-shadow: inset 0 -1px 0 rgba(110, 118, 129, 0.4);
}

/* Definition list */
.markdown-body :deep(dl) {
  padding: 0;
}

.markdown-body :deep(dl dt) {
  padding: 0;
  margin-top: 16px;
  font-size: 1em;
  font-style: italic;
  font-weight: 600;
}

.markdown-body :deep(dl dd) {
  padding: 0 16px;
  margin-bottom: 16px;
}

/* ============ IDE Code Viewer ============ */
.ide-code-viewer {
  background: #1e1e1e;
}

/* Shiki code highlighting */
.code-with-lines {
  display: flex;
  min-height: 100%;
}

.shiki-wrapper {
  flex: 1;
  overflow-x: auto;
}

.shiki-wrapper :deep(pre.shiki) {
  margin: 0;
  padding: 0.75rem 0;
  overflow-x: auto;
  background: #1e1e1e !important;
  font-size: 13px;
  line-height: 20px;
}

.shiki-wrapper :deep(pre.shiki code) {
  font-family: 'Cascadia Code', 'Fira Code', 'Consolas', 'Monaco', monospace;
  counter-reset: line;
}

.shiki-wrapper :deep(pre.shiki code > span.line) {
  display: block;
  padding-right: 1rem;
  min-height: 20px;
}

.shiki-wrapper :deep(pre.shiki code > span.line::before) {
  counter-increment: line;
  content: counter(line);
  display: inline-block;
  width: 3rem;
  margin-right: 1rem;
  padding-right: 0.5rem;
  text-align: right;
  color: #858585;
  border-right: 1px solid #3c3c3c50;
  user-select: none;
}

.shiki-wrapper :deep(pre.shiki code > span.line:hover) {
  background-color: #2a2d2e;
}

/* Scrollbar styling */
.ide-code-viewer::-webkit-scrollbar,
.shiki-wrapper :deep(pre.shiki)::-webkit-scrollbar {
  width: 10px;
  height: 10px;
}

.ide-code-viewer::-webkit-scrollbar-track,
.shiki-wrapper :deep(pre.shiki)::-webkit-scrollbar-track {
  background: transparent;
}

.ide-code-viewer::-webkit-scrollbar-thumb,
.shiki-wrapper :deep(pre.shiki)::-webkit-scrollbar-thumb {
  background: rgba(121, 121, 121, 0.4);
  border-radius: 0;
}

.ide-code-viewer::-webkit-scrollbar-thumb:hover,
.shiki-wrapper :deep(pre.shiki)::-webkit-scrollbar-thumb:hover {
  background: rgba(121, 121, 121, 0.7);
}

.ide-code-viewer::-webkit-scrollbar-corner,
.shiki-wrapper :deep(pre.shiki)::-webkit-scrollbar-corner {
  background: transparent;
}

/* Line numbers column */
.line-numbers {
  min-width: 3rem;
}

/* Text Viewer - single scroll container */
.text-viewer {
  background: #1e1e1e;
}

.text-viewer-table {
  border-collapse: collapse;
  width: 100%;
  font-family: 'Cascadia Code', 'Fira Code', 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  line-height: 20px;
}

.text-viewer-table .text-line:hover {
  background-color: #2a2d2e;
}

.text-viewer-table .line-number {
  width: 3rem;
  min-width: 3rem;
  padding: 0 0.5rem;
  text-align: right;
  color: #858585;
  border-right: 1px solid #3c3c3c50;
  user-select: none;
  vertical-align: top;
  position: sticky;
  left: 0;
  background: #1e1e1e;
}

.text-viewer-table .line-content {
  padding: 0 1rem;
  color: #cccccc;
  white-space: pre;
}

.text-viewer-table .line-content pre {
  margin: 0;
  font: inherit;
  white-space: pre;
}

/* First and last row padding */
.text-viewer-table tr:first-child td {
  padding-top: 0.75rem;
}

.text-viewer-table tr:last-child td {
  padding-bottom: 0.75rem;
}
</style>
