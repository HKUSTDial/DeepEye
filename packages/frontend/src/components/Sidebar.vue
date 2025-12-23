<script setup lang="ts">
import { onMounted } from 'vue'
import { useChatStore } from '../stores/chat'

const store = useChatStore()

onMounted(() => store.fetchSessions())

function handleNewChat() {
  store.createSession()
}

function handleSelectSession(id: string) {
  store.selectSession(id)
}

function handleDeleteSession(id: string, event: Event) {
  event.stopPropagation()
  if (confirm('Delete this conversation?')) {
    store.deleteSession(id)
  }
}
</script>

<template>
  <div class="flex flex-col h-full overflow-hidden">
    <!-- New Chat Button -->
    <div class="p-2">
      <button
        @click="handleNewChat"
        class="btn w-full flex items-center gap-3 px-3 py-3 rounded-xl border border-[var(--sidebar-border)] hover:bg-[var(--sidebar-hover)] text-sm"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
        </svg>
        New chat
      </button>
    </div>

    <!-- Session List -->
    <nav class="flex-1 overflow-y-auto px-2 pb-2">
      <!-- Loading skeleton -->
      <div v-if="store.isLoadingSessions" class="space-y-2 py-2">
        <div v-for="i in 3" :key="i" class="skeleton h-10 rounded-lg"></div>
      </div>

      <TransitionGroup v-else name="msg" tag="ul" class="space-y-1">
        <li v-for="session in store.sessions" :key="session.id">
          <div
            @click="handleSelectSession(session.id)"
            class="group flex items-center gap-3 px-3 py-2.5 rounded-xl cursor-pointer text-sm session-item"
            :class="store.sessionId === session.id ? 'bg-[var(--sidebar-active)]' : 'hover:bg-[var(--sidebar-hover)]'"
          >
            <!-- Chat Icon -->
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 flex-shrink-0 text-[var(--sidebar-text-muted)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            <!-- Title -->
            <span class="flex-1 truncate">
              {{ session.title || 'New conversation' }}
            </span>
            <!-- Delete -->
            <button
              @click="handleDeleteSession(session.id, $event)"
              class="btn opacity-0 group-hover:opacity-100 p-1.5 rounded-lg hover:bg-red-500/20 text-[var(--sidebar-text-muted)] hover:text-red-400"
              title="Delete"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        </li>

        <li v-if="store.sessions.length === 0" key="empty" class="text-center text-[var(--sidebar-text-muted)] text-sm py-8">
          <svg xmlns="http://www.w3.org/2000/svg" class="w-8 h-8 mx-auto mb-2 opacity-40" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">
            <path stroke-linecap="round" stroke-linejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
          No conversations yet
        </li>
      </TransitionGroup>
    </nav>
  </div>
</template>

<style scoped>
.session-item {
  transition: background 0.15s ease, transform 0.15s var(--ease-out-back);
}
.session-item:active {
  transform: scale(0.98);
}
</style>
