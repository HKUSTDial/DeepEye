import { useMemo, useState } from 'react'
import { Plus, X } from 'lucide-react'
import { panelRegistry, getPanelPlugin, type PanelRenderContext } from './panelRegistry'
import { useRightPanelStore } from '../../stores/rightPanel'
import './RightPanel.css'

interface RightPanelLayoutProps {
  sessionId: string | null
  dataSourceId: string | null
}

export function RightPanelLayout({ sessionId, dataSourceId }: RightPanelLayoutProps) {
  const panes = useRightPanelStore((state) => state.panes)
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
      <div className="right-panel-container">
        <div className="right-panel-empty">
          <div className="right-panel-empty-icon">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <div className="right-panel-empty-title">No panels open</div>
          <div className="right-panel-empty-subtitle">Open a panel to get started</div>
          <div className="right-panel-empty-actions">
            {panelRegistry.map((plugin) => (
              <button
                key={plugin.id}
                type="button"
                onClick={() => openTab(plugin.id)}
                className="right-panel-empty-action"
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
    <div className="right-panel-container">
      {panes.map((pane) => {
        const activeTab =
          pane.tabs.find((tab) => tab.id === pane.activeTabId) || pane.tabs[0] || null
        const plugin = activeTab ? getPanelPlugin(activeTab.pluginId) : undefined
        const title =
          plugin && typeof plugin.title === 'function' ? plugin.title(activeTab?.params) : plugin?.title

        return (
          <div
            key={pane.id}
            className="right-panel-pane"
            onClick={() => setActivePane(pane.id)}
          >
            <div className="right-panel-header">
              <div className="right-panel-tabs">
                {pane.tabs.map((tab) => {
                  const tabPlugin = getPanelPlugin(tab.pluginId)
                  const tabTitle: string =
                    tabPlugin && typeof tabPlugin.title === 'function'
                      ? tabPlugin.title(tab.params)
                      : (tabPlugin?.title as string) || tab.pluginId
                  const isActiveTab = tab.id === activeTab?.id

                  return (
                    <div
                      key={tab.id}
                      className={`right-panel-tab ${isActiveTab ? 'active' : ''}`}
                    >
                      <button
                        type="button"
                        onClick={() => setActiveTab(pane.id, tab.id)}
                        className="right-panel-tab-button"
                      >
                        <span className="truncate">{tabTitle}</span>
                      </button>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation()
                          closeTab(pane.id, tab.id)
                        }}
                        className="right-panel-tab-close"
                        aria-label="Close tab"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </div>
                  )
                })}
              </div>
              <div className="right-panel-actions">
                <div className="relative">
                  <button
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation()
                      setMenuPaneId((current) => (current === pane.id ? null : pane.id))
                    }}
                    className="right-panel-action-btn"
                    title="New tab"
                  >
                    <Plus className="h-4 w-4" />
                  </button>
                  {menuPaneId === pane.id && (
                    <div className="right-panel-menu">
                      {panelRegistry.map((plugin) => (
                        <button
                          key={plugin.id}
                          type="button"
                          onClick={() => {
                            openTab(plugin.id, undefined, pane.id)
                            setMenuPaneId(null)
                          }}
                          className="right-panel-menu-item"
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
                  className="right-panel-action-btn"
                  title="Split pane"
                >
                  <span className="text-xs">Split</span>
                </button>
                {panes.length > 1 && (
                  <button
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation()
                      closePane(pane.id)
                    }}
                    className="right-panel-action-btn"
                    title="Close pane"
                  >
                    <X className="h-4 w-4" />
                  </button>
                )}
              </div>
            </div>
            <div className="right-panel-content">
              {activeTab && plugin ? (
                plugin.render(context, activeTab.params)
              ) : (
                <div className="right-panel-empty">
                  <div className="right-panel-empty-title">
                    {title ? `Loading ${title}...` : 'Select a tab'}
                  </div>
                </div>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
