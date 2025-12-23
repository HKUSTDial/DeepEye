<script setup lang="ts">
import { ref, computed, nextTick, watch } from 'vue'
import VueMarkdown from 'vue-markdown-render'
import { useChat } from '../composables/useChat'
import { useChatStore } from '../stores/chat'
import type { Message } from '../types'
import StepItem from './StepItem.vue'

const props = defineProps<{ dataSourceId: string }>()

const { sendMessage, error } = useChat()
const store = useChatStore()
const messages = computed<Message[]>(() => store.messages)
const isStreaming = computed(() => store.isStreaming)
const input = ref('')
const chatContainer = ref<HTMLElement | null>(null)
const textareaRef = ref<HTMLTextAreaElement | null>(null)

function handleSend() {
  if (input.value.trim() && !isStreaming.value) {
    sendMessage(input.value.trim(), props.dataSourceId)
    input.value = ''
    if (textareaRef.value) textareaRef.value.style.height = 'auto'
  }
}

function autoResize(e: Event) {
  const el = e.target as HTMLTextAreaElement
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 200) + 'px'
}

function scrollToBottom() {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTo({
        top: chatContainer.value.scrollHeight,
        behavior: 'smooth'
      })
    }
  })
}

watch(() => store.messages.length, scrollToBottom)
watch(() => store.messages.at(-1)?.content, scrollToBottom)
</script>

<template>
  <div class="flex flex-col h-full">
    <!-- Messages Area -->
    <div ref="chatContainer" class="flex-1 overflow-y-auto scroll-smooth">
      <!-- Empty State -->
      <Transition name="fade" appear>
        <div v-if="messages.length === 0" class="h-full flex flex-col items-center justify-center px-4">
          <h2 class="text-2xl font-semibold mb-2">How can I help you today?</h2>
          <p class="text-[var(--main-text-muted)] text-center max-w-md">
            Ask me to analyze your data, write SQL queries, or create visualizations.
          </p>
        </div>
      </Transition>

      <!-- Messages -->
      <div v-if="messages.length > 0" class="max-w-3xl mx-auto px-4 py-6 space-y-5">
        <TransitionGroup name="msg">
          <div
            v-for="(msg, index) in messages"
            :key="`msg-${index}`"
            class="flex gap-3"
            :class="msg.role === 'user' ? 'justify-end' : 'justify-start'"
          >
            <!-- AI Avatar -->
            <div
              v-if="msg.role !== 'user'"
              class="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 bg-[var(--accent)] text-white text-sm font-medium"
            >
              D
            </div>

            <!-- Message Content -->
            <div class="flex-1 max-w-[80%] space-y-2" :class="msg.role === 'user' ? 'flex flex-col items-end' : ''">
              <!-- Tool Steps -->
              <TransitionGroup v-if="msg.steps?.length && msg.role !== 'user'" name="msg" tag="div" class="space-y-2">
                <StepItem v-for="(step, sIdx) in msg.steps" :key="`step-${sIdx}`" :step="step" />
              </TransitionGroup>

              <!-- Content Bubble -->
              <div
                v-if="msg.content || msg.isStreaming"
                class="inline-block rounded-2xl px-4 py-3 text-left"
                :class="msg.role === 'user'
                  ? 'bg-[var(--accent)] text-white'
                  : 'bg-[var(--main-bg-alt)]'"
              >
                <!-- User: plain text, AI: markdown -->
                <div v-if="msg.role === 'user'" class="whitespace-pre-wrap">{{ msg.content }}</div>
                <VueMarkdown v-else :source="msg.content || ''" class="prose-chat" />
                <span v-if="msg.isStreaming" class="typing-cursor"></span>
              </div>

              <!-- Thinking indicator -->
              <div v-if="msg.role === 'assistant' && msg.isStreaming && !msg.content && !msg.steps?.length" class="thinking-dots py-2">
                <span></span><span></span><span></span>
              </div>
            </div>

            <!-- User Avatar -->
            <div
              v-if="msg.role === 'user'"
              class="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 bg-purple-600 text-white text-sm font-medium"
            >
              U
            </div>
          </div>
        </TransitionGroup>

        <!-- Error -->
        <Transition name="fade">
          <div v-if="error" class="text-center text-red-400 text-sm py-2">
            {{ error }}
          </div>
        </Transition>
      </div>
    </div>

    <!-- Input Area -->
    <div class="border-t border-[var(--input-border)] bg-[var(--main-bg)]">
      <div class="max-w-3xl mx-auto px-4 py-4">
        <div class="relative flex items-end bg-[var(--input-bg)] rounded-2xl border border-[var(--input-border)] input-focus-ring">
          <textarea
            ref="textareaRef"
            v-model="input"
            @input="autoResize"
            @keydown.enter.exact.prevent="handleSend"
            rows="1"
            class="flex-1 bg-transparent px-4 py-3 resize-none focus:outline-none text-[var(--main-text)] placeholder-[var(--main-text-muted)]"
            style="max-height: 200px;"
            placeholder="Message DeepEye..."
            :disabled="isStreaming"
          ></textarea>
          <button
            @click="handleSend"
            :disabled="!input.trim() || isStreaming"
            class="btn m-2 p-2 rounded-xl"
            :class="input.trim() && !isStreaming
              ? 'bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white'
              : 'bg-transparent text-[var(--main-text-muted)]'"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="m5 12 7-7 7 7"/>
              <path d="M12 19V5"/>
            </svg>
          </button>
        </div>
        <p class="text-xs text-[var(--main-text-muted)] text-center mt-2 opacity-60">
          DeepEye can make mistakes. Consider checking important information.
        </p>
      </div>
    </div>
  </div>
</template>
