<script setup lang="ts">
import { ref, toRefs } from 'vue'
import { useChat } from '../composables/useChat'
import { useChatStore } from '../stores/chat'
import StepItem from './StepItem.vue'

const props = defineProps<{
  dataSourceId: string
}>()

const { dataSourceId } = toRefs(props)
const { sendMessage, isConnecting, error } = useChat()
const store = useChatStore()
const { messages } = toRefs(store)
const input = ref('')

function handleSend() {
  if (input.value && !isConnecting.value) {
    sendMessage(input.value, dataSourceId.value)
    input.value = ''
  }
}
</script>

<template>
  <div class="flex flex-col h-screen bg-gray-100 p-4">
    <!-- Header -->
    <header class="mb-4">
        <h1 class="text-2xl font-bold text-gray-800">DeepEye Agent</h1>
        <p class="text-sm text-gray-500">FastAPI + LangGraph + Vue 3</p>
    </header>

    <!-- Chat Area -->
    <div class="flex-1 overflow-y-auto bg-white rounded-lg shadow p-4 space-y-4">
        <div v-if="messages.length === 0" class="text-center text-gray-400 mt-10">
            Start a conversation...
        </div>

        <div 
            v-for="(msg, index) in messages" 
            :key="index" 
            class="flex"
            :class="msg.role === 'user' ? 'justify-end' : 'justify-start'"
        >
            <div 
                class="max-w-[80%] rounded-lg p-3 whitespace-pre-wrap flex flex-col gap-2"
                :class="msg.role === 'user' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-800'"
            >
                <!-- Tool Steps (Thinking Process) -->
                <div v-if="msg.steps && msg.steps.length > 0" class="flex flex-col gap-2 mb-2 w-full">
                    <StepItem v-for="(step, sIdx) in msg.steps" :key="sIdx" :step="step" />
                </div>

                <!-- Main Content -->
                <div class="whitespace-pre-wrap">
                    {{ msg.content }}
                    <span v-if="msg.isStreaming" class="inline-block w-2 h-4 ml-1 bg-gray-500 animate-pulse"></span>
                </div>
            </div>
        </div>
        
        <div v-if="error" class="text-red-500 text-center text-sm">
            Error: {{ error }}
        </div>
    </div>

    <!-- Input Area -->
    <div class="mt-4 flex gap-2">
        <input 
            v-model="input"
            @keyup.enter="handleSend"
            type="text" 
            class="flex-1 border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Ask something (e.g. 'Analyze sales data')..."
            :disabled="isConnecting"
        />
        <button 
            @click="handleSend"
            class="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            :disabled="isConnecting"
        >
            {{ isConnecting ? 'Thinking...' : 'Send' }}
        </button>
    </div>
  </div>
</template>

