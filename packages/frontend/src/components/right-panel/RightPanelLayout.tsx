import { useEffect, useMemo, useRef, useState } from 'react'
import { Plus, X } from 'lucide-react'
import { panelRegistry, getPanelPlugin, type PanelRenderContext } from './panelRegistry'
import { useRightPanelStore } from '../../stores/rightPanel'
import { useLocale } from '../../locale'
import './RightPanel.css'

interface RightPanelLayoutProps {
  sessionId: string | null
  dataSourceIds: string[]
  onRequestClose?: () => void
}

export function RightPanelLayout({ sessionId, dataSourceIds, onRequestClose }: RightPanelLayoutProps) {
  const { t } = useLocale()
  const panes = useRightPanelStore((state) => state.panes)
  const openTab = useRightPanelStore((state) => state.openTab)
  const closeTab = useRightPanelStore((state) => state.closeTab)
  const setActiveTab = useRightPanelStore((state) => state.setActiveTab)
  const setActivePane = useRightPanelStore((state) => state.setActivePane)
  const closePane = useRightPanelStore((state) => state.closePane)

  const [menuPaneId, setMenuPaneId] = useState<string | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  const context = useMemo<PanelRenderContext>(
    () => ({ sessionId, dataSourceIds }),
    [sessionId, dataSourceIds],
  )

  useEffect(() => {
    if (!menuPaneId) return
    const onMouseDown = (event: MouseEvent) => {
      if (!containerRef.current) return
      if (!containerRef.current.contains(event.target as Node)) {
        setMenuPaneId(null)
      }
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setMenuPaneId(null)
      }
    }
    document.addEventListener('mousedown', onMouseDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('mousedown', onMouseDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [menuPaneId])

  if (panes.length === 0) {
    return (
      <div className="right-panel-container" ref={containerRef}>
        <div className="right-panel-empty">
          <div className="right-panel-empty-kicker">{t('common.workspace')}</div>
          <div className="right-panel-empty-icon">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <div className="right-panel-empty-title">{t('rightPanel.emptyTitle')}</div>
          <div className="right-panel-empty-subtitle">{t('rightPanel.emptySubtitle')}</div>
          <div className="right-panel-empty-actions">
            {panelRegistry.map((plugin) => (
              <button
                key={plugin.id}
                type="button"
                onClick={() => openTab(plugin.id)}
                className="right-panel-empty-action"
              >
                <span className="right-panel-entry-icon">{plugin.icon}</span>
                  <span className="right-panel-entry-text">
                    <span className="right-panel-entry-title">
                      {typeof plugin.title === 'string' ? plugin.title : plugin.title()}
                    </span>
                    <span className="right-panel-entry-desc">{typeof plugin.description === 'string' ? plugin.description : plugin.description()}</span>
                  </span>
                <span className="right-panel-entry-arrow" aria-hidden="true">
                  <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8">
                    <path d="m6 14 8-8M7 6h7v7" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="right-panel-container" ref={containerRef}>
      {panes.map((pane) => {
        const activeTab =
          pane.tabs.find((tab) => tab.id === pane.activeTabId) || pane.tabs[0] || null
        const plugin = activeTab ? getPanelPlugin(activeTab.pluginId) : undefined
        const title =
          plugin && typeof plugin.title === 'function' ? plugin.title(activeTab?.params) : typeof plugin?.title === 'string' ? plugin.title : null

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
                        <span className="right-panel-tab-icon" aria-hidden="true">
                          {tabPlugin?.icon}
                        </span>
                        <span className="truncate">{tabTitle}</span>
                      </button>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation()
                          closeTab(pane.id, tab.id)
                        }}
                        className="right-panel-tab-close"
                        aria-label={t('common.closeTab')}
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </div>
                  )
                })}
              </div>
              <div className="right-panel-actions">
                {onRequestClose && (
                  <button
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation()
                      onRequestClose()
                    }}
                    className="right-panel-action-btn right-panel-mobile-close"
                    title={t('common.closeWorkspace')}
                    aria-label={t('common.closeWorkspace')}
                  >
                    <X className="h-4 w-4" />
                  </button>
                )}
                <div className="relative">
                  <button
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation()
                      setMenuPaneId((current) => (current === pane.id ? null : pane.id))
                    }}
                    className="right-panel-action-btn"
                    title={t('common.newTab')}
                  >
                    <Plus className="h-4 w-4" />
                  </button>
                  {menuPaneId === pane.id && (
                    <div className="right-panel-menu">
                      <div className="right-panel-menu-title">{t('common.openView')}</div>
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
                          <span className="right-panel-entry-icon">{plugin.icon}</span>
                          <span className="right-panel-entry-text">
                            <span className="right-panel-entry-title">
                              {typeof plugin.title === 'string' ? plugin.title : plugin.title()}
                            </span>
                            <span className="right-panel-entry-desc">{typeof plugin.description === 'string' ? plugin.description : plugin.description()}</span>
                          </span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
                {panes.length > 1 && (
                  <button
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation()
                      closePane(pane.id)
                    }}
                    className="right-panel-action-btn"
                    title={t('common.closePane')}
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
                    {title ? t('rightPanel.loadingPanel', { title }) : t('common.selectTab')}
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
