<script setup lang="ts">
import { ref } from 'vue';
import ChatBox from './components/ChatBox.vue'
import DataSourceManager from './components/DataSourceManager.vue'
import Sidebar from './components/Sidebar.vue'

const currentDataSourceId = ref<string | null>(null);

function onDataSourceSelected(id: string) {
    currentDataSourceId.value = id;
}
</script>

<template>
  <div class="flex h-screen w-screen bg-gray-50">
    <!-- Sidebar Column -->
    <div class="w-64 flex flex-col h-full bg-gray-900 border-r border-gray-800 flex-shrink-0 z-20">
        <!-- History (Top) -->
        <div class="flex-1 overflow-hidden relative">
            <Sidebar />
        </div>
        
        <!-- Data Sources (Bottom) -->
        <div class="h-1/3 min-h-[200px] border-t border-gray-800 bg-gray-800">
            <DataSourceManager @select="onDataSourceSelected" />
        </div>
    </div>
    
    <!-- Main Chat Area -->
    <div class="flex-1 flex flex-col min-w-0 bg-white relative z-10">
        <div v-if="!currentDataSourceId" class="flex-1 flex items-center justify-center text-gray-400">
            Please select or create a data source to start chatting.
        </div>
        <ChatBox v-else :data-source-id="currentDataSourceId" class="flex-1" />
    </div>
  </div>
</template>
