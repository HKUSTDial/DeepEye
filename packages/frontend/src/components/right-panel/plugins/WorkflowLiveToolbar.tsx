import { Loader2, Workflow as WorkflowIcon } from 'lucide-react'

import type { WorkflowDraft } from '../../../types'
import {
  buildWorkflowExportFilename,
  getDraftDisplayName,
} from './workflowPanelUtils'

type WorkflowLiveToolbarProps = {
  sessionId: string | null
  availableDrafts: WorkflowDraft[]
  activeDraft: WorkflowDraft | null
  activeDraftId: string | null
  runStatus: string | null
  runError: string | null
  error: string | null
  displayFileError: string | null
  isViewSwitching: boolean
  isLoadingFiles: boolean
  isLoadingFile: boolean
  isSaving: boolean
  isStreaming: boolean
  isExporting: boolean
  isRunning: boolean
  hasNodeDefinitions: boolean
  hasFlowNodes: boolean
  onSelectDraft: (draftId: string) => void
  onSave: () => Promise<void>
  onExport: (filename: string) => void
  onRun: () => Promise<void>
}

export function WorkflowLiveToolbar({
  sessionId,
  availableDrafts,
  activeDraft,
  activeDraftId,
  runStatus,
  runError,
  error,
  displayFileError,
  isViewSwitching,
  isLoadingFiles,
  isLoadingFile,
  isSaving,
  isStreaming,
  isExporting,
  isRunning,
  hasNodeDefinitions,
  hasFlowNodes,
  onSelectDraft,
  onSave,
  onExport,
  onRun,
}: WorkflowLiveToolbarProps) {
  const exportFilename = buildWorkflowExportFilename(activeDraft, activeDraftId)

  return (
    <div className="panel-toolbar">
      <div className="panel-toolbar-main">
        <div className="panel-toolbar-icon">
          <WorkflowIcon />
        </div>
        <div className="panel-toolbar-copy">
          <div className="panel-toolbar-label">Workflow</div>
          <div className="panel-toolbar-title">Live graph</div>
          <div className="panel-toolbar-meta">
            {isViewSwitching && (
              <span className="panel-toolbar-status">
                <Loader2 className="animate-spin" />
                Switching session...
              </span>
            )}
            {runStatus && <span>Run: {runStatus}</span>}
            {runError && <span className="panel-toolbar-error">{runError}</span>}
            {error && <span className="panel-toolbar-error">{error}</span>}
            {displayFileError && <span className="panel-toolbar-error">{displayFileError}</span>}
          </div>
        </div>
      </div>
      <div className="panel-toolbar-actions">
        <select
          value={activeDraftId || ''}
          disabled={!sessionId || isLoadingFiles || availableDrafts.length === 0 || isStreaming}
          onChange={(event) => onSelectDraft(event.target.value)}
          className="panel-toolbar-select"
        >
          {availableDrafts.length === 0 ? (
            <option value="">No workflow drafts</option>
          ) : (
            availableDrafts.map((draft) => (
              <option key={draft.id} value={draft.id}>
                {getDraftDisplayName(draft)}
              </option>
            ))
          )}
        </select>
        <button
          type="button"
          disabled={!sessionId || isLoadingFile || isStreaming || isSaving}
          onClick={() => void onSave()}
          className="panel-toolbar-btn"
        >
          {isSaving ? 'Saving...' : 'Save'}
        </button>
        <button
          type="button"
          disabled={!hasNodeDefinitions || isStreaming || isExporting}
          onClick={() => onExport(exportFilename)}
          className="panel-toolbar-btn"
        >
          {isExporting ? 'Exporting...' : 'Export'}
        </button>
        <button
          type="button"
          disabled={!sessionId || isStreaming || isRunning || !hasFlowNodes}
          onClick={() => void onRun()}
          className="panel-toolbar-btn panel-toolbar-btn--primary"
        >
          {isRunning ? 'Running...' : 'Run'}
        </button>
      </div>
    </div>
  )
}
