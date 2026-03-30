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

type SessionLayout = {
  panes: Pane[]
  activePaneId: string | null
}

interface RightPanelState {
  collapsed: boolean
  panelRatio: number
  panes: Pane[]
  activePaneId: string | null
  activeSessionKey: string | null
  sessionLayouts: Record<string, SessionLayout>
  maxPanes: number
  activateSession: (sessionKey: string | null) => void
  transferSessionLayout: (fromSessionKey: string, toSessionKey: string) => void
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

const clonePane = (pane: Pane): Pane => ({
  ...pane,
  tabs: pane.tabs.map((tab) => ({
    ...tab,
    params: tab.params ? { ...tab.params } : undefined,
  })),
})

const cloneLayout = (layout: SessionLayout): SessionLayout => ({
  panes: layout.panes.map(clonePane),
  activePaneId: layout.activePaneId,
})

const createEmptyLayout = (): SessionLayout => ({
  panes: [],
  activePaneId: null,
})

const syncActiveLayout = (
  state: RightPanelState,
  nextLayout: SessionLayout,
  extras?: Partial<RightPanelState>,
) => {
  const nextState: Partial<RightPanelState> = {
    panes: nextLayout.panes,
    activePaneId: nextLayout.activePaneId,
    ...extras,
  }

  if (state.activeSessionKey) {
    nextState.sessionLayouts = {
      ...state.sessionLayouts,
      [state.activeSessionKey]: cloneLayout(nextLayout),
    }
  }

  return nextState
}

export const useRightPanelStore = create<RightPanelState>()(
  persist(
    (set) => ({
      collapsed: true,
      panelRatio: 28,
      panes: [],
      activePaneId: null,
      activeSessionKey: null,
      sessionLayouts: {},
      maxPanes: 2,
      activateSession: (sessionKey) =>
        set((state) => {
          if (state.activeSessionKey === sessionKey) {
            return state
          }

          const sessionLayouts = { ...state.sessionLayouts }
          if (state.activeSessionKey) {
            sessionLayouts[state.activeSessionKey] = cloneLayout({
              panes: state.panes,
              activePaneId: state.activePaneId,
            })
          }

          const nextLayout = sessionKey
            ? cloneLayout(sessionLayouts[sessionKey] ?? createEmptyLayout())
            : createEmptyLayout()

          return {
            activeSessionKey: sessionKey,
            sessionLayouts,
            panes: nextLayout.panes,
            activePaneId: nextLayout.activePaneId,
          }
        }),
      transferSessionLayout: (fromSessionKey, toSessionKey) =>
        set((state) => {
          const sessionLayouts = { ...state.sessionLayouts }
          const sourceLayout =
            state.activeSessionKey === fromSessionKey
              ? cloneLayout({ panes: state.panes, activePaneId: state.activePaneId })
              : cloneLayout(sessionLayouts[fromSessionKey] ?? createEmptyLayout())

          sessionLayouts[toSessionKey] = sourceLayout
          delete sessionLayouts[fromSessionKey]

          if (state.activeSessionKey !== fromSessionKey) {
            return { sessionLayouts }
          }

          return {
            activeSessionKey: toSessionKey,
            sessionLayouts,
            panes: sourceLayout.panes,
            activePaneId: sourceLayout.activePaneId,
          }
        }),
      setCollapsed: (value) => set({ collapsed: value }),
      setPanelRatio: (value) => set({ panelRatio: value }),
      setActivePane: (paneId) =>
        set((state) =>
          syncActiveLayout(state, {
            panes: state.panes,
            activePaneId: paneId,
          }),
        ),
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

          return syncActiveLayout(
            state,
            {
              panes,
              activePaneId: targetPaneId,
            },
            { collapsed: false },
          )
        }),
      openOrFocusTab: (pluginId, params, paneId) => {
        return set((state) => {
          const targetParams = normalizeParams(params)
          for (const pane of state.panes) {
            const existing = pane.tabs.find(
              (tab) =>
                tab.pluginId === pluginId &&
                normalizeParams(tab.params as Record<string, unknown> | undefined) === targetParams,
            )
            if (existing) {
              return syncActiveLayout(
                state,
                {
                  panes: state.panes.map((p) =>
                    p.id === pane.id ? { ...p, activeTabId: existing.id } : p,
                  ),
                  activePaneId: pane.id,
                },
                { collapsed: false },
              )
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

          return syncActiveLayout(
            state,
            {
              panes,
              activePaneId: targetPaneId,
            },
            { collapsed: false },
          )
        })
      },
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

          return syncActiveLayout(state, { panes: nextPanes, activePaneId })
        }),
      setActiveTab: (paneId, tabId) =>
        set((state) =>
          syncActiveLayout(state, {
            panes: state.panes.map((pane) =>
              pane.id === paneId ? { ...pane, activeTabId: tabId } : pane,
            ),
            activePaneId: paneId,
          }),
        ),
      splitPane: () =>
        set((state) => {
          if (state.panes.length >= state.maxPanes) return state
          const newPaneId = createId('pane')
          return syncActiveLayout(
            state,
            {
              panes: [...state.panes, { id: newPaneId, tabs: [], activeTabId: null }],
              activePaneId: newPaneId,
            },
            { collapsed: false },
          )
        }),
      closePane: (paneId) =>
        set((state) => {
          const nextPanes = state.panes.filter((pane) => pane.id !== paneId)
          const activePaneId = nextPanes.find((pane) => pane.id === state.activePaneId)
            ? state.activePaneId
            : nextPanes[0]?.id || null
          return syncActiveLayout(state, { panes: nextPanes, activePaneId })
        }),
    }),
    {
      name: 'right-panel-layout',
      version: 2,
      migrate: (persistedState, version) => {
        const legacyState = persistedState as Partial<RightPanelState> | undefined
        if (!legacyState) {
          return {
            collapsed: true,
            panelRatio: 28,
            sessionLayouts: {},
          }
        }

        if (version < 2) {
          return {
            collapsed: legacyState.collapsed ?? true,
            panelRatio: legacyState.panelRatio ?? 28,
            sessionLayouts: {},
          }
        }

        return {
          collapsed: legacyState.collapsed ?? true,
          panelRatio: legacyState.panelRatio ?? 28,
          sessionLayouts: legacyState.sessionLayouts ?? {},
        }
      },
      partialize: (state) => ({
        collapsed: state.collapsed,
        panelRatio: state.panelRatio,
        sessionLayouts: state.sessionLayouts,
      }),
    },
  ),
)
