<script setup lang="ts">
import { ref, computed } from 'vue'
import type { ToolStep } from '../types'

const props = defineProps<{ step: ToolStep }>()
const expanded = ref(false)

const isRunning = computed(() => props.step.status === 'running')
</script>

<template>
  <!-- Thought Step -->
  <div v-if="step.type === 'thought'" class="flex items-start gap-2 text-sm text-[var(--main-text-muted)] py-1">
    <span class="thinking-dots mt-1" v-if="step.status === 'running'">
      <span></span><span></span><span></span>
    </span>
    <svg v-else xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 mt-0.5 flex-shrink-0 text-[var(--accent)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
    </svg>
    <span class="italic leading-relaxed">{{ step.thought }}</span>
  </div>

  <!-- Tool Step -->
  <div v-else class="rounded-xl border border-[var(--input-border)] overflow-hidden text-sm tool-card">
    <!-- Header -->
    <button
      @click="expanded = !expanded"
      class="btn w-full flex items-center gap-2 px-3 py-2.5 bg-[var(--input-bg)] hover:bg-[var(--sidebar-hover)] text-left group"
    >
      <!-- Spinner or Icon -->
      <div class="w-5 h-5 flex items-center justify-center flex-shrink-0">
        <svg v-if="isRunning" class="w-4 h-4 text-[var(--accent)] animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3"/>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
        </svg>
        <svg v-else xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-[var(--accent)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065zM15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      </div>
      <!-- Name -->
      <span class="flex-1 font-medium truncate">{{ step.name }}</span>
      <!-- Status Badge -->
      <span v-if="isRunning" class="text-xs px-2 py-0.5 rounded-full bg-[var(--accent)]/20 text-[var(--accent)]">
        Running
      </span>
      <span v-else class="text-xs px-2 py-0.5 rounded-full bg-green-500/20 text-green-400">
        Done
      </span>
      <!-- Expand Arrow -->
      <svg
        xmlns="http://www.w3.org/2000/svg"
        class="w-4 h-4 text-[var(--main-text-muted)] transition-transform duration-200"
        :class="{ 'rotate-180': expanded }"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        stroke-width="2"
      >
        <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
      </svg>
    </button>

    <!-- Details (with smooth height transition) -->
    <Transition name="expand">
      <div v-if="expanded" class="details-panel">
        <div class="px-3 py-3 space-y-3 bg-black/20">
          <!-- Input -->
          <div v-if="step.input" class="text-xs">
            <div class="text-[var(--main-text-muted)] mb-1.5 uppercase tracking-wide text-[10px] font-medium">Input</div>
            <pre class="p-2.5 bg-black/30 rounded-lg overflow-x-auto leading-relaxed">{{ step.input }}</pre>
          </div>

          <!-- Sub-Steps -->
          <TransitionGroup v-if="step.subSteps?.length" name="msg" tag="div" class="space-y-2 pl-3 border-l-2 border-[var(--accent)]/30">
            <StepItem v-for="(sub, idx) in step.subSteps" :key="`sub-${idx}`" :step="sub" />
          </TransitionGroup>

          <!-- Output -->
          <div v-if="step.output" class="text-xs">
            <div class="text-[var(--main-text-muted)] mb-1.5 uppercase tracking-wide text-[10px] font-medium">Output</div>
            <pre class="p-2.5 bg-black/30 rounded-lg overflow-x-auto max-h-48 leading-relaxed">{{ step.output }}</pre>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.tool-card {
  transition: box-shadow 0.2s ease;
}
.tool-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.details-panel {
  max-height: 500px;
  overflow-y: auto;
}

/* Custom scrollbar for details panel */
.details-panel::-webkit-scrollbar {
  width: 6px;
}
.details-panel::-webkit-scrollbar-track {
  background: transparent;
}
.details-panel::-webkit-scrollbar-thumb {
  background: var(--main-text-muted);
  border-radius: 3px;
  opacity: 0.3;
}
.details-panel::-webkit-scrollbar-thumb:hover {
  background: var(--accent);
}

/* Expand transition */
.expand-enter-active,
.expand-leave-active {
  transition: max-height 0.3s var(--ease-out-expo), opacity 0.2s ease;
  overflow: hidden;
}
.expand-enter-from,
.expand-leave-to {
  max-height: 0;
  opacity: 0;
}
.expand-enter-to,
.expand-leave-from {
  max-height: 500px;
  opacity: 1;
}
</style>
