import { useMemo, useState } from 'react'

import type { Message, ToolStep } from '../types'

interface EvidenceMatch {
  id: string
  title: string
  kind?: string
  matched_terms?: string[]
  evidence_status?: string
  sources?: Array<{ title: string; url: string; locator?: string }>
}

interface EvidenceTrace {
  status?: string
  assessment?: string
  matches?: EvidenceMatch[]
  notice?: string
}

function flattenSteps(steps: ToolStep[] = []): ToolStep[] {
  return steps.flatMap((step) => [step, ...flattenSteps(step.subSteps)])
}

function parseTrace(step?: ToolStep): EvidenceTrace | null {
  if (!step?.output) return null
  try {
    const parsed = JSON.parse(step.output) as EvidenceTrace
    return parsed && typeof parsed === 'object' ? parsed : null
  } catch {
    return null
  }
}

export default function AnalysisEvidence({ message }: { message: Message }) {
  const [expanded, setExpanded] = useState(false)
  const { trace, workflowStep } = useMemo(() => {
    const steps = flattenSteps(message.steps)
    const evidenceStep = steps.find((step) => step.name === 'analysis_knowledge')
    return { trace: parseTrace(evidenceStep), workflowStep: steps.find((step) => step.name === 'workflow_agent') }
  }, [message.steps])

  if (!trace || (!trace.matches?.length && trace.status !== 'no_match')) return null
  const matches = trace.matches || []
  const status = trace.status === 'matched' ? '已检索候选' : trace.status === 'no_match' ? '未匹配案例' : '知识库状态'

  return (
    <section className="analysis-evidence-card">
      <button
        type="button"
        className="analysis-evidence-toggle"
        onClick={() => setExpanded((current) => !current)}
        aria-expanded={expanded}
      >
        <span className="analysis-evidence-heading">
          <span className="analysis-evidence-mark" aria-hidden="true">↗</span>
          <span>
            <strong>分析依据</strong>
            <small>知识检索 · {matches.length} 张卡片</small>
          </span>
        </span>
        <span className="analysis-evidence-status">{status}<span className={`analysis-evidence-chevron ${expanded ? 'is-open' : ''}`}>⌄</span></span>
      </button>

      {expanded && (
        <div className="analysis-evidence-body">
          <div className="analysis-evidence-flow" aria-label="分析依据流程">
            <span>检索</span><i>→</i><span>适用性待审阅</span><i>→</i><span>{workflowStep ? '进入执行' : '方法回答'}</span>
          </div>
          {matches.map((match) => (
            <article className="analysis-evidence-match" key={match.id}>
              <div className="analysis-evidence-match-head">
                <span className="analysis-evidence-id">{match.id}</span>
                <div><strong>{match.title}</strong><small>{match.kind === 'enterprise_case' ? '企业案例' : '方法文档'} · {match.evidence_status || '证据状态未提供'}</small></div>
              </div>
              {match.matched_terms && match.matched_terms.length > 0 && (
                <div className="analysis-evidence-tags">{match.matched_terms.map((term) => <span key={term}>{term}</span>)}</div>
              )}
              {match.sources?.map((source) => (
                <a className="analysis-evidence-source" href={source.url} target="_blank" rel="noreferrer" key={source.url}>
                  <span>{source.title}</span><small>{source.locator || '打开来源'} ↗</small>
                </a>
              ))}
            </article>
          ))}
          <p className="analysis-evidence-notice">{trace.notice || '检索结果是参考候选，不代表已采用、已满足数据条件或已完成统计验证。'}</p>
        </div>
      )}
    </section>
  )
}
