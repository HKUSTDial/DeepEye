import { create } from 'zustand'

interface ReportState {
  reportHtml: string | null
  reportSteps: string[]
  reportFilename: string | null
  reportError: string | null
  isGenerating: boolean
  setReportResult: (html: string | null, steps: string[], filename?: string | null, error?: string | null) => void
  addReportStep: (step: string) => void
  startGeneration: () => void
  stopGeneration: () => void
  clear: () => void
}

export const useReportStore = create<ReportState>((set) => ({
  reportHtml: null,
  reportSteps: [],
  reportFilename: null,
  reportError: null,
  isGenerating: false,
  setReportResult: (html, steps, filename, error) =>
    set({
      reportHtml: html,
      reportSteps: steps ?? [],
      reportFilename: filename ?? null,
      reportError: error ?? null,
      isGenerating: false,
    }),
  addReportStep: (step) => set((state) => ({ reportSteps: [...state.reportSteps, step] })),
  startGeneration: () =>
    set({ isGenerating: true, reportSteps: [], reportHtml: null, reportFilename: null, reportError: null }),
  stopGeneration: () => set({ isGenerating: false }),
  clear: () =>
    set({ reportHtml: null, reportSteps: [], reportFilename: null, reportError: null, isGenerating: false }),
}))
