import { useEffect } from 'react'
import { createPortal } from 'react-dom'

import DataSourceManager from '../DataSourceManager'
import { useWorkspaceUiStore } from '../../stores/workspaceUi'
import type { DataSource } from '../../types'
import { useLocale } from '../../locale'
import '../ChatBox.css'

interface GlobalDataSourceManagerModalProps {
  onDataSourcesChange?: (sources: DataSource[]) => void
}

export function GlobalDataSourceManagerModal({
  onDataSourcesChange,
}: GlobalDataSourceManagerModalProps) {
  const { t } = useLocale()
  const isOpen = useWorkspaceUiStore((state) => state.isDataSourceManagerOpen)
  const closeDataSourceManager = useWorkspaceUiStore((state) => state.closeDataSourceManager)

  useEffect(() => {
    if (!isOpen) return

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        closeDataSourceManager()
      }
    }

    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    document.addEventListener('keydown', onKeyDown)

    return () => {
      document.body.style.overflow = previousOverflow
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [isOpen, closeDataSourceManager])

  if (!isOpen || typeof document === 'undefined') {
    return null
  }

  return createPortal(
    <div
      className="chat-datasource-modal-overlay"
      onClick={closeDataSourceManager}
    >
      <div
        className="chat-datasource-modal"
        onClick={(event) => event.stopPropagation()}
      >
        <button
          type="button"
          className="chat-datasource-modal-close"
          onClick={closeDataSourceManager}
          aria-label={t('common.close')}
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
          </svg>
        </button>
        <DataSourceManager
          variant="modal"
          onDataSourcesChange={onDataSourcesChange}
        />
      </div>
    </div>,
    document.body,
  )
}
