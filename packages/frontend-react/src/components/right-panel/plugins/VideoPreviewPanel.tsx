import { useEffect, useRef, useState, useMemo } from 'react'
import { useTheme } from '../../../hooks/useTheme'
import type React from 'react'
import { Player } from '@remotion/player'
import { getVideoConfig, getVideoConfigByPath, type VideoConfig } from '../../../api/video'
import { getFallbackConfig, FALLBACK_TASK_IDS } from '../../../api/videoFallbackConfigs'
import { registerVideoByTaskId, getRegisteredVideo } from '../../../api/videoRegistration'
import { VideoComposer } from '../../video/VideoComposer'
import { useWorkflowSessionsStore } from '../../../stores/workflowSessions'

const KNOWN_PREFIXES = ['分析学生成绩分布生成数据视频', 'Createavideoreportex']

interface VideoPreviewPanelProps {
  configPath?: string
  taskId?: string
  sessionId?: string | null
}

/**
 * 从配置文件的 meta.title 提取 componentPrefix
 * 逻辑：去掉空格和特殊字符，只保留字母数字，截取前20个字符
 */
function extractComponentPrefix(config: VideoConfig): string {
  const title = config.meta.title || ''
  if (!title) {
    return '分析学生成绩分布生成数据视频' // 默认模板
  }
  
  // 去掉空格和特殊字符，只保留“字母/数字”（包含中文等非 ASCII 字母）
  // 与后端 `str.isalnum()` 的行为保持一致
  const datasetName = title.replace(/[^\p{L}\p{N}]/gu, '')
  // 如果太长，截取前20个字符
  const prefix = datasetName.length > 20 ? datasetName.substring(0, 20) : datasetName
  return prefix || '分析学生成绩分布生成数据视频'
}

// 视频预览组件（使用 VideoComposer，可传入已注册的场景组件实现按 id 预览）
function VideoPreviewComponent({
  config,
  taskId,
  sessionId,
  registeredSceneComponents,
}: {
  config: VideoConfig
  taskId?: string | null
  sessionId?: string | null
  registeredSceneComponents?: Record<string, React.FC<any>> | null
}) {
  const componentPrefix = useMemo(() => extractComponentPrefix(config), [config])

  return (
    <VideoComposer
      configJson={config}
      componentPrefix={componentPrefix}
      taskId={taskId}
      sessionId={sessionId}
      registeredSceneComponents={registeredSceneComponents}
    />
  )
}

/** 从任意字符串中提取 taskId / configPath（用于 JSON 内的 stdout 等字段） */
function extractVideoInfoFromString(str: string): { taskId?: string; configPath?: string } | null {
  if (typeof str !== 'string' || !str) return null
  const configPathMatch = str.match(/video_configs[/\\]generated_(\d{8}_\d{6})_aligned\.json|generated_(\d{8}_\d{6})_aligned\.json/)
  if (configPathMatch) {
    const taskId = configPathMatch[1] || configPathMatch[2]
    return taskId ? { taskId, configPath: undefined } : null
  }
  const taskIdLabelMatch = str.match(/Task ID:\s*(\d{8}_\d{6})/i)
  if (taskIdLabelMatch) return { taskId: taskIdLabelMatch[1], configPath: undefined }
  const taskIdMatch = str.match(/(\d{8}_\d{6})/)
  if (taskIdMatch) return { taskId: taskIdMatch[1], configPath: undefined }
  return null
}

/**
 * 从工作流输出中提取视频信息。
 * 支持：1) 节点输出中的 video_info / config_path / video_path；2) 节点输出中任意字符串（如 stdout）；3) 整段 runOutput 文本。
 */
function extractVideoInfoFromOutput(runOutput: string): { taskId?: string; configPath?: string } {
  if (!runOutput) return {}

  try {
    const outputs = JSON.parse(runOutput)
    if (outputs && typeof outputs === 'object') {
      for (const nodeId of Object.keys(outputs)) {
        const nodeOutputs = outputs[nodeId]
        if (!nodeOutputs || typeof nodeOutputs !== 'object') continue

        const videoInfo = nodeOutputs.video_info
        const configPath = nodeOutputs.config_path
        const videoPath = nodeOutputs.video_path

        let taskId: string | undefined
        if (videoInfo?.task_id) {
          taskId = videoInfo.task_id
        } else if (typeof videoPath === 'string') {
          const m = videoPath.match(/(?:claude_tsx_animated|video_components)[/\\](\d{8}_\d{6})/)
          taskId = m ? m[1] : undefined
        } else if (typeof configPath === 'string') {
          const m = configPath.match(/generated_(\d{8}_\d{6})_aligned\.json/)
          taskId = m ? m[1] : undefined
        }

        if (videoInfo || configPath || videoPath) {
          return { taskId, configPath: typeof configPath === 'string' ? configPath : undefined }
        }

        // 节点没有 video 字段时，在其所有字符串值中搜索（如 stdout 里打印了 Task ID）
        for (const key of Object.keys(nodeOutputs)) {
          const v = nodeOutputs[key]
          if (typeof v === 'string') {
            const fromField = extractVideoInfoFromString(v)
            if (fromField) return fromField
          }
        }
      }
    }
  } catch {
    // 非 JSON，下面用文本方式提取
  }

  // 整段文本中提取（兼容非 JSON 或视频信息只在某段文本里的情况）
  const fromText = extractVideoInfoFromString(runOutput)
  if (fromText) return fromText

  return {}
}

const STEP_LABELS = [
  { icon: '📹', label: 'Generate config', index: 0 },
  { icon: '🎵', label: 'Audio & timeline', index: 1 },
  { icon: '💾', label: 'Save config', index: 2 },
  { icon: '🎬', label: 'Render components', index: 3 },
]

/** 根据日志内容返回条目类型，用于高亮 */
function getLogEntryType(message: string): 'success' | 'warn' | 'error' | 'info' | null {
  const t = message.trim()
  if (t.includes('✅') || t.includes('✓') || /完成!?/.test(t)) return 'success'
  if (t.includes('⚠️') || t.includes('Warning') || t.includes('未找到')) return 'warn'
  if (t.includes('❌') || t.includes('Error') || t.includes('Failed') || t.includes('失败')) return 'error'
  if (t.includes('📊') || t.includes('Step') || /^\s*\[?\d+\/\d+\]/.test(t) || t.includes('耗时')) return 'info'
  return null
}

export function VideoPreviewPanel({ configPath, taskId, sessionId }: VideoPreviewPanelProps) {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const videoProgressLogsRef = useRef<HTMLDivElement | null>(null)

  const [config, setConfig] = useState<VideoConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [manualTaskId, setManualTaskId] = useState<string>('')
  const [showManualInput, setShowManualInput] = useState(false)
  const [registeredSceneComponents, setRegisteredSceneComponents] = useState<Record<string, React.FC<any>> | null>(null)
  const [registerLoading, setRegisterLoading] = useState(false)
  const [registerError, setRegisterError] = useState<string | null>(null)

  // 如果没有提供 configPath 或 taskId，尝试从工作流输出中提取
  const sessionState = useWorkflowSessionsStore((state) =>
    sessionId ? state.sessions[sessionId] : undefined,
  )
  const runOutput = sessionState?.runOutput ?? ''
  const videoProgress = sessionState?.videoProgress ?? { visible: false, step: 0, percent: 0, logs: [] }
  const runStatus = sessionState?.runStatus ?? null
  const runError = sessionState?.runError ?? null

  useEffect(() => {
    if (videoProgress.visible && videoProgress.logs.length > 0 && videoProgressLogsRef.current) {
      videoProgressLogsRef.current.scrollTop = videoProgressLogsRef.current.scrollHeight
    }
  }, [videoProgress.visible, videoProgress.logs.length])
  
  // 自动从工作流输出中提取视频信息（taskId / configPath）
  const extractedInfo = useMemo(() => {
    if (!configPath && !taskId && runOutput) {
      return extractVideoInfoFromOutput(runOutput)
    }
    return {}
  }, [configPath, taskId, runOutput])
  
  // 使用提供的参数、提取的参数或手动输入的参数
  const effectiveTaskId = taskId || extractedInfo.taskId || manualTaskId
  const effectiveConfigPath = configPath || extractedInfo.configPath
  const loadCancelledRef = useRef(false)

  useEffect(() => {
    loadCancelledRef.current = false
    const loadConfig = async (retryCount = 0) => {
      setLoading(true)
      setError(null)

      const taskIdStr = effectiveTaskId ? String(effectiveTaskId).trim() : ''
      const fallback = taskIdStr ? getFallbackConfig(taskIdStr) : null

      if (fallback) {
        setConfig(fallback)
        setLoading(false)
        return
      }

      // 如果 run 还在进行中，延迟加载（等 Step 4/4 完成，config 文件就绪）
      const runInProgress = runStatus === 'running' || runStatus === null
      if (runInProgress && effectiveTaskId) {
        console.log('⏳ VideoPreviewPanel: Run in progress, delaying config load until run completes...', {
          runStatus,
          effectiveTaskId
        })
        setLoading(false)
        return
      }

      try {
        console.log('🎬 VideoPreviewPanel: Loading config...', {
          effectiveTaskId,
          effectiveConfigPath,
          taskId,
          configPath,
          extractedInfo,
          hasRunOutput: !!runOutput,
          runStatus,
          retryCount
        })

        let response
        if (effectiveTaskId) {
          console.log('🎬 Using taskId to load config:', effectiveTaskId)
          response = await getVideoConfig(effectiveTaskId, sessionId)
        } else if (effectiveConfigPath) {
          console.log('🎬 Using configPath to load config:', effectiveConfigPath)
          response = await getVideoConfigByPath(effectiveConfigPath, sessionId)
        } else {
          throw new Error('Either taskId or configPath must be provided')
        }

        if (loadCancelledRef.current) return
        console.log('🎬 Config loaded successfully:', {
          hasConfig: !!response.config,
          scenesCount: response.config?.scenes?.length,
          configPath: response.config_path,
          taskId: response.task_id
        })
        setConfig(response.config)
      } catch (err: any) {
        if (err?.name === 'AbortError') {
          // 请求被取消（如 effect 重跑、超时），不展示为错误
          return
        }
        
        // 404 且 run 已完成：可能是文件同步延迟，重试几次
        const is404 = err?.message?.includes('404') || err?.message?.includes('not found')
        const maxRetries = 3
        const retryDelay = 2000 // 2秒
        
        if (is404 && retryCount < maxRetries && (runStatus === 'finished' || runStatus === 'success')) {
          console.log(`⏳ VideoPreviewPanel: Config not found (404), retrying in ${retryDelay}ms... (${retryCount + 1}/${maxRetries})`)
          await new Promise(resolve => setTimeout(resolve, retryDelay))
          if (!loadCancelledRef.current) {
            return loadConfig(retryCount + 1)
          }
          return
        }
        
        console.error('❌ Failed to load video config:', err)
        const msg = err?.message || 'Failed to load video configuration'
        const hint = FALLBACK_TASK_IDS.length > 0
          ? ` 可用的内置预览 Task ID：${FALLBACK_TASK_IDS.join('、')}。其他 ID 需后端存在对应配置文件。`
          : ''
        setError(msg + hint)
      } finally {
        if (!loadCancelledRef.current) setLoading(false)
      }
    }

    if (effectiveConfigPath || effectiveTaskId) {
      loadConfig()
    } else {
      setLoading(false)
      setShowManualInput(true)
    }
    return () => {
      loadCancelledRef.current = true
    }
  }, [effectiveConfigPath, effectiveTaskId, taskId, configPath, extractedInfo, runOutput, manualTaskId, runStatus, sessionId])

  // 当 config + taskId 就绪且为「动态任务」时，从后端拉取并注册组件（按 id 预览）
  useEffect(() => {
    if (!config || !effectiveTaskId) {
      setRegisteredSceneComponents(null)
      setRegisterLoading(false)
      setRegisterError(null)
      return
    }
    const prefix = extractComponentPrefix(config)
    if (KNOWN_PREFIXES.includes(prefix)) {
      setRegisteredSceneComponents(null)
      setRegisterLoading(false)
      setRegisterError(null)
      return
    }
    const cached = getRegisteredVideo(effectiveTaskId, sessionId)
    if (cached) {
      setRegisteredSceneComponents(cached.components)
      setRegisterLoading(false)
      setRegisterError(null)
      return
    }
    setRegisterLoading(true)
    setRegisterError(null)
    registerVideoByTaskId(effectiveTaskId, sessionId)
      .then((entry) => {
        if (entry) {
          setRegisteredSceneComponents(entry.components)
          setRegisterError(null)
        } else {
          setRegisteredSceneComponents(null)
          setRegisterError('注册视频组件失败')
        }
      })
      .catch((e) => {
        setRegisteredSceneComponents(null)
        setRegisterError(e?.message || '注册视频组件失败')
      })
      .finally(() => setRegisterLoading(false))
  }, [config, effectiveTaskId, sessionId])

  // 处理手动输入 taskId
  const handleManualLoad = async () => {
    if (!manualTaskId.trim()) {
      setError('Please enter a task ID')
      return
    }
    
    // 验证格式（YYYYMMDD_HHMMSS）
    const taskIdPattern = /^\d{8}_\d{6}$/
    if (!taskIdPattern.test(manualTaskId.trim())) {
      setError('Invalid task ID format. Expected format: YYYYMMDD_HHMMSS (e.g., 20260114_134845)')
      return
    }
    
    setShowManualInput(false)
    setError(null)
    setLoading(true)
    
    try {
      const response = await getVideoConfig(manualTaskId.trim(), sessionId)
      console.log('🎬 Config loaded successfully from manual input:', {
        hasConfig: !!response.config,
        scenesCount: response.config?.scenes?.length
      })
      setConfig(response.config)
    } catch (err: any) {
      console.error('❌ Failed to load video config from manual input:', err)
      setError(err.message || 'Failed to load video configuration')
      setShowManualInput(true) // 重新显示输入框
    } finally {
      setLoading(false)
    }
  }

  // When video is being generated and run is still in progress, show progress view; once finished, show player (below)
  const runInProgress = runStatus === 'running' || runStatus === null
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
              {runStatus === 'failed' ? 'Video generation failed' : 'Generating data video'}
            </span>
            {runStatus !== 'failed' && (
              <span style={{ fontSize: 12, fontWeight: 500, color: isDark ? '#818cf8' : '#4f46e5' }}>
                {videoProgress.percent}%
              </span>
            )}
            {runStatus === 'failed' && (
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
          <div
            style={{
              marginTop: 16,
              paddingTop: 16,
              borderTop: `1px solid ${isDark ? '#334155' : '#e2e8f0'}`,
            }}
          >
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
                <div style={{ color: isDark ? '#64748b' : '#94a3b8', fontStyle: 'italic', textAlign: 'center', padding: 20 }}>
                  Waiting for progress…
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

  if (loading) {
    return (
      <div style={{ 
        padding: '20px', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        height: '100%',
        color: 'var(--main-text-muted, #6b7280)',
        background: 'var(--panel-bg, #ffffff)'
      }}>
        Loading video configuration...
      </div>
    )
  }

  // 显示手动输入界面
  if (showManualInput && !loading) {
    return (
      <div style={{ 
        padding: '20px', 
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
        background: 'var(--panel-bg, #ffffff)',
        height: '100%'
      }}>
        <div style={{ fontWeight: 'bold', fontSize: '16px', color: 'var(--main-text, #111827)' }}>
          Video Preview
        </div>
        <div style={{ fontSize: '14px', color: 'var(--main-text-muted, #6b7280)' }}>
          No video configuration found. Please enter a task ID to load the video.
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <label style={{ fontSize: '12px', fontWeight: '500', color: 'var(--main-text, #111827)' }}>
            Task ID (format: YYYYMMDD_HHMMSS)
          </label>
          <input
            type="text"
            value={manualTaskId}
            onChange={(e) => setManualTaskId(e.target.value)}
            placeholder="e.g., 20260114_134845"
            style={{
              padding: '8px 12px',
              border: '1px solid var(--panel-border, #e5e7eb)',
              borderRadius: '6px',
              fontSize: '14px',
              fontFamily: 'monospace',
              background: 'var(--panel-bg, #ffffff)',
              color: 'var(--main-text, #111827)'
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                handleManualLoad()
              }
            }}
          />
          <div style={{ fontSize: '12px', color: 'var(--main-text-muted, #6b7280)', marginTop: '4px' }}>
            💡 You can find the task ID in the workflow output, e.g., "20260114_134845"
          </div>
        </div>
        <button
          onClick={handleManualLoad}
          disabled={!manualTaskId.trim() || loading}
          style={{
            padding: '10px 16px',
            background: manualTaskId.trim() && !loading ? 'var(--accent, #3b82f6)' : 'var(--panel-border, #e5e7eb)',
            color: manualTaskId.trim() && !loading ? '#ffffff' : 'var(--main-text-muted, #6b7280)',
            border: 'none',
            borderRadius: '6px',
            fontSize: '14px',
            fontWeight: '500',
            cursor: manualTaskId.trim() && !loading ? 'pointer' : 'not-allowed',
            transition: 'all 0.2s'
          }}
        >
          {loading ? 'Loading...' : 'Load Video'}
        </button>
        {error && (
          <div style={{ 
            padding: '12px',
            background: '#fef2f2',
            border: '1px solid #fecaca',
            borderRadius: '6px',
            color: '#dc2626',
            fontSize: '14px'
          }}>
            {error}
          </div>
        )}
      </div>
    )
  }

  if (error) {
    return (
      <div style={{ 
        padding: '20px', 
        color: '#ef4444',
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
        background: 'var(--panel-bg, #ffffff)'
      }}>
        <div style={{ fontWeight: 'bold' }}>Error loading video</div>
        <div style={{ fontSize: '14px' }}>{error}</div>
        {(effectiveConfigPath || effectiveTaskId) && (
          <div style={{ fontSize: '12px', opacity: 0.7, marginTop: '10px' }}>
            {effectiveTaskId && `Task ID: ${effectiveTaskId}`}
            {effectiveConfigPath && `Path: ${effectiveConfigPath}`}
          </div>
        )}
        <button
          onClick={() => {
            setError(null)
            setShowManualInput(true)
          }}
          style={{
            marginTop: '12px',
            padding: '8px 16px',
            background: 'var(--accent, #3b82f6)',
            color: '#ffffff',
            border: 'none',
            borderRadius: '6px',
            fontSize: '14px',
            cursor: 'pointer'
          }}
        >
          Enter Task ID Manually
        </button>
      </div>
    )
  }

  if (!config) {
    return (
      <div style={{ 
        padding: '20px', 
        color: 'var(--main-text-muted, #6b7280)',
        textAlign: 'center',
        background: 'var(--panel-bg, #ffffff)'
      }}>
        No video configuration available
      </div>
    )
  }

  const componentPrefixForPanel = extractComponentPrefix(config)
  const isDynamicTask = effectiveTaskId && !KNOWN_PREFIXES.includes(componentPrefixForPanel)
  if (isDynamicTask && registerLoading) {
    return (
      <div style={{ padding: '20px', textAlign: 'center', background: 'var(--panel-bg, #ffffff)' }}>
        <div style={{ fontWeight: 'bold', marginBottom: 8 }}>正在加载视频组件…</div>
        <div style={{ fontSize: 12, color: 'var(--main-text-muted)' }}>根据 task id 从后端拉取并注册</div>
      </div>
    )
  }
  if (isDynamicTask && registerError && !registeredSceneComponents) {
    return (
      <div style={{ padding: '20px', color: '#ef4444', background: 'var(--panel-bg, #ffffff)' }}>
        <div style={{ fontWeight: 'bold' }}>加载视频组件失败</div>
        <div style={{ fontSize: 14, marginTop: 8 }}>{registerError}</div>
      </div>
    )
  }

  // 安全地获取配置值，提供默认值
  const { fps = 30, width = 1280, height = 720, video_duration } = config.meta || {}
  
  // 如果没有 video_duration，尝试从 scenes 计算
  let calculatedDuration = video_duration
  if (!calculatedDuration && config.scenes && config.scenes.length > 0) {
    // 从最后一个场景的 time_range 获取结束时间
    const lastScene = config.scenes[config.scenes.length - 1]
    if (lastScene.time_range && Array.isArray(lastScene.time_range) && lastScene.time_range.length >= 2) {
      calculatedDuration = lastScene.time_range[1]
    }
  }
  
  // 如果还是没有，使用默认值
  const finalDuration = calculatedDuration || 10.0
  const totalFrames = Math.floor(finalDuration * fps)

  return (
    <div style={{ 
      width: '100%', 
      height: '100%', 
      display: 'flex', 
      flexDirection: 'column',
      background: 'var(--panel-bg, #ffffff)'
    }}>
      {/* 视频信息栏 */}
      <div style={{
        padding: '12px 16px',
        borderBottom: '1px solid var(--panel-border, #e5e7eb)',
        background: 'var(--panel-bg, #ffffff)',
        fontSize: '12px',
        color: 'var(--main-text-muted, #6b7280)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <div>
          <span style={{ fontWeight: 'bold', color: 'var(--main-text, #111827)' }}>{config.meta?.title || 'Video Preview'}</span>
          <span style={{ marginLeft: '12px' }}>
            {config.scenes?.length || 0} scenes • {finalDuration.toFixed(1)}s • {width}×{height}
          </span>
        </div>
        {effectiveTaskId && (
          <div style={{ fontSize: '11px', opacity: 0.7 }}>
            Task: {effectiveTaskId}
          </div>
        )}
      </div>

      {/* 视频播放器区域 */}
      <div style={{ 
        flex: 1, 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        padding: '20px',
        overflow: 'auto',
        background: 'var(--panel-bg, #ffffff)'
      }}>
        {/* 使用 Remotion Player 渲染视频 */}
        {/* 注意：这里使用简化组件，完整版本需要集成 SceneBasedVideo */}
        <div style={{ 
          width: '100%', 
          maxWidth: `${width}px`,
          aspectRatio: `${width} / ${height}`,
          background: '#ffffff',
          borderRadius: '8px',
          boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)'
        }}>
          <Player
            component={VideoPreviewComponent}
            durationInFrames={totalFrames}
            compositionWidth={width}
            compositionHeight={height}
            fps={fps}
            controls
            style={{ width: '100%', borderRadius: '8px' }}
            inputProps={{
              config,
              taskId: effectiveTaskId,
              sessionId,
              registeredSceneComponents: registeredSceneComponents ?? undefined,
            }}
          />
        </div>
      </div>
    </div>
  )
}
