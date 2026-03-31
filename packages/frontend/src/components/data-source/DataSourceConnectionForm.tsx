import { EngineSelect } from './EngineSelect'
import { URI_EXAMPLES } from './dataSourceManagerUtils'

type ConnectionFormState = {
  name: string
  type: string
  connection_string: string
}

interface DataSourceConnectionFormProps {
  form: ConnectionFormState
  onChange: (next: ConnectionFormState) => void
  statusMessage: string | null
  onClearStatus: () => void
  onTest: () => void
  onSubmit: () => void
  onCancel?: () => void
  isTesting: boolean
  isSubmitting: boolean
  submitLabel: string
  testingLabel?: string
  idleTestLabel?: string
  intro?: {
    kicker: string
    copy: string
  }
}

export function DataSourceConnectionForm({
  form,
  onChange,
  statusMessage,
  onClearStatus,
  onTest,
  onSubmit,
  onCancel,
  isTesting,
  isSubmitting,
  submitLabel,
  testingLabel = 'Testing...',
  idleTestLabel = 'Test connection',
  intro,
}: DataSourceConnectionFormProps) {
  return (
    <>
      {intro && (
        <div className="data-source-form-intro">
          <span className="data-source-form-kicker">{intro.kicker}</span>
          <span className="data-source-form-copy">{intro.copy}</span>
        </div>
      )}

      <div className="data-source-form-grid">
        <label className="data-source-field-group">
          <span className="data-source-field-label">Display name</span>
          <input
            value={form.name}
            onChange={(event) => {
              onChange({ ...form, name: event.target.value })
              onClearStatus()
            }}
            placeholder="Revenue warehouse"
            className="data-source-field"
          />
        </label>
        <label className="data-source-field-group">
          <span className="data-source-field-label">Engine</span>
          <EngineSelect
            value={form.type}
            onChange={(nextType) => {
              onChange({ ...form, type: nextType })
              onClearStatus()
            }}
          />
        </label>
      </div>

      <label className="data-source-field-group">
        <span className="data-source-field-label">Connection URI</span>
        <textarea
          value={form.connection_string}
          onChange={(event) => {
            onChange({ ...form, connection_string: event.target.value })
            onClearStatus()
          }}
          placeholder={URI_EXAMPLES[form.type] || 'Connection URI'}
          className="data-source-field data-source-field-mono data-source-textarea"
          rows={3}
        />
      </label>

      <div className="data-source-uri-help">
        <span className="data-source-uri-label">Example</span>
        <code className="data-source-uri-example">{URI_EXAMPLES[form.type] || 'Connection URI'}</code>
      </div>

      {statusMessage && (
        <div className="data-source-success">
          <span>{statusMessage}</span>
        </div>
      )}

      <div className={onCancel ? 'data-source-subpanel-actions' : 'data-source-form-footer'}>
        <button
          type="button"
          onClick={onTest}
          disabled={isTesting || isSubmitting}
          className="data-source-secondary-btn"
        >
          {isTesting ? testingLabel : idleTestLabel}
        </button>
        <button
          type="button"
          onClick={onSubmit}
          disabled={isSubmitting}
          className="data-source-submit-btn"
        >
          {isSubmitting ? 'Saving...' : submitLabel}
        </button>
        {onCancel && (
          <button type="button" onClick={onCancel} className="data-source-secondary-btn">
            Cancel
          </button>
        )}
      </div>
    </>
  )
}
