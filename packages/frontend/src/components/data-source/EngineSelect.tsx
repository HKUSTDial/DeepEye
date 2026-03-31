import { useEffect, useRef, useState } from 'react'

import { ENGINE_OPTIONS } from './dataSourceManagerUtils'
import { useLocale } from '../../locale'

interface EngineSelectProps {
  value: string
  onChange: (value: string) => void
}

export function EngineSelect({ value, onChange }: EngineSelectProps) {
  const { t } = useLocale()
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)

  const selected = ENGINE_OPTIONS.find((option) => option.value === value) ?? ENGINE_OPTIONS[0]

  useEffect(() => {
    if (!open) return

    const onMouseDown = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false)
      }
    }

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setOpen(false)
      }
    }

    document.addEventListener('mousedown', onMouseDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('mousedown', onMouseDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [open])

  return (
    <div className={`data-source-select-shell ${open ? 'is-open' : ''}`} ref={rootRef}>
      <button
        type="button"
        className={`data-source-field data-source-select-trigger ${open ? 'is-open' : ''}`}
        onClick={() => setOpen((current) => !current)}
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <span className="data-source-select-trigger-value">{selected.label}</span>
        <span className="data-source-select-chevron" aria-hidden="true">
          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8">
            <path d="m5.5 7.5 4.5 5 4.5-5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </span>
      </button>

      {open && (
        <div className="data-source-select-menu" role="listbox" aria-label={t('datasource.engine')}>
          {ENGINE_OPTIONS.map((option) => {
            const isSelected = option.value === value
            return (
              <button
                key={option.value}
                type="button"
                role="option"
                aria-selected={isSelected}
                className={`data-source-select-option ${isSelected ? 'is-selected' : ''}`}
                onClick={() => {
                  onChange(option.value)
                  setOpen(false)
                }}
              >
                <span className="data-source-select-option-label">{option.label}</span>
                {isSelected && (
                  <span className="data-source-select-option-check" aria-hidden="true">
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
  )
}
