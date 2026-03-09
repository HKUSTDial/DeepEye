import { useState, useMemo } from 'react'
import type { ToolStep } from '../types'
import './StepItem.css'

interface StepItemProps {
  step: ToolStep
  depth?: number
}

function formatSourceLabel(source?: string) {
  const raw = source?.trim() || 'tool'
  return raw
    .replace(/[._]+/g, ' ')
    .split(/\s+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

export default function StepItem({ step, depth = 0 }: StepItemProps) {
  const [expanded, setExpanded] = useState(false)
  const isRunning = useMemo(() => step.status === 'running', [step.status])
  const hasDetails = useMemo(
    () => Boolean(step.input || step.output || (step.subSteps && step.subSteps.length > 0)),
    [step.input, step.output, step.subSteps],
  )
  const nodeStateClass = useMemo(() => {
    if (step.status === 'completed') return 'done'
    if (step.status === 'error') return 'error'
    return 'running'
  }, [step.status])
  const statusLabel = useMemo(() => {
    if (step.status === 'completed') return 'Done'
    if (step.status === 'error') return 'Error'
    return 'Running'
  }, [step.status])
  const sourceLabel = useMemo(() => formatSourceLabel(step.source), [step.source])

  // Thought Step
  if (step.type === 'thought') {
    return (
      <div className={`tool-thought ${isRunning ? 'running' : ''}`}>
        <span className="tool-thought-mark">
          {isRunning ? (
            <span className="thinking-dots">
              <span></span>
              <span></span>
              <span></span>
            </span>
          ) : (
            <span className="tool-thought-dot">·</span>
          )}
        </span>
        <span className="tool-thought-body">
          <span className="tool-thought-label">{isRunning ? 'Thinking' : 'Thought'}</span>
          <span className="tool-thought-text">{step.thought}</span>
        </span>
      </div>
    )
  }

  const headerContent = (
    <>
      <span className={`tool-node ${nodeStateClass}`}></span>
      <span className="tool-main">
        <span className="tool-title-row">
          <span className="tool-name">{step.name}</span>
          <span className={`tool-status ${nodeStateClass}`}>{statusLabel}</span>
        </span>
        <span className="tool-meta-row">
          <span className="tool-source">{sourceLabel}</span>
        </span>
      </span>
      {hasDetails && (
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className={`tool-chevron ${expanded ? 'expanded' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth="2"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      )}
    </>
  )

  // Tool Step
  return (
    <div className={`tool-tree-item ${depth > 0 ? 'is-nested' : ''}`}>
      {hasDetails ? (
        <button
          onClick={() => setExpanded(!expanded)}
          className="tool-header"
          aria-expanded={expanded}
          type="button"
        >
          {headerContent}
        </button>
      ) : (
        <div className="tool-header static">{headerContent}</div>
      )}

      {/* Details */}
      {hasDetails && expanded && (
        <div className="tool-details">
          {step.input && (
            <div className="tool-block">
              <div className="tool-label">Input</div>
              <pre className="tool-pre">{step.input}</pre>
            </div>
          )}

          {step.subSteps && step.subSteps.length > 0 && (
            <div className="tool-children">
              {step.subSteps.map((sub, idx) => (
                <StepItem key={`sub-${idx}`} step={sub} depth={depth + 1} />
              ))}
            </div>
          )}

          {step.output && (
            <div className="tool-block">
              <div className="tool-label">Output</div>
              <pre className="tool-pre">{step.output}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
