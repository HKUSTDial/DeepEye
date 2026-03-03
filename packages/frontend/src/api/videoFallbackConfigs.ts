/**
 * 内置视频配置：当后端没有该 task_id 的 config 时使用，保证两个写死模板的 task id 始终可预览。
 */

import type { VideoConfig } from './video'

const fps = 30
const width = 1280
const height = 720

/** 20260114_181334 - 分析学生成绩分布生成数据视频（STUDENTSCORE） */
export const FALLBACK_CONFIG_20260114_181334: VideoConfig = {
  meta: {
    title: '分析学生成绩分布生成数据视频',
    fps,
    width,
    height,
    video_duration: 35,
  },
  scenes: [
    { id: 'scene_opening', type: 'opening', time_range: [0, 5], content: {} },
    { id: 'analysis_score_distribution', type: 'chart', time_range: [5, 12], content: {} },
    { id: 'analysis_grade_comparison', type: 'chart', time_range: [12, 19], content: {} },
    { id: 'summary_basic_stats', type: 'stat_cards', time_range: [19, 28], content: {} },
    { id: 'scene_closing', type: 'closing', time_range: [28, 35], content: {} },
  ],
}

/** 20260115_184400 - Createavideoreportex 销售数据报表 */
export const FALLBACK_CONFIG_20260115_184400: VideoConfig = {
  meta: {
    title: 'Create a video report ex',
    fps,
    width,
    height,
    video_duration: 55,
  },
  scenes: [
    { id: 'scene_opening', type: 'opening', time_range: [0, 5], content: {} },
    { id: 'analysis_category_performance_q4', type: 'chart', time_range: [5, 12], content: {} },
    { id: 'analysis_monthly_revenue_q4', type: 'chart', time_range: [12, 19], content: {} },
    { id: 'analysis_profit_margin_q4_products', type: 'chart', time_range: [19, 26], content: {} },
    { id: 'analysis_quarterly_revenue_trend', type: 'chart', time_range: [26, 33], content: {} },
    { id: 'analysis_regional_contribution_q4', type: 'chart', time_range: [33, 40], content: {} },
    { id: 'analysis_top_products_q4', type: 'chart', time_range: [40, 47], content: {} },
    { id: 'scene_stats', type: 'stat_cards', time_range: [47, 52], content: {} },
    { id: 'scene_closing', type: 'closing', time_range: [52, 55], content: {} },
  ],
}

const FALLBACK_MAP: Record<string, VideoConfig> = {
  '20260114_181334': FALLBACK_CONFIG_20260114_181334,
  '20260115_184400': FALLBACK_CONFIG_20260115_184400,
}

/** 有内置配置的 task id 列表（无需后端 config 即可预览） */
export const FALLBACK_TASK_IDS = Object.keys(FALLBACK_MAP)

export function getFallbackConfig(taskId: string): VideoConfig | null {
  return FALLBACK_MAP[taskId] ?? null
}
