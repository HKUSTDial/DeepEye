import { create } from 'zustand'

export interface FileRevealRequest {
  path: string
  requestId: number
}

interface WorkspaceUiState {
  isDataSourceManagerOpen: boolean
  nextFileRevealId: number
  fileRevealRequests: Record<string, FileRevealRequest>
  openDataSourceManager: () => void
  closeDataSourceManager: () => void
  toggleDataSourceManager: () => void
  requestFileReveal: (sessionId: string, path: string) => void
}

export const useWorkspaceUiStore = create<WorkspaceUiState>((set) => ({
  isDataSourceManagerOpen: false,
  nextFileRevealId: 1,
  fileRevealRequests: {},
  openDataSourceManager: () => set({ isDataSourceManagerOpen: true }),
  closeDataSourceManager: () => set({ isDataSourceManagerOpen: false }),
  toggleDataSourceManager: () =>
    set((state) => ({ isDataSourceManagerOpen: !state.isDataSourceManagerOpen })),
  requestFileReveal: (sessionId, path) =>
    set((state) => {
      const requestId = state.nextFileRevealId + 1
      return {
        nextFileRevealId: requestId,
        fileRevealRequests: {
          ...state.fileRevealRequests,
          [sessionId]: {
            path,
            requestId,
          },
        },
      }
    }),
}))
