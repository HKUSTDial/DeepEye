/**
 * VideoComposer - 数据视频串联组件
 * 支持：1) 写死的两套模板 2) 按 taskId + componentPrefix 动态加载本次生成的组件
 */

import React, { useState, useEffect, useMemo } from 'react'
import { AbsoluteFill, Sequence, useVideoConfig, Audio } from 'remotion'
import { getAudioFileUrl, getVideoComponentRegistry, getVideoComponentFileUrl } from '../../api/video'
import { compileTsxAndGetComponent } from '../../utils/compileTsxInBrowser'

import { 分析学生成绩分布生成数据视频_SceneOpeningComponent as StudentScore_SceneOpeningComponent } from './分析学生成绩分布生成数据视频/20260114_181334/分析学生成绩分布生成数据视频_SceneOpening_20260114_181334ComponentAnimated'
import { 分析学生成绩分布生成数据视频_AnalysisScoreDistributionComponent as StudentScore_AnalysisScoreDistributionComponent } from './分析学生成绩分布生成数据视频/20260114_181334/分析学生成绩分布生成数据视频_AnalysisScoreDistribution_20260114_181334ComponentAnimated'
import { SceneComponentAnimated as StudentScore_AnalysisGradeComparisonAnimated } from './分析学生成绩分布生成数据视频/20260114_181334/分析学生成绩分布生成数据视频_AnalysisGradeComparison_20260114_181334Animated'
import { 分析学生成绩分布生成数据视频_SummaryBasicStatsComponent as StudentScore_SummaryBasicStatsComponent } from './分析学生成绩分布生成数据视频/20260114_181334/分析学生成绩分布生成数据视频_SummaryBasicStats_20260114_181334ComponentAnimated'
import { 分析学生成绩分布生成数据视频_SceneClosingComponent as StudentScore_SceneClosingComponent } from './分析学生成绩分布生成数据视频/20260114_181334/分析学生成绩分布生成数据视频_SceneClosing_20260114_181334ComponentAnimated'

import { Createavideoreportex_SceneOpeningComponent } from './Createavideoreportex/20260115_184400/Createavideoreportex_SceneOpening_20260115_184400ComponentAnimated'
import { SceneComponentAnimated as Createavideoreportex_AnalysisCategoryPerformanceQ4Animated } from './Createavideoreportex/20260115_184400/Createavideoreportex_AnalysisCategoryPerformanceQ4_20260115_184400Animated'
import { SceneComponentAnimated as Createavideoreportex_AnalysisMonthlyRevenueQ4Animated } from './Createavideoreportex/20260115_184400/Createavideoreportex_AnalysisMonthlyRevenueQ4_20260115_184400Animated'
import { SceneComponentAnimated as Createavideoreportex_AnalysisProfitMarginQ4ProductsAnimated } from './Createavideoreportex/20260115_184400/Createavideoreportex_AnalysisProfitMarginQ4Products_20260115_184400Animated'
import { SceneComponentAnimated as Createavideoreportex_AnalysisQuarterlyRevenueTrendAnimated } from './Createavideoreportex/20260115_184400/Createavideoreportex_AnalysisQuarterlyRevenueTrend_20260115_184400Animated'
import { SceneComponentAnimated as Createavideoreportex_AnalysisRegionalContributionQ4Animated } from './Createavideoreportex/20260115_184400/Createavideoreportex_AnalysisRegionalContributionQ4_20260115_184400Animated'
import { SceneComponentAnimated as Createavideoreportex_AnalysisTopProductsQ4Animated } from './Createavideoreportex/20260115_184400/Createavideoreportex_AnalysisTopProductsQ4_20260115_184400Animated'
import { Createavideoreportex_SceneStatsComponent } from './Createavideoreportex/20260115_184400/Createavideoreportex_SceneStats_20260115_184400ComponentAnimated'
import { Createavideoreportex_SceneClosingComponent } from './Createavideoreportex/20260115_184400/Createavideoreportex_SceneClosing_20260115_184400ComponentAnimated'

const STUDENTSCORE_COMPONENTS: Record<string, React.FC<any>> = {
  scene_opening: StudentScore_SceneOpeningComponent,
  analysis_score_distribution: StudentScore_AnalysisScoreDistributionComponent,
  analysis_grade_comparison: StudentScore_AnalysisGradeComparisonAnimated,
  summary_basic_stats: StudentScore_SummaryBasicStatsComponent,
  scene_closing: StudentScore_SceneClosingComponent,
}

const CREATEAVIDEOREPORTEX_COMPONENTS: Record<string, React.FC<any>> = {
  scene_opening: Createavideoreportex_SceneOpeningComponent,
  analysis_category_performance_q4: Createavideoreportex_AnalysisCategoryPerformanceQ4Animated,
  analysis_monthly_revenue_q4: Createavideoreportex_AnalysisMonthlyRevenueQ4Animated,
  analysis_profit_margin_q4_products: Createavideoreportex_AnalysisProfitMarginQ4ProductsAnimated,
  analysis_quarterly_revenue_trend: Createavideoreportex_AnalysisQuarterlyRevenueTrendAnimated,
  analysis_regional_contribution_q4: Createavideoreportex_AnalysisRegionalContributionQ4Animated,
  analysis_top_products_q4: Createavideoreportex_AnalysisTopProductsQ4Animated,
  scene_stats: Createavideoreportex_SceneStatsComponent,
  summary_stats: Createavideoreportex_SceneStatsComponent,
  scene_closing: Createavideoreportex_SceneClosingComponent,
}



/** 已知的写死模板 prefix，用静态映射 */
const KNOWN_PREFIXES = ['分析学生成绩分布生成数据视频', 'Createavideoreportex']

/** 根据 scene_id 生成动画组件文件名（与后端一致） */
function sceneIdToFilename(sceneId: string, datasetName: string, taskId: string): string {
  const camel = sceneId.split('_').map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join('')
  const needComponent =
    sceneId === 'scene_opening' ||
    sceneId === 'scene_closing' ||
    sceneId.toLowerCase().includes('stat') ||
    sceneId.endsWith('_statistics')
  if (needComponent) return `${datasetName}_${camel}_${taskId}ComponentAnimated.tsx`
  return `${datasetName}_${camel}_${taskId}Animated.tsx`
}

/** 所有子目录下的场景 TSX（*Animated.tsx / *ComponentAnimated.tsx），用于按路径动态解析
 * 排除包含 task ID 格式（YYYYMMDD_HHMMSS）的动态生成目录，这些文件应该通过 API 获取并在浏览器中编译
 */
const dynamicModuleLoaders = import.meta.glob<{ [key: string]: React.FC<any> }>(
  [
    // 只包含已知的静态模板目录，排除动态生成的 task ID 目录
    './分析学生成绩分布生成数据视频/**/*ComponentAnimated.tsx',
    './分析学生成绩分布生成数据视频/**/*Animated.tsx',
    './Createavideoreportex/**/*ComponentAnimated.tsx',
    './Createavideoreportex/**/*Animated.tsx',
  ],
  { eager: false }
)

interface VideoComposerProps {
  configJson: any
  componentPrefix?: string
  taskId?: string | null
  sessionId?: string | null
  includeOpeningClosing?: boolean
  /** 已注册的场景组件（由前端拉取后端 full 接口后编译并缓存，按 id 预览时传入） */
  registeredSceneComponents?: Record<string, React.FC<any>> | null
}

const VideoComposerComponent: React.FC<VideoComposerProps> = ({
  configJson,
  componentPrefix = '分析学生成绩分布生成数据视频',
  taskId,
  sessionId,
  includeOpeningClosing = true,
  registeredSceneComponents,
}) => {
  const { fps } = useVideoConfig()

  const [dynamicComponents, setDynamicComponents] = useState<Record<string, React.FC<any>> | null>(null)
  const [dynamicLoadError, setDynamicLoadError] = useState<string | null>(null)

  const useDynamic = useMemo(() => {
    if (!taskId || !componentPrefix) return false
    return !KNOWN_PREFIXES.includes(componentPrefix)
  }, [taskId, componentPrefix])

  useEffect(() => {
    if (!useDynamic || !configJson?.scenes || !taskId) {
      setDynamicComponents(null)
      setDynamicLoadError(null)
      return
    }
    if (registeredSceneComponents && Object.keys(registeredSceneComponents).length > 0) {
      setDynamicComponents(registeredSceneComponents)
      setDynamicLoadError(null)
      return
    }
    const datasetName = componentPrefix
    const sceneIds = (configJson.scenes as any[]).map((s: any) => s.id).filter(Boolean)
    const loaders: Promise<void>[] = []
    const next: Record<string, React.FC<any>> = {}

    sceneIds.forEach((sceneId) => {
      const filename = sceneIdToFilename(sceneId, datasetName, taskId)
      const pathKey = `./${componentPrefix}/${taskId}/${filename}`
      const loader = dynamicModuleLoaders[pathKey]
      if (!loader) return
      loaders.push(
        (loader as () => Promise<{ [key: string]: React.FC<any> }>)()
          .then((mod) => {
            const comp = mod.default || (Object.values(mod).find((v) => typeof v === 'function') as React.FC<any>)
            if (comp) next[sceneId] = comp
          })
          .catch((e) => {
            console.warn(`Failed to load dynamic scene ${sceneId}:`, e)
          })
      )
    })

    if (loaders.length > 0) {
      Promise.all(loaders).then(() => {
        const hasAny = Object.keys(next).length > 0
        setDynamicComponents(hasAny ? next : null)
        setDynamicLoadError(hasAny ? null : '未成功加载任何场景组件。')
      })
      return
    }

    getVideoComponentRegistry(taskId, sessionId)
      .then((res) => {
        const registry = res.registry || {}
        const fetchPromises = Object.entries(registry).map(([sceneId, filename]) => {
          const url = getVideoComponentFileUrl(taskId, filename, sessionId)
          return fetch(url)
            .then((r) => (r.ok ? r.text() : Promise.reject(new Error(`${filename}: ${r.status}`))))
            .then((tsx) => compileTsxAndGetComponent(tsx, filename))
            .then((comp) => {
              if (comp) next[sceneId] = comp
            })
            .catch((e) => console.warn(`[VideoComposer] fetch/compile ${sceneId}:`, e))
        })
        return Promise.all(fetchPromises).then(() => next)
      })
      .then((loaded) => {
        const hasAny = Object.keys(loaded).length > 0
        setDynamicComponents(hasAny ? loaded : null)
        setDynamicLoadError(hasAny ? null : '未找到与当前任务匹配的组件（后端可能尚未生成完成）。')
      })
      .catch((e) => {
        console.warn('[VideoComposer] load from API failed:', e)
        setDynamicComponents(null)
        setDynamicLoadError('加载组件失败：' + (e?.message || '请确认该任务已生成视频组件。'))
      })
  }, [useDynamic, taskId, componentPrefix, configJson?.scenes, registeredSceneComponents, sessionId])

  const SCENE_COMPONENTS = useMemo(() => {
    // 如果使用动态加载，优先使用已注册的组件
    if (useDynamic && registeredSceneComponents && Object.keys(registeredSceneComponents).length > 0) {
      return registeredSceneComponents
    }
    // 如果使用动态加载，使用动态加载的组件
    if (useDynamic && dynamicComponents && Object.keys(dynamicComponents).length > 0) {
      return dynamicComponents
    }
    // 如果使用动态加载但加载失败，返回空对象（不要回退到静态映射）
    if (useDynamic) {
      return {}
    }
    // 静态映射（仅用于已知的模板）
    return componentPrefix === 'Createavideoreportex' ? CREATEAVIDEOREPORTEX_COMPONENTS : STUDENTSCORE_COMPONENTS
  }, [useDynamic, registeredSceneComponents, dynamicComponents, componentPrefix])

  const allScenes = (configJson?.scenes || []).filter((scene: any) => {
    if (!scene || !scene.type) return false
    if (includeOpeningClosing) {
      return ['opening', 'chart', 'stat_cards', 'closing'].includes(scene.type)
    }
    return scene.type === 'chart'
  })

  const audioSegments = React.useMemo(() => {
    if (!configJson?.scenes || !Array.isArray(configJson.scenes)) return []
    return configJson.scenes.flatMap((scene: any) => {
      if (!scene?.narration) return []
      return (scene.narration || [])
        .filter((narr: any) => narr?.audio_file)
        .map((narr: any) => ({
          audioFile: narr.audio_file,
          startTime: narr.time_start || 0,
          endTime: narr.time_end ?? (narr.time_start || 0) + 3.0,
        }))
    })
  }, [configJson?.scenes])

  const firstChartScene = (configJson?.scenes || []).find((s: any) => s?.type === 'chart')
  const backgroundColor = firstChartScene?.content?.style?.background_color || '#0f1419'

  const getSceneComponent = (scene: any): React.FC<any> | null => {
    return SCENE_COMPONENTS[scene.id] || null
  }

  const createMissingSceneComponent = (scene: any): React.FC<any> => {
    const sceneId = String(scene?.id || 'unknown')
    const title = String(scene?.content?.title || scene?.content?.headline || sceneId)
    const type = String(scene?.type || 'unknown')
    return () => (
      <AbsoluteFill
        style={{
          justifyContent: 'center',
          alignItems: 'center',
          color: '#e5e7eb',
          padding: 48,
        }}
      >
        <div style={{ textAlign: 'center', maxWidth: 860 }}>
          <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 10 }}>
            Scene component not generated
          </div>
          <div style={{ fontSize: 12, opacity: 0.85, marginBottom: 10 }}>
            Scene ID: <span style={{ fontFamily: 'monospace' }}>{sceneId}</span> · Type: {type}
          </div>
          <div style={{ fontSize: 14, opacity: 0.9 }}>{title}</div>
          <div style={{ marginTop: 14, fontSize: 12, opacity: 0.7 }}>
            This usually means the backend only generated some TSX files (often opening/closing).
            Re-run generation or check backend-worker logs for TSX generation errors.
          </div>
        </div>
      </AbsoluteFill>
    )
  }

  if (useDynamic && dynamicLoadError && (!dynamicComponents || Object.keys(dynamicComponents).length === 0)) {
    return (
      <AbsoluteFill style={{ backgroundColor, justifyContent: 'center', alignItems: 'center', color: '#fff' }}>
        <div style={{ textAlign: 'center', maxWidth: 360 }}>
          <div style={{ marginBottom: 8 }}>无法加载本次生成的视频组件</div>
          <div style={{ fontSize: 12, opacity: 0.8 }}>{dynamicLoadError}</div>
        </div>
      </AbsoluteFill>
    )
  }

  if (useDynamic && dynamicComponents === null && !dynamicLoadError) {
    return (
      <AbsoluteFill style={{ backgroundColor, justifyContent: 'center', alignItems: 'center', color: '#fff' }}>
        <div>正在加载视频组件…</div>
      </AbsoluteFill>
    )
  }

  return (
    <AbsoluteFill style={{ backgroundColor }}>
      {audioSegments.map((segment: any, idx: number) => {
        const startFrame = Math.floor(segment.startTime * fps)
        const durationInFrames = Math.floor((segment.endTime - segment.startTime) * fps)
        if (durationInFrames <= 0) return null
        const audioFilename = (segment.audioFile || '').split('/').pop() || segment.audioFile
        if (!audioFilename) return null
        const audioSrc = getAudioFileUrl(audioFilename, sessionId)
        return (
          <Sequence key={`audio-${idx}`} from={startFrame} durationInFrames={durationInFrames}>
            <Audio src={audioSrc} />
          </Sequence>
        )
      })}

      {allScenes.map((scene: any, sceneIndex: number) => {
        let startTime: number
        let endTime: number
        if (!scene.time_range || !Array.isArray(scene.time_range) || scene.time_range.length < 2) {
          if (scene.narration?.length) {
            const first = scene.narration[0]
            const last = scene.narration[scene.narration.length - 1]
            startTime = first.time_start || 0
            endTime = last.time_end ?? (last.time_start || 0) + 3.0
          } else {
            startTime = sceneIndex * 10.0
            endTime = startTime + 5.0
          }
        } else {
          [startTime, endTime] = scene.time_range
        }
        const startFrame = Math.round(startTime * fps)
        const duration = Math.round((endTime - startTime) * fps)
        const SceneComponent = getSceneComponent(scene) ?? createMissingSceneComponent(scene)
        const durationInFrames = duration <= 0 ? Math.round(1 * fps) : duration
        return (
          <Sequence key={scene.id} from={startFrame} durationInFrames={durationInFrames} name={scene.id}>
            <SceneComponent
              sceneStartOffset={startTime}
              narrations={scene.narration}
              animations={scene.animations}
              sceneContent={scene.content}
              scene={scene}
            />
          </Sequence>
        )
      })}
    </AbsoluteFill>
  )
}

export const VideoComposer = VideoComposerComponent as React.FC<any>
