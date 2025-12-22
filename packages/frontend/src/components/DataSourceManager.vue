<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { DataSourceService } from '../api/datasource';
import type { DataSource } from '../types/datasource';

const emit = defineEmits(['select']);

const dataSources = ref<DataSource[]>([]);
const selectedId = ref<string>('');
const isCreating = ref(false);
const newDataSource = ref({
  name: '',
  type: 'postgres',
  connection_string: ''
});
const error = ref<string | null>(null);

async function loadDataSources() {
  try {
    dataSources.value = await DataSourceService.list();
    // Default select first one if available and none selected
    if (dataSources.value.length > 0 && !selectedId.value) {
        selectedId.value = dataSources.value[0].id;
        emit('select', selectedId.value);
    }
  } catch (e: any) {
    error.value = e.message;
  }
}

async function createDataSource() {
  if (!newDataSource.value.name || !newDataSource.value.connection_string) return;
  try {
    const created = await DataSourceService.create(newDataSource.value);
    dataSources.value.push(created);
    isCreating.value = false;
    newDataSource.value = { name: '', type: 'postgres', connection_string: '' };
    // Auto select new one
    selectedId.value = created.id;
    emit('select', created.id);
  } catch (e: any) {
    error.value = e.message;
  }
}

async function deleteDataSource(id: string) {
    if(!confirm('Are you sure?')) return;
    try {
        await DataSourceService.delete(id);
        dataSources.value = dataSources.value.filter(ds => ds.id !== id);
        if (selectedId.value === id) {
            selectedId.value = '';
            emit('select', null);
        }
    } catch (e: any) {
        error.value = e.message;
    }
}

function onSelectChange() {
    emit('select', selectedId.value);
}

onMounted(() => {
  loadDataSources();
});
</script>

<template>
  <div class="p-4 flex flex-col h-full text-white bg-gray-800">
    <h2 class="text-sm font-bold mb-2 uppercase text-gray-400 tracking-wider">Data Sources</h2>
    
    <!-- List -->
    <div class="flex-1 overflow-y-auto mb-2 custom-scrollbar">
        <div v-if="error" class="text-red-400 text-xs mb-2">{{ error }}</div>
        
        <div v-if="dataSources.length === 0" class="text-gray-500 text-xs">
            No data sources.
        </div>

        <div v-for="ds in dataSources" :key="ds.id" 
             class="flex justify-between items-center p-2 mb-1 rounded cursor-pointer hover:bg-gray-700 transition-colors"
             :class="{ 'bg-blue-900 border-blue-700 border': selectedId === ds.id, 'border border-transparent': selectedId !== ds.id }"
             @click="selectedId = ds.id; onSelectChange()">
            <div class="truncate flex-1 min-w-0">
                <div class="font-medium text-sm truncate">{{ ds.name }}</div>
                <div class="text-xs text-gray-400 truncate">{{ ds.type }}</div>
            </div>
            <button @click.stop="deleteDataSource(ds.id)" class="text-gray-500 hover:text-red-400 text-lg ml-2 leading-none">&times;</button>
        </div>
    </div>

    <!-- Create Form -->
    <button v-if="!isCreating" @click="isCreating = true" class="w-full py-1.5 bg-gray-700 text-gray-200 rounded hover:bg-gray-600 text-sm border border-gray-600">
        + Add Source
    </button>

    <div v-else class="border-t border-gray-700 pt-2">
        <input v-model="newDataSource.name" placeholder="Name" class="w-full mb-2 p-1 bg-gray-900 border border-gray-600 rounded text-sm text-white placeholder-gray-500">
        <select v-model="newDataSource.type" class="w-full mb-2 p-1 bg-gray-900 border border-gray-600 rounded text-sm text-white">
            <option value="postgres">PostgreSQL</option>
            <option value="mysql">MySQL</option>
            <option value="sqlite">SQLite</option>
        </select>
        <input v-model="newDataSource.connection_string" placeholder="URI" class="w-full mb-2 p-1 bg-gray-900 border border-gray-600 rounded text-sm text-white placeholder-gray-500">
        
        <div class="flex gap-2">
            <button @click="createDataSource" class="flex-1 bg-blue-600 hover:bg-blue-500 text-white py-1 rounded text-xs">Save</button>
            <button @click="isCreating = false" class="flex-1 bg-gray-700 hover:bg-gray-600 text-white py-1 rounded text-xs">Cancel</button>
        </div>
    </div>
  </div>
</template>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent; 
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #4b5563; 
  border-radius: 2px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: #6b7280; 
}
</style>

