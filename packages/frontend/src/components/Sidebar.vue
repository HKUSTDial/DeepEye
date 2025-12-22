<script setup lang="ts">
import { onMounted } from 'vue'
import { useChatStore } from '../stores/chat'

const store = useChatStore()

onMounted(() => {
  store.fetchSessions()
})

function handleNewChat() {
    store.createSession()
}

function handleSelectSession(id: string) {
    store.selectSession(id)
}

function handleDeleteSession(id: string, event: Event) {
    event.stopPropagation()
    if (confirm('Are you sure you want to delete this conversation?')) {
        store.deleteSession(id)
    }
}
</script>

<template>
  <div class="flex flex-col h-full bg-gray-900 text-white">
    <div class="p-4 border-b border-gray-800">
      <button 
        @click="handleNewChat"
        class="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded-md transition-colors font-medium text-sm"
      >
        <span>+</span> New Chat
      </button>
    </div>

    <div class="flex-1 overflow-y-auto custom-scrollbar">
        <div v-if="store.isLoadingSessions" class="text-center text-gray-400 py-4 text-sm">
            Loading...
        </div>
        <ul v-else class="space-y-1 p-2">
            <li v-for="session in store.sessions" :key="session.id">
                <div 
                    @click="handleSelectSession(session.id)"
                    class="group flex items-center justify-between p-3 rounded-md cursor-pointer hover:bg-gray-800 transition-colors"
                    :class="{ 'bg-gray-800': store.sessionId === session.id }"
                >
                    <div class="flex-1 min-w-0">
                        <div class="truncate text-sm text-gray-200">
                            {{ session.title || 'Untitled Conversation' }}
                        </div>
                        <div class="text-xs text-gray-500 mt-1">
                            {{ new Date(session.updated_at).toLocaleDateString() }} {{ new Date(session.updated_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) }}
                        </div>
                    </div>
                    <button 
                        @click="handleDeleteSession(session.id, $event)"
                        class="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-400 transition-opacity p-1 ml-2"
                        title="Delete"
                    >
                        <span class="text-lg leading-none">&times;</span>
                    </button>
                </div>
            </li>
            
            <li v-if="store.sessions.length === 0" class="text-center text-gray-500 text-sm py-4">
                No history yet.
            </li>
        </ul>
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
  background: #374151; 
  border-radius: 2px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: #4b5563; 
}
</style>

