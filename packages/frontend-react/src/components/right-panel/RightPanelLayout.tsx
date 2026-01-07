import { useMemo, useState } from 'react'
import { Plus, X } from 'lucide-react'
import { panelRegistry, getPanelPlugin, type PanelRenderContext } from './panelRegistry'
import { useRightPanelStore } from '../../stores/rightPanel'

interface RightPanelLayoutProps {
  sessionId: string | null
  dataSourceId: string | null
}

export function RightPanelLayout({ sessionId, dataSourceId }: RightPanelLayoutProps) {
  const panes = useRightPanelStore((state) => state.panes)
  const activePaneId = useRightPanelStore((state) => state.activePaneId)
  const maxPanes = useRightPanelStore((state) => state.maxPanes)
  const openTab = useRightPanelStore((state) => state.openTab)
  const closeTab = useRightPanelStore((state) => state.closeTab)
  const setActiveTab = useRightPanelStore((state) => state.setActiveTab)
  const setActivePane = useRightPanelStore((state) => state.setActivePane)
  const splitPane = useRightPanelStore((state) => state.splitPane)
  const closePane = useRightPanelStore((state) => state.closePane)

  const [menuPaneId, setMenuPaneId] = useState<string | null>(null)

  const context = useMemo<PanelRenderContext>(
    () => ({ sessionId, dataSourceId }),
    [sessionId, dataSourceId],
  )

  if (panes.length === 0) {
    return (
      <div className="flex h-full w-full items-center justify-center bg-[#1e1e1e] text-slate-400">
        <div className="text-center">
          <div className="text-sm font-semibold text-slate-300">No panels open</div>
          <div className="mt-3 flex flex-col gap-2">
            {panelRegistry.map((plugin) => (
              <button
                key={plugin.id}
                type="button"
                onClick={() => openTab(plugin.id)}
                className="flex items-center justify-center gap-2 rounded-md border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-800"
              >
                {plugin.icon}
                Open {typeof plugin.title === 'string' ? plugin.title : plugin.title()}
              </button>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-full w-full bg-[#1e1e1e]">
      {panes.map((pane) => {
        const activeTab =
          pane.tabs.find((tab) => tab.id === pane.activeTabId) || pane.tabs[0] || null
        const plugin = activeTab ? getPanelPlugin(activeTab.pluginId) : undefined
        const title =
          plugin && typeof plugin.title === 'function' ? plugin.title(activeTab?.params) : plugin?.title
        const isActivePane = pane.id === activePaneId

        return (
          <div
            key={pane.id}
            className={`flex min-w-0 flex-1 flex-col border-l border-[#2a2a2a] ${
              isActivePane ? 'bg-[#1f1f1f]' : 'bg-[#1e1e1e]'
            }`}
            onClick={() => setActivePane(pane.id)}
          >
            <div className="flex items-center gap-2 border-b border-[#2a2a2a] bg-[#252526] px-2 py-1">
              <div className="flex min-w-0 flex-1 items-center gap-1 overflow-x-auto">
                {pane.tabs.map((tab) => {
                  const tabPlugin = getPanelPlugin(tab.pluginId)
                  const tabTitle =
                    tabPlugin && typeof tabPlugin.title === 'function'
                      ? tabPlugin.title(tab.params)
                      : tabPlugin?.title || tab.pluginId
                  const isActiveTab = tab.id === activeTab?.id

                  return (
                    <div
                      key={tab.id}
                      className={`group flex items-center gap-2 rounded-md px-2 py-1 text-xs ${
                        isActiveTab
                          ? 'bg-[#1e1e1e] text-slate-100'
                          : 'text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      <button
                        type="button"
                        onClick={() => setActiveTab(pane.id, tab.id)}
                        className="truncate text-left"
                      >
                        {tabTitle}
                      </button>
                      <button
                        type="button"
                        onClick={() => closeTab(pane.id, tab.id)}
                        className="rounded p-0.5 text-slate-500 hover:text-slate-200"
                        aria-label="Close tab"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </div>
                  )
                })}
              </div>
              <div className="flex items-center gap-1">
                <div className="relative">
                  <button
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation()
                      setMenuPaneId((current) => (current === pane.id ? null : pane.id))
                    }}
                    className="rounded p-1 text-slate-400 hover:text-slate-200"
                    title="New tab"
                  >
                    <Plus className="h-4 w-4" />
                  </button>
                  {menuPaneId === pane.id && (
                    <div className="absolute right-0 mt-1 w-40 rounded-md border border-slate-700 bg-slate-900 p-1 text-xs shadow-xl">
                      {panelRegistry.map((plugin) => (
                        <button
                          key={plugin.id}
                          type="button"
                          onClick={() => {
                            openTab(plugin.id, undefined, pane.id)
                            setMenuPaneId(null)
                          }}
                          className="flex w-full items-center gap-2 rounded px-2 py-1 text-left text-slate-200 hover:bg-slate-800"
                        >
                          {plugin.icon}
                          {typeof plugin.title === 'string' ? plugin.title : plugin.title()}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
                <button
                  type="button"
                  onClick={(event) => {
                    event.stopPropagation()
                    splitPane()
                  }}
                  disabled={panes.length >= maxPanes}
                  className="rounded px-2 py-1 text-xs text-slate-400 hover:text-slate-200 disabled:opacity-40"
                  title="Split pane"
                >
                  Split
                </button>
                {panes.length > 1 && (
                  <button
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation()
                      closePane(pane.id)
                    }}
                    className="rounded p-1 text-slate-400 hover:text-slate-200"
                    title="Close pane"
                  >
                    <X className="h-4 w-4" />
                  </button>
                )}
              </div>
            </div>
            <div className="min-h-0 flex-1 bg-[#1e1e1e]">
              {activeTab && plugin ? (
                plugin.render(context, activeTab.params)
              ) : (
                <div className="flex h-full items-center justify-center text-xs text-slate-500">
                  {title ? `Loading ${title}...` : 'Select a tab'}
                </div>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
