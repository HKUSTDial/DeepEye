<script setup lang="ts">
import type { ToolStep } from '../types/chat';

defineProps<{
  step: ToolStep
}>()
</script>

<template>
  <!-- Case 1: Thought -->
  <div v-if="step.type === 'thought'" class="bg-blue-50/50 p-2 rounded text-xs border-l-2 border-blue-200 mb-2">
      <div class="text-[10px] text-blue-400 uppercase tracking-wider mb-1 flex justify-between">
          <span>Thinking ({{ step.source }})</span>
          <span v-if="step.status === 'running'" class="animate-pulse">...</span>
      </div>
      <div class="text-gray-600 font-mono whitespace-pre-wrap">{{ step.thought }}</div>
  </div>

  <!-- Case 2: Tool -->
  <div v-else class="bg-white/50 p-2 rounded text-xs border border-gray-300/50 mb-2">
      <!-- Header -->
      <div class="font-bold flex justify-between items-center text-gray-700">
          <span class="flex items-center gap-2">
              <span v-if="step.source === 'supervisor'">🛠️</span>
              <span v-else>⚙️</span>
              {{ step.name }}
          </span>
          <span v-if="step.status === 'running'" class="animate-pulse text-blue-600">Running...</span>
          <span v-else class="text-green-700">Done</span>
      </div>

      <!-- Input -->
      <div v-if="step.input" class="mt-1 text-gray-600 font-mono truncate opacity-75" :title="step.input">
          Input: {{ step.input }}
      </div>

      <!-- Recursive Sub-Steps (Thoughts & Inner Tools) -->
      <div v-if="step.subSteps && step.subSteps.length > 0" class="mt-2 pl-2 border-l-2 border-gray-200">
          <StepItem v-for="(sub, idx) in step.subSteps" :key="idx" :step="sub" />
      </div>

      <!-- Output -->
      <details v-if="step.output" class="mt-1">
          <summary class="cursor-pointer text-gray-600 hover:text-gray-900 select-none">Show Output</summary>
          <pre class="mt-1 text-gray-800 bg-gray-50 p-1 rounded overflow-x-auto max-h-40">{{ step.output }}</pre>
      </details>
  </div>
</template>
