import { create } from 'zustand'

interface ReportSessionState {
  reportHtml: string | null
  reportSteps: string[]
  reportFilename: string | null
  reportError: string | null
  isGenerating: boolean
}

interface ReportState {
  sessions: Record<string, ReportSessionState>
  ensureSession: (sessionId: string) => ReportSessionState
  setReportResult: (
    sessionId: string,
    html: string | null,
    steps: string[],
    filename?: string | null,
    error?: string | null,
  ) => void
  addReportStep: (sessionId: string, step: string) => void
  startGeneration: (sessionId: string) => void
  stopGeneration: (sessionId: string) => void
  clear: (sessionId: string) => void
}

const createEmptySession = (): ReportSessionState => ({
  reportHtml: null,
  reportSteps: [],
  reportFilename: null,
  reportError: null,
  isGenerating: false,
})

const withSession = (sessions: ReportState['sessions'], sessionId: string) =>
  sessions[sessionId] ?? createEmptySession()

export const useReportStore = create<ReportState>((set, get) => ({
  sessions: {},
  ensureSession: (sessionId) => {
    const existing = get().sessions[sessionId]
    if (existing) return existing
    const next = createEmptySession()
    set((state) => ({ sessions: { ...state.sessions, [sessionId]: next } }))
    return next
  },
  setReportResult: (sessionId, html, steps, filename, error) =>
    set((state) => {
      const current = withSession(state.sessions, sessionId)
      return {
        sessions: {
          ...state.sessions,
          [sessionId]: {
            ...current,
            reportHtml: html,
            reportSteps: steps ?? [],
            reportFilename: filename ?? null,
            reportError: error ?? null,
            isGenerating: false,
          },
        },
      }
    }),
  addReportStep: (sessionId, step) =>
    set((state) => {
      const current = withSession(state.sessions, sessionId)
      return {
        sessions: {
          ...state.sessions,
          [sessionId]: {
            ...current,
            reportSteps: [...current.reportSteps, step],
          },
        },
      }
    }),
  startGeneration: (sessionId) =>
    set((state) => {
      const current = withSession(state.sessions, sessionId)
      return {
        sessions: {
          ...state.sessions,
          [sessionId]: {
            ...current,
            isGenerating: true,
            reportSteps: [],
            reportHtml: null,
            reportFilename: null,
            reportError: null,
          },
        },
      }
    }),
  stopGeneration: (sessionId) =>
    set((state) => {
      const current = withSession(state.sessions, sessionId)
      return {
        sessions: {
          ...state.sessions,
          [sessionId]: {
            ...current,
            isGenerating: false,
          },
        },
      }
    }),
  clear: (sessionId) =>
    set((state) => ({
      sessions: {
        ...state.sessions,
        [sessionId]: createEmptySession(),
      },
    })),
}))
