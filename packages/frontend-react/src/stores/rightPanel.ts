import { create } from 'zustand'
import { persist } from 'zustand/middleware'

type PanelTab = {
  id: string
  pluginId: string
  params?: Record<string, unknown>
}

type Pane = {
  id: string
  tabs: PanelTab[]
  activeTabId: string | null
}

interface RightPanelState {
  collapsed: boolean
  panelRatio: number
  panes: Pane[]
  activePaneId: string | null
  maxPanes: number
  setCollapsed: (value: boolean) => void
  setPanelRatio: (value: number) => void
  setActivePane: (paneId: string) => void
  openTab: (pluginId: string, params?: Record<string, unknown>, paneId?: string) => void
  openOrFocusTab: (pluginId: string, params?: Record<string, unknown>, paneId?: string) => void
  closeTab: (paneId: string, tabId: string) => void
  setActiveTab: (paneId: string, tabId: string) => void
  splitPane: () => void
  closePane: (paneId: string) => void
}

const createId = (prefix: string) =>
  `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`

const normalizeParams = (params?: Record<string, unknown>) => {
  if (!params) return ''
  const entries = Object.entries(params).sort(([a], [b]) => a.localeCompare(b))
  return JSON.stringify(Object.fromEntries(entries))
}

export const useRightPanelStore = create<RightPanelState>()(
  persist(
    (set, get) => ({
      collapsed: true,
      panelRatio: 40,
      panes: [],
      activePaneId: null,
      maxPanes: 2,
      setCollapsed: (value) => set({ collapsed: value }),
      setPanelRatio: (value) => set({ panelRatio: value }),
      setActivePane: (paneId) => set({ activePaneId: paneId }),
      openTab: (pluginId, params, paneId) =>
        set((state) => {
          const panes = [...state.panes]
          let targetPaneId = paneId || state.activePaneId
          let paneIndex = panes.findIndex((pane) => pane.id === targetPaneId)

          if (paneIndex === -1) {
            targetPaneId = createId('pane')
            panes.push({ id: targetPaneId, tabs: [], activeTabId: null })
            paneIndex = panes.length - 1
          }

          const tabId = createId('tab')
          const tab: PanelTab = { id: tabId, pluginId, params }
          const pane = panes[paneIndex]
          panes[paneIndex] = {
            ...pane,
            tabs: [...pane.tabs, tab],
            activeTabId: tabId,
          }

          return {
            panes,
            activePaneId: targetPaneId,
            collapsed: false,
          }
        }),
      openOrFocusTab: (pluginId, params, paneId) =>
        set((state) => {
          const targetParams = normalizeParams(params)
          for (const pane of state.panes) {
            const existing = pane.tabs.find(
              (tab) =>
                tab.pluginId === pluginId &&
                normalizeParams(tab.params as Record<string, unknown> | undefined) === targetParams,
            )
            if (existing) {
              return {
                panes: state.panes.map((p) =>
                  p.id === pane.id ? { ...p, activeTabId: existing.id } : p,
                ),
                activePaneId: pane.id,
                collapsed: false,
              }
            }
          }

          const panes = [...state.panes]
          let targetPaneId = paneId || state.activePaneId
          let paneIndex = panes.findIndex((pane) => pane.id === targetPaneId)

          if (paneIndex === -1) {
            targetPaneId = createId('pane')
            panes.push({ id: targetPaneId, tabs: [], activeTabId: null })
            paneIndex = panes.length - 1
          }

          const tabId = createId('tab')
          const tab: PanelTab = { id: tabId, pluginId, params }
          const pane = panes[paneIndex]
          panes[paneIndex] = {
            ...pane,
            tabs: [...pane.tabs, tab],
            activeTabId: tabId,
          }

          return {
            panes,
            activePaneId: targetPaneId,
            collapsed: false,
          }
        }),
      closeTab: (paneId, tabId) =>
        set((state) => {
          const panes = state.panes.map((pane) => {
            if (pane.id !== paneId) return pane
            const nextTabs = pane.tabs.filter((tab) => tab.id !== tabId)
            const nextActive =
              pane.activeTabId === tabId
                ? nextTabs[0]?.id || null
                : pane.activeTabId
            return { ...pane, tabs: nextTabs, activeTabId: nextActive }
          })

          const nextPanes = panes.filter((pane) => pane.tabs.length > 0)
          const activePaneId = nextPanes.find((pane) => pane.id === state.activePaneId)
            ? state.activePaneId
            : nextPanes[0]?.id || null

          return { panes: nextPanes, activePaneId }
        }),
      setActiveTab: (paneId, tabId) =>
        set((state) => ({
          panes: state.panes.map((pane) =>
            pane.id === paneId ? { ...pane, activeTabId: tabId } : pane,
          ),
          activePaneId: paneId,
        })),
      splitPane: () =>
        set((state) => {
          if (state.panes.length >= state.maxPanes) return state
          const newPaneId = createId('pane')
          return {
            panes: [...state.panes, { id: newPaneId, tabs: [], activeTabId: null }],
            activePaneId: newPaneId,
            collapsed: false,
          }
        }),
      closePane: (paneId) =>
        set((state) => {
          const nextPanes = state.panes.filter((pane) => pane.id !== paneId)
          const activePaneId = nextPanes.find((pane) => pane.id === state.activePaneId)
            ? state.activePaneId
            : nextPanes[0]?.id || null
          return { panes: nextPanes, activePaneId }
        }),
    }),
    {
      name: 'right-panel-layout',
      partialize: (state) => ({
        collapsed: state.collapsed,
        panelRatio: state.panelRatio,
        panes: state.panes,
        activePaneId: state.activePaneId,
      }),
    },
  ),
)
