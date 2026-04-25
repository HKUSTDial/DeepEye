import { useEffect, useRef, useState } from 'react'
import { AlertCircle } from 'lucide-react'

import type { DataSource } from '../../types'
import type { NodeDefParam } from '../../stores/workflowNodes'
import {
  formatDatasourceOptionLabel,
  getDatasourcePlaceholder,
  getEmptyDatasourceMessage,
  isMultilineParam,
} from './workflowInspectorUtils'

interface WorkflowInspectorParamFieldProps {
  fieldKey: string
  nodeType: string | undefined
  paramDef?: NodeDefParam
  displayValue: string
  datasourceCategory: DataSource['category'] | null
  filteredDatasources: DataSource[]
  isLoadingDatasources: boolean
  datasourceError: string | null
  onRefreshDatasources: () => void
  onStartEditing: (key: string) => void
  onChange: (key: string, value: string) => void
  onBlur: (key: string) => void
  onDatasourceSelect: (key: string, value: string) => void
}

export function WorkflowInspectorParamField({
  fieldKey,
  nodeType,
  paramDef,
  displayValue,
  datasourceCategory,
  filteredDatasources,
  isLoadingDatasources,
  datasourceError,
  onRefreshDatasources,
  onStartEditing,
  onChange,
  onBlur,
  onDatasourceSelect,
}: WorkflowInspectorParamFieldProps) {
  const [datasourceMenuOpen, setDatasourceMenuOpen] = useState(false)
  const datasourcePickerRef = useRef<HTMLDivElement | null>(null)

  const required = paramDef?.required
  const isDatasourceIdField = fieldKey === 'datasource_id'
  const isMultilineField = isMultilineParam(nodeType, fieldKey)

  const selectedDatasource =
    filteredDatasources.find((datasource) => datasource.id === displayValue) || null
  const datasourcePlaceholder = getDatasourcePlaceholder(datasourceCategory)
  const datasourceTriggerLabel = selectedDatasource
    ? formatDatasourceOptionLabel(selectedDatasource)
    : displayValue
      ? 'Current value not in list'
      : datasourcePlaceholder
  const datasourceHint = selectedDatasource
    ? `${selectedDatasource.name} · ${selectedDatasource.category.toUpperCase()} · ${selectedDatasource.id}`
    : displayValue
      ? 'Current value is not in the loaded datasource list. You can still paste a valid UUID manually.'
      : getEmptyDatasourceMessage(datasourceCategory)

  useEffect(() => {
    if (!datasourceMenuOpen) return

    const onMouseDown = (event: MouseEvent) => {
      if (!datasourcePickerRef.current?.contains(event.target as globalThis.Node)) {
        setDatasourceMenuOpen(false)
      }
    }

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setDatasourceMenuOpen(false)
      }
    }

    document.addEventListener('mousedown', onMouseDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('mousedown', onMouseDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [datasourceMenuOpen])

  return (
    <div className="workflow-inspector-field">
      <label className="workflow-inspector-label">
        <span className="workflow-inspector-label-text">{fieldKey}</span>
        {required ? (
          <span className="workflow-inspector-label-required">
            <AlertCircle className="w-3 h-3" />
            required
          </span>
        ) : (
          <span className="workflow-inspector-label-optional">optional</span>
        )}
      </label>

      {isDatasourceIdField ? (
        <div className="workflow-inspector-datasource-picker">
          <div
            ref={datasourcePickerRef}
            className={`workflow-inspector-select-shell ${datasourceMenuOpen ? 'is-open' : ''}`}
          >
            <button
              type="button"
              className={`workflow-inspector-select-trigger ${datasourceMenuOpen ? 'is-open' : ''}`}
              onClick={() => {
                if (!isLoadingDatasources && filteredDatasources.length > 0) {
                  setDatasourceMenuOpen((current) => !current)
                }
              }}
              aria-haspopup="listbox"
              aria-expanded={datasourceMenuOpen}
              disabled={isLoadingDatasources || filteredDatasources.length === 0}
            >
              <span className="workflow-inspector-select-trigger-value">
                {isLoadingDatasources ? 'Loading datasources...' : datasourceTriggerLabel}
              </span>
              <span className="workflow-inspector-select-chevron" aria-hidden="true">
                <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8">
                  <path d="m5.5 7.5 4.5 5 4.5-5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </span>
            </button>

            {datasourceMenuOpen && (
              <div className="workflow-inspector-select-menu" role="listbox" aria-label="Datasource">
                {filteredDatasources.map((datasource) => {
                  const isSelected = datasource.id === displayValue
                  return (
                    <button
                      key={datasource.id}
                      type="button"
                      role="option"
                      aria-selected={isSelected}
                      className={`workflow-inspector-select-option ${isSelected ? 'is-selected' : ''}`}
                      onClick={() => {
                        onDatasourceSelect(fieldKey, datasource.id)
                        setDatasourceMenuOpen(false)
                      }}
                    >
                      <span className="workflow-inspector-select-option-copy">
                        <span className="workflow-inspector-select-option-label">{datasource.name}</span>
                        <span className="workflow-inspector-select-option-meta">
                          {datasource.category === 'file' ? 'FILE' : 'DATABASE'} · {datasource.id.slice(0, 8)}
                        </span>
                      </span>
                      {isSelected && (
                        <span className="workflow-inspector-select-option-check" aria-hidden="true">
                          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="m4.5 10 3.2 3.2L15.5 5.8" strokeLinecap="round" strokeLinejoin="round" />
                          </svg>
                        </span>
                      )}
                    </button>
                  )
                })}
              </div>
            )}
          </div>

          <input
            type="text"
            value={displayValue}
            placeholder={paramDef?.placeholder}
            onFocus={() => onStartEditing(fieldKey)}
            onChange={(event) => onChange(fieldKey, event.target.value)}
            onBlur={() => onBlur(fieldKey)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') {
                event.currentTarget.blur()
              }
            }}
            className="workflow-inspector-input workflow-inspector-input--mono"
          />

          <div className="workflow-inspector-datasource-row">
            <div className={`workflow-inspector-field-hint ${datasourceError ? 'is-error' : ''}`}>
              {datasourceError || datasourceHint}
            </div>
            <button
              type="button"
              onClick={onRefreshDatasources}
              disabled={isLoadingDatasources}
              className="workflow-inspector-field-action"
            >
              {isLoadingDatasources ? 'Loading...' : 'Refresh'}
            </button>
          </div>
        </div>
      ) : isMultilineField ? (
        <textarea
          value={displayValue}
          placeholder={paramDef?.placeholder}
          onFocus={() => onStartEditing(fieldKey)}
          onChange={(event) => onChange(fieldKey, event.target.value)}
          onBlur={() => onBlur(fieldKey)}
          className={`workflow-inspector-input workflow-inspector-textarea ${
            fieldKey === 'code' || fieldKey === 'query' ? 'workflow-inspector-input--mono' : ''
          }`}
          rows={fieldKey === 'code' ? 18 : fieldKey === 'query' ? 10 : 7}
          spellCheck={false}
        />
      ) : (
        <input
          type="text"
          value={displayValue}
          placeholder={paramDef?.placeholder}
          onFocus={() => onStartEditing(fieldKey)}
          onChange={(event) => onChange(fieldKey, event.target.value)}
          onBlur={() => onBlur(fieldKey)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') {
              event.currentTarget.blur()
            }
          }}
          className="workflow-inspector-input"
        />
      )}
    </div>
  )
}
