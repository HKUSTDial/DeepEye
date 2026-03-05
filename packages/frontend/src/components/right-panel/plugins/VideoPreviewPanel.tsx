import { useEffect, useRef, useMemo, useState } from 'react'
import { Loader2 } from 'lucide-react'
import { useTheme } from '../../../hooks/useTheme'
import { useAuthStore } from '../../../stores/auth'
import { useWorkflowSessionsStore } from '../../../stores/workflowSessions'
import { config } from '../../../config'

interface VideoPreviewPanelProps {
  taskId?: string
  sessionId?: string | null
}

/** Task ID 格式：YYYYMMDD_HHMMSS，仅允许该格式用于 URL，避免误粘贴整段控制台输出 */
const TASK_ID_REGEX = /^\d{8}_\d{6}$/

/** 从粘贴内容中规范出合法 Task ID：精确匹配或从长文本中提取第一处 \d{8}_\d{6} */
function normalizePastedTaskId(raw: string): string | undefined {
  const trimmed = raw.trim()
  if (!trimmed) return undefined
  if (TASK_ID_REGEX.test(trimmed)) return trimmed
  const extracted = trimmed.match(/(\d{8}_\d{6})/)
  return extracted ? extracted[1] : undefined
}

/** 从工作流输出中提取 Task ID（支持 JSON 与纯文本） */
function extractTaskIdFromOutput(runOutput: string): string | undefined {
  if (!runOutput || typeof runOutput !== 'string') return undefined
  const taskIdLabelMatch = runOutput.match(/Task ID:\s*(\d{8}_\d{6})/i)
  if (taskIdLabelMatch) return taskIdLabelMatch[1]
  try {
    const data = JSON.parse(runOutput)
    if (data && typeof data === 'object') {
      for (const key of Object.keys(data)) {
        const node = data[key]
        if (node && typeof node === 'object' && typeof node.task_id === 'string') return node.task_id
        if (node && typeof node === 'object' && node.video_info?.task_id) return node.video_info.task_id
      }
    }
  } catch {
    // not JSON, continue
  }
  const taskIdMatch = runOutput.match(/(\d{8}_\d{6})/)
  return taskIdMatch ? taskIdMatch[1] : undefined
}

const STEP_LABELS = [
  { icon: '📹', label: 'Generate config', index: 0 },
  { icon: '🎵', label: 'Audio & timeline', index: 1 },
  { icon: '💾', label: 'Save config', index: 2 },
  { icon: '🎬', label: 'Render components', index: 3 },
]

const STEP_MESSAGES: Record<number, string> = {
  0: '📹 Step 1/4: Generating video configuration...',
  1: '🎵 Step 2/4: Generating audio and aligning timeline...',
  2: '💾 Step 3/4: Saving configuration file...',
  3: '🎬 Step 4/4: Rendering video components...',
}

function getLogEntryType(message: string): 'success' | 'warn' | 'error' | 'info' | null {
  const t = message.trim()
  if (t.includes('✅') || t.includes('✓')) return 'success'
  if (t.includes('⚠️') || t.includes('Warning')) return 'warn'
  if (t.includes('❌') || t.includes('Error') || t.includes('Failed')) return 'error'
  if (t.includes('📊') || t.includes('Step') || /^\s*\[?\d+\/\d+\]/.test(t)) return 'info'
  return null
}

function withQueryParam(url: string, key: string, value?: string | null): string {
  if (!value) return url
  try {
    const u = new URL(url, typeof window !== 'undefined' ? window.location.origin : 'http://localhost')
    u.searchParams.set(key, value)
    return /^https?:\/\//i.test(url) ? u.toString() : `${u.pathname}${u.search}${u.hash}`
  } catch {
    const sep = url.includes('?') ? '&' : '?'
    return `${url}${sep}${encodeURIComponent(key)}=${encodeURIComponent(value)}`
  }
}

/**
 * Video Preview panel: Doc Docker only.
 * - When video_preview_ready: show iframe (container URL).
 * - When container deploying: show "starting…".
 * - When generating: show progress (steps + logs).
 * - Otherwise: show empty state (no manual Task ID / in-page player).
 */
export function VideoPreviewPanel({ taskId, sessionId }: VideoPreviewPanelProps) {
  const { theme } = useTheme()
  const accessToken = useAuthStore((state) => state.accessToken)
  const isDark = theme === 'dark'
  const videoProgressLogsRef = useRef<HTMLDivElement | null>(null)
  const [pastedTaskId, setPastedTaskId] = useState('')

  const sessionState = useWorkflowSessionsStore((state) =>
    sessionId ? state.sessions[sessionId] : undefined,
  )
  const runOutput = sessionState?.runOutput ?? ''
  const videoProgress = sessionState?.videoProgress ?? { visible: false, step: 0, percent: 0, logs: [] }
  const runStatus = (sessionState?.runStatus as string | null | undefined) ?? null
  const runError = sessionState?.runError ?? null
  const videoPreviewUrl = sessionState?.videoPreviewUrl ?? null
  const [isPreviewReady, setIsPreviewReady] = useState(false)
  const [isCheckingPreview, setIsCheckingPreview] = useState(false)
  const previewCheckIntervalRef = useRef<number | null>(null)

  // 与仪表盘一致：从 node 输出收集 video_url，取最后一个并拼完整 URL
  const videoUrlsFromNode = useMemo(() => {
    if (!sessionState?.nodeStatus) return []
    const urls: { nodeId: string; url: string }[] = []
    Object.entries(sessionState.nodeStatus).forEach(([nodeId, statusInfo]) => {
      const info = statusInfo as { outputs?: Record<string, unknown> }
      const u = info.outputs?.video_url
      if (typeof u === 'string' && u) urls.push({ nodeId, url: u })
    })
    return urls
  }, [sessionState?.nodeStatus])

  const latestVideoUrlFromNode = videoUrlsFromNode[videoUrlsFromNode.length - 1]?.url
  const fullPreviewUrlFromNode = useMemo(() => {
    if (!latestVideoUrlFromNode) return ''
    if (latestVideoUrlFromNode.startsWith('http')) return latestVideoUrlFromNode
    const base = config.api.baseUrl.replace('/api/v1', '')
    return `${base}${latestVideoUrlFromNode.startsWith('/') ? '' : '/'}${latestVideoUrlFromNode}`
  }, [latestVideoUrlFromNode])

  const pastedNormalized = normalizePastedTaskId(pastedTaskId)
  const displayTaskId = taskId || extractTaskIdFromOutput(runOutput) || pastedNormalized || undefined

  // 约定 URL：有 taskId 但尚无事件/节点输出时使用（与后端容器命名一致）
  const constructedPreviewUrl =
    displayTaskId && typeof window !== 'undefined'
      ? `${window.location.origin}/video-previews/deepeye-video-${displayTaskId}/`
      : null

  // 统一预览 URL 优先级：事件 > 节点输出 > 约定 URL（与仪表盘逻辑一致）
  const effectivePreviewUrl =
    videoPreviewUrl || fullPreviewUrlFromNode || constructedPreviewUrl || null
  const effectivePreviewUrlWithAuth = useMemo(() => {
    if (!effectivePreviewUrl) return null
    let next = effectivePreviewUrl
    next = withQueryParam(next, 'session_id', sessionId ?? undefined)
    next = withQueryParam(next, 'token', accessToken ?? undefined)
    return next
  }, [effectivePreviewUrl, sessionId, accessToken])

  // 与仪表盘一致：有预览 URL 时轮询就绪，就绪后再显示 iframe。用 GET 避免 Vite 对 HEAD 返回异常导致 502
  useEffect(() => {
    if (!effectivePreviewUrlWithAuth) {
      setIsPreviewReady(false)
      return
    }
    setIsPreviewReady(false)

    const checkReady = async () => {
      setIsCheckingPreview(true)
      try {
        // GET 更可靠：Vite 对 HEAD 可能未正确响应，nginx 易报 502
        const res = await fetch(effectivePreviewUrlWithAuth, { method: 'GET', cache: 'no-store' })
        // 仅当来自「预览路由」且 200 时才视为就绪，避免误把主站首页当预览（若被错误转发到前端会缺 X-Video-Preview）
        const fromPreviewRoute = res.headers.get('X-Video-Preview') === '1'
        if (res.ok && fromPreviewRoute) {
          setIsPreviewReady(true)
          if (previewCheckIntervalRef.current) {
            window.clearInterval(previewCheckIntervalRef.current)
            previewCheckIntervalRef.current = null
          }
        }
      } catch {
        // 502/网络错误时继续轮询，容器可能仍在启动
      } finally {
        setIsCheckingPreview(false)
      }
    }

    // 首次延迟 3s 再开始轮询，减少容器刚启动时的 502
    const t = window.setTimeout(() => {
      checkReady()
      previewCheckIntervalRef.current = window.setInterval(checkReady, 2000)
    }, 3000)

    return () => {
      window.clearTimeout(t)
      if (previewCheckIntervalRef.current) {
        window.clearInterval(previewCheckIntervalRef.current)
        previewCheckIntervalRef.current = null
      }
    }
  }, [effectivePreviewUrlWithAuth])

  // 控制台调试信息，便于排查预览不加载
  useEffect(() => {
    const prefix = '[VideoPreview]'
    if (effectivePreviewUrlWithAuth) {
      console.info(prefix, 'Preview URL (will poll until ready):', {
        source: videoPreviewUrl ? 'event' : fullPreviewUrlFromNode ? 'node output' : 'constructed',
        url: effectivePreviewUrlWithAuth,
      })
      return
    }
    if (sessionId != null || (runOutput?.length ?? 0) > 0) {
      console.info(prefix, 'No preview URL (paste Task ID or wait for event):', {
        sessionId: sessionId ?? null,
        taskIdFromProps: taskId ?? null,
        extractedFromRunOutput: extractTaskIdFromOutput(runOutput) ?? null,
        pastedTaskId: pastedNormalized ?? (pastedTaskId.trim() || null),
        runOutputLength: runOutput?.length ?? 0,
      })
    }
  }, [effectivePreviewUrlWithAuth, videoPreviewUrl, fullPreviewUrlFromNode, sessionId, taskId, pastedNormalized, pastedTaskId, runOutput])

  useEffect(() => {
    if (videoProgress.visible && videoProgress.logs.length > 0 && videoProgressLogsRef.current) {
      videoProgressLogsRef.current.scrollTop = videoProgressLogsRef.current.scrollHeight
    }
  }, [videoProgress.visible, videoProgress.logs.length])

  const runInProgress = runStatus === 'running' || runStatus === null
  const runFailed = runStatus === 'failed'

  // 1) 有预览 URL：轮询就绪后显示 iframe（与仪表盘一致，避免 502/主应用）
  if (effectivePreviewUrlWithAuth) {
    return (
      <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', background: isDark ? '#0f1419' : '#f8fafc' }}>
        <div style={{
          padding: '8px 16px',
          borderBottom: `1px solid ${isDark ? '#334155' : '#e2e8f0'}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          fontSize: 12,
          color: isDark ? '#94a3b8' : '#64748b',
          background: isDark ? 'rgba(15,23,42,0.8)' : '#ffffff',
          flexShrink: 0,
        }}>
          <span style={{ fontWeight: 600, color: isDark ? '#e2e8f0' : '#1e293b' }}>Video Preview</span>
          {(!isPreviewReady || isCheckingPreview) && (
            <span style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: isDark ? '#94a3b8' : '#64748b' }}>
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Waiting for preview…
            </span>
          )}
          {isPreviewReady && (
            <a
              href={effectivePreviewUrlWithAuth}
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: isDark ? '#818cf8' : '#4f46e5', textDecoration: 'none', fontSize: 11 }}
            >
              Open in new tab ↗
            </a>
          )}
        </div>
        {!isPreviewReady ? (
          <div style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 12,
            background: isDark ? '#0f1419' : '#f8fafc',
            color: isDark ? '#e2e8f0' : '#1e293b',
          }}>
            <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
            <p className="text-sm text-slate-500">Starting preview container…</p>
            <p className="text-xs text-slate-400 max-w-[260px] text-center">
              This usually takes 15–30 seconds. The panel will show the video when ready.
            </p>
            <p className="text-xs text-slate-400 max-w-[300px] text-center mt-2" style={{ marginTop: 8 }}>
              若超过 1 分钟仍不出现，请先构建镜像：<br />
              <code style={{ fontSize: 10 }}>docker build -f docker/Dockerfile.video-preview -t deepeye-video-preview:latest .</code>
            </p>
          </div>
        ) : (
          <iframe
            src={effectivePreviewUrlWithAuth}
            style={{ flex: 1, border: 'none', width: '100%' }}
            title="Video Preview"
            allow="autoplay"
          />
        )}
      </div>
    )
  }

  // 2) Generating: progress (steps + logs)
  if (sessionId && videoProgress.visible && runInProgress) {
    return (
      <div style={{
        padding: '16px',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
        background: isDark ? 'var(--panel-bg)' : '#f8fafc',
        height: '100%',
      }}>
        <div style={{
          padding: '12px 16px',
          borderRadius: '12px',
          border: `1px solid ${isDark ? '#334155' : '#e2e8f0'}`,
          background: isDark ? 'rgba(15,23,42,0.6)' : '#ffffff',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <span style={{ fontWeight: 600, fontSize: 14, color: isDark ? '#e2e8f0' : '#1e293b' }}>
              {runFailed ? 'Video generation failed' : 'Generating data video'}
            </span>
            {!runFailed && (
              <span style={{ fontSize: 12, fontWeight: 500, color: isDark ? '#818cf8' : '#4f46e5' }}>
                {videoProgress.percent}%
              </span>
            )}
            {runFailed && (
              <span style={{ fontSize: 12, fontWeight: 500, color: isDark ? '#ef4444' : '#dc2626' }}>
                Failed
              </span>
            )}
          </div>
          {runError && (
            <div style={{
              padding: '8px 12px',
              borderRadius: 8,
              background: isDark ? 'rgba(239, 68, 68, 0.1)' : '#fee2e2',
              border: `1px solid ${isDark ? '#ef4444' : '#dc2626'}`,
              marginBottom: 12,
              color: isDark ? '#fca5a5' : '#991b1b',
              fontSize: 12,
            }}>
              <strong>Error:</strong> {runError}
            </div>
          )}
          <div style={{
            height: 8,
            width: '100%',
            borderRadius: 4,
            overflow: 'hidden',
            background: isDark ? '#334155' : '#e2e8f0',
            marginBottom: 12,
          }}>
            <div
              style={{
                height: '100%',
                width: `${videoProgress.percent}%`,
                background: '#6366f1',
                borderRadius: 4,
                transition: 'width 0.3s',
              }}
            />
          </div>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            gap: 4,
            padding: '8px 12px',
            borderRadius: 8,
            background: isDark ? 'rgba(30,41,59,0.5)' : '#f1f5f9',
            marginBottom: 12,
          }}>
            {STEP_LABELS.map(({ icon, label, index }) => (
              <div
                key={index}
                style={{
                  flex: 1,
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: 2,
                  opacity: videoProgress.step >= index ? 1 : 0.4,
                }}
              >
                <span style={{ fontSize: 16 }}>{icon}</span>
                <span style={{
                  fontSize: 10,
                  fontWeight: videoProgress.step === index ? 600 : 400,
                  color: videoProgress.step === index
                    ? (isDark ? '#22d3ee' : '#4f46e5')
                    : videoProgress.step > index
                      ? (isDark ? '#34d399' : '#059669')
                      : (isDark ? '#64748b' : '#94a3b8'),
                }}>
                  {label}
                </span>
              </div>
            ))}
          </div>
          <div style={{
            marginTop: 16,
            paddingTop: 16,
            borderTop: `1px solid ${isDark ? '#334155' : '#e2e8f0'}`,
          }}>
            <div
              ref={videoProgressLogsRef}
              style={{
                maxHeight: 300,
                overflowY: 'auto',
                padding: 12,
                borderRadius: 8,
                border: `1px solid ${isDark ? '#334155' : '#e2e8f0'}`,
                fontFamily: "'JetBrains Mono', 'Consolas', 'Monaco', 'Courier New', monospace",
                fontSize: 12,
                lineHeight: 1.6,
                background: isDark ? 'rgba(15,23,42,0.8)' : '#ffffff',
                color: isDark ? '#cbd5e1' : '#1e293b',
              }}
            >
              {videoProgress.logs.length === 0 ? (
                <div style={{ padding: '8px 0' }}>
                  {(videoProgress.step > 0 || videoProgress.percent > 0) && STEP_MESSAGES[videoProgress.step] ? (
                    <>
                      <div
                        style={{
                          display: 'flex',
                          gap: 12,
                          padding: '4px 0',
                          color: isDark ? '#818cf8' : '#4f46e5',
                          fontSize: 12,
                          fontFamily: "'JetBrains Mono', 'Consolas', monospace",
                        }}
                      >
                        <span style={{ color: isDark ? '#94a3b8' : '#64748b', minWidth: 80 }}>—</span>
                        <span>{STEP_MESSAGES[videoProgress.step]}</span>
                      </div>
                      <div style={{ color: isDark ? '#64748b' : '#94a3b8', fontStyle: 'italic', fontSize: 11, marginTop: 12, textAlign: 'center' }}>
                        Live log lines will appear here when the backend sends progress.
                      </div>
                    </>
                  ) : (
                    <div style={{ color: isDark ? '#64748b' : '#94a3b8', fontStyle: 'italic', textAlign: 'center', padding: 20 }}>
                      Progress will appear here (workflow live output).
                    </div>
                  )}
                </div>
              ) : (
                videoProgress.logs.slice(-50).map((log, idx, arr) => {
                  const type = getLogEntryType(log.message)
                  const isLast = idx === arr.length - 1
                  const msgColor =
                    type === 'success'
                      ? isDark ? '#34d399' : '#059669'
                      : type === 'warn'
                        ? isDark ? '#fbbf24' : '#d97706'
                        : type === 'error'
                          ? isDark ? '#f87171' : '#dc2626'
                          : type === 'info'
                            ? isDark ? '#818cf8' : '#4f46e5'
                            : isDark ? '#cbd5e1' : '#475569'
                  return (
                    <div
                      key={log.id}
                      style={{
                        display: 'flex',
                        gap: 12,
                        padding: '4px 0',
                        borderBottom: isLast ? 'none' : `1px solid ${isDark ? '#334155' : '#f1f5f9'}`,
                      }}
                    >
                      <span
                        style={{
                          color: isDark ? '#94a3b8' : '#64748b',
                          minWidth: 80,
                          flexShrink: 0,
                          fontSize: 11,
                        }}
                      >
                        {log.time}
                      </span>
                      <span style={{ wordBreak: 'break-word', flex: 1, color: msgColor }}>
                        {log.message}
                      </span>
                    </div>
                  )
                })
              )}
            </div>
          </div>
        </div>
      </div>
    )
  }

  // 3) Empty state: no preview URL — show hint and paste Task ID
  return (
    <div style={{
      width: '100%',
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 16,
      padding: 24,
      background: isDark ? '#0f1419' : '#f8fafc',
      color: isDark ? '#94a3b8' : '#64748b',
      textAlign: 'center',
    }}>
      <div style={{ fontSize: 32 }}>🎬</div>
      <div style={{ fontWeight: 600, fontSize: 15, color: isDark ? '#e2e8f0' : '#1e293b' }}>
        Video Preview
      </div>
      <div style={{ fontSize: 13, maxWidth: 320 }}>
        If the preview did not load automatically, paste the <strong>Task ID</strong> from the chat (e.g. 20260302_121928) and open the preview.
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, width: '100%', maxWidth: 320 }}>
        <input
          type="text"
          value={pastedTaskId}
          onChange={(e) => setPastedTaskId(e.target.value)}
          placeholder="e.g. 20260302_121928"
          style={{
            padding: '10px 12px',
            border: `1px solid ${isDark ? '#334155' : '#e2e8f0'}`,
            borderRadius: 8,
            fontSize: 14,
            fontFamily: 'monospace',
            background: isDark ? 'rgba(30,41,59,0.8)' : '#fff',
            color: isDark ? '#e2e8f0' : '#1e293b',
          }}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && pastedNormalized) {
              setPastedTaskId(pastedNormalized)
            }
          }}
        />
        <button
          type="button"
          onClick={() => pastedNormalized && setPastedTaskId(pastedNormalized)}
          disabled={!pastedNormalized}
          style={{
            padding: '10px 16px',
            background: pastedNormalized ? (isDark ? '#4f46e5' : '#6366f1') : (isDark ? '#334155' : '#e2e8f0'),
            color: '#fff',
            border: 'none',
            borderRadius: 8,
            fontSize: 14,
            fontWeight: 500,
            cursor: pastedNormalized ? 'pointer' : 'not-allowed',
          }}
        >
          Open preview
        </button>
      </div>
    </div>
  )
}
