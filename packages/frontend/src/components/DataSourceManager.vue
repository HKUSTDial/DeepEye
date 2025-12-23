<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { datasourceApi } from '../api'
import type { DataSource } from '../types'

const emit = defineEmits<{ select: [id: string | null] }>()

const dataSources = ref<DataSource[]>([])
const selectedId = ref('')
const isCreating = ref(false)
const newDs = ref({ name: '', type: 'postgres', connection_string: '' })
const error = ref<string | null>(null)

async function loadDataSources() {
  try {
    dataSources.value = await datasourceApi.list()
    if (dataSources.value.length && !selectedId.value) {
      selectedId.value = dataSources.value[0].id
      emit('select', selectedId.value)
    }
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Failed to load'
  }
}

async function createDataSource() {
  if (!newDs.value.name || !newDs.value.connection_string) return
  try {
    const created = await datasourceApi.create(newDs.value)
    dataSources.value.push(created)
    isCreating.value = false
    newDs.value = { name: '', type: 'postgres', connection_string: '' }
    selectedId.value = created.id
    emit('select', created.id)
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Failed to create'
  }
}

async function deleteDataSource(id: string, event: Event) {
  event.stopPropagation()
  if (!confirm('Delete this data source?')) return
  try {
    await datasourceApi.delete(id)
    dataSources.value = dataSources.value.filter(ds => ds.id !== id)
    if (selectedId.value === id) {
      selectedId.value = ''
      emit('select', null)
    }
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Failed to delete'
  }
}

function selectSource(id: string) {
  selectedId.value = id
  emit('select', id)
}

onMounted(loadDataSources)
</script>

<template>
  <div class="border-t border-[var(--sidebar-border)] p-2">
    <!-- Header -->
    <div class="flex items-center justify-between px-2 py-1.5 mb-1">
      <span class="text-xs font-medium text-[var(--sidebar-text-muted)] uppercase tracking-wider">Data Sources</span>
      <button
        @click="isCreating = !isCreating"
        class="btn p-1.5 rounded-lg hover:bg-[var(--sidebar-hover)] text-[var(--sidebar-text-muted)] hover:text-[var(--sidebar-text)]"
        :title="isCreating ? 'Cancel' : 'Add Data Source'"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 transition-transform duration-200" :class="{ 'rotate-45': isCreating }" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
        </svg>
      </button>
    </div>

    <!-- Error -->
    <Transition name="fade">
      <div v-if="error" class="text-red-400 text-xs px-2 mb-2">{{ error }}</div>
    </Transition>

    <!-- Create Form -->
    <Transition name="expand">
      <div v-if="isCreating" class="form-panel">
        <div class="space-y-2 p-2.5 bg-[var(--sidebar-hover)] rounded-xl mb-2">
          <input
            v-model="newDs.name"
            placeholder="Name"
            class="w-full px-3 py-2 bg-[var(--sidebar-bg)] border border-[var(--sidebar-border)] rounded-lg text-sm focus:outline-none input-focus-ring"
          />
          <select
            v-model="newDs.type"
            class="w-full px-3 py-2 bg-[var(--sidebar-bg)] border border-[var(--sidebar-border)] rounded-lg text-sm focus:outline-none input-focus-ring"
          >
            <option value="postgres">PostgreSQL</option>
            <option value="mysql">MySQL</option>
            <option value="sqlite">SQLite</option>
          </select>
          <input
            v-model="newDs.connection_string"
            placeholder="Connection URI"
            class="w-full px-3 py-2 bg-[var(--sidebar-bg)] border border-[var(--sidebar-border)] rounded-lg text-sm focus:outline-none input-focus-ring"
          />
          <button
            @click="createDataSource"
            class="btn w-full py-2 bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white rounded-lg text-sm font-medium"
          >
            Connect
          </button>
        </div>
      </div>
    </Transition>

    <!-- List -->
    <div class="space-y-1 max-h-36 overflow-y-auto">
      <Transition name="fade">
        <div v-if="dataSources.length === 0 && !isCreating" class="text-[var(--sidebar-text-muted)] text-xs text-center py-4">
          <svg xmlns="http://www.w3.org/2000/svg" class="w-6 h-6 mx-auto mb-1.5 opacity-40" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">
            <path stroke-linecap="round" stroke-linejoin="round" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
          </svg>
          No data sources
        </div>
      </Transition>

      <TransitionGroup name="msg" tag="div" class="space-y-1">
        <div
          v-for="ds in dataSources"
          :key="ds.id"
          @click="selectSource(ds.id)"
          class="group flex items-center gap-2 px-2.5 py-2 rounded-xl cursor-pointer text-sm ds-item"
          :class="selectedId === ds.id ? 'bg-[var(--accent)] text-white' : 'hover:bg-[var(--sidebar-hover)]'"
        >
          <!-- DB Icon -->
          <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
          </svg>
          <!-- Name -->
          <span class="flex-1 truncate">{{ ds.name }}</span>
          <!-- Delete -->
          <button
            @click="deleteDataSource(ds.id, $event)"
            class="btn opacity-0 group-hover:opacity-100 p-1 rounded-lg"
            :class="selectedId === ds.id ? 'hover:bg-white/20' : 'hover:bg-red-500/20 text-[var(--sidebar-text-muted)] hover:text-red-400'"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </TransitionGroup>
    </div>
  </div>
</template>

<style scoped>
.form-panel {
  overflow: hidden;
}

.ds-item {
  transition: background 0.15s ease, transform 0.15s var(--ease-out-back);
}
.ds-item:active {
  transform: scale(0.98);
}

/* Expand transition for form */
.expand-enter-active,
.expand-leave-active {
  transition: all 0.25s var(--ease-out-expo);
  overflow: hidden;
}
.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  max-height: 0;
}
.expand-enter-to,
.expand-leave-from {
  opacity: 1;
  max-height: 200px;
}
</style>
