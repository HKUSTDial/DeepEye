import { create } from 'zustand'

interface DatasourceSyncState {
  revision: number
  notifyUpdated: () => void
}

export const useDatasourceSyncStore = create<DatasourceSyncState>((set) => ({
  revision: 0,
  notifyUpdated: () => set((state) => ({ revision: state.revision + 1 })),
}))
