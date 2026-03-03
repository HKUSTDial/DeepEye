import { create } from 'zustand'
import { knowledgeBasesApi } from '../api'
import type { KnowledgeBase } from '../types'

type KnowledgeBaseState = {
  bases: KnowledgeBase[]
  isLoading: boolean
  error: string | null
  loadBases: () => Promise<void>
  refreshBases: () => Promise<void>
}

export const useKnowledgeBasesStore = create<KnowledgeBaseState>((set, get) => ({
  bases: [],
  isLoading: false,
  error: null,
  loadBases: async () => {
    if (get().isLoading) return
    if (get().bases.length > 0) return
    set({ isLoading: true, error: null })
    try {
      const bases = await knowledgeBasesApi.list()
      set({ bases, isLoading: false })
    } catch (err) {
      set({
        bases: [],
        isLoading: false,
        error: err instanceof Error ? err.message : 'Failed to load knowledge bases.',
      })
    }
  },
  refreshBases: async () => {
    if (get().isLoading) return
    set({ isLoading: true, error: null })
    try {
      const bases = await knowledgeBasesApi.list()
      set({ bases, isLoading: false })
    } catch (err) {
      set({
        bases: [],
        isLoading: false,
        error: err instanceof Error ? err.message : 'Failed to load knowledge bases.',
      })
    }
  },
}))
