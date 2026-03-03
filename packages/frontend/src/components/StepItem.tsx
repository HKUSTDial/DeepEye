import { useState, useMemo } from 'react'
import type { ToolStep } from '../types'
import './StepItem.css'

interface StepItemProps {
  step: ToolStep
}

export default function StepItem({ step }: StepItemProps) {
  const [expanded, setExpanded] = useState(false)
  const isRunning = useMemo(() => step.status === 'running', [step.status])
  const nodeStateClass = useMemo(() => {
    if (step.status === 'completed') return 'done'
    if (step.status === 'error') return 'error'
    return 'running'
  }, [step.status])

  // Thought Step
  if (step.type === 'thought') {
    return (
      <div className="tool-thought">
        {isRunning ? (
          <span className="thinking-dots">
            <span></span>
            <span></span>
            <span></span>
          </span>
        ) : (
          <span className="tool-thought-dot">·</span>
        )}
        <span className="tool-thought-text">{step.thought}</span>
      </div>
    )
  }

  // Tool Step
  return (
    <div className="tool-tree-item">
      <button onClick={() => setExpanded(!expanded)} className="tool-header">
        <span className={`tool-node ${nodeStateClass}`}></span>
        <span className="tool-name">{step.name}</span>
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
      </button>

      {/* Details */}
      {expanded && (
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
                <StepItem key={`sub-${idx}`} step={sub} />
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

