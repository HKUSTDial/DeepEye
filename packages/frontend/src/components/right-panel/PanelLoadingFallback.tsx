import { translateApp } from '../../locale'

export function PanelLoadingFallback({ title }: { title: string }) {
  return (
    <div className="right-panel-empty">
      <div className="right-panel-empty-title">{translateApp('rightPanel.loadingPanel', { title })}</div>
    </div>
  )
}
