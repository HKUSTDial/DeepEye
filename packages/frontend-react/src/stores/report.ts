import { create } from 'zustand'

interface ReportState {
  reportHtml: string | null
  reportSteps: string[]
  reportFilename: string | null
  reportError: string | null
  setReportResult: (html: string | null, steps: string[], filename?: string | null, error?: string | null) => void
  clear: () => void
}

export const useReportStore = create<ReportState>((set) => ({
  reportHtml: null,
  reportSteps: [],
  reportFilename: null,
  reportError: null,
  setReportResult: (html, steps, filename, error) => set({ 
    reportHtml: html, 
    reportSteps: steps ?? [], 
    reportFilename: filename ?? null,
    reportError: error ?? null,
  }),
  clear: () => set({ reportHtml: null, reportSteps: [], reportFilename: null, reportError: null }),
}))
