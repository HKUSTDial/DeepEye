export const VIDEO_PROGRESS_STAGE_KEYS = [
  'video.step1',
  'video.step2',
  'video.step3',
  'video.step4',
] as const

export const VIDEO_PROGRESS_STAGE_MESSAGE_KEYS = [
  'video.stepMessage1',
  'video.stepMessage2',
  'video.stepMessage3',
  'video.stepMessage4',
] as const

export const VIDEO_PROGRESS_STAGE_ICONS = ['📹', '🎵', '💾', '🎬'] as const

export const VIDEO_PROGRESS_TOTAL_STEPS = VIDEO_PROGRESS_STAGE_KEYS.length

export function parseVideoProgressStep(message: string) {
  const match = message.match(/Step\s*(\d+)\s*\/\s*(\d+)/i)
  if (!match) return null

  const rawStep = Number.parseInt(match[1], 10)
  const rawTotal = Number.parseInt(match[2], 10)
  if (Number.isNaN(rawStep)) return null

  const total = Number.isNaN(rawTotal) || rawTotal <= 0 ? VIDEO_PROGRESS_TOTAL_STEPS : rawTotal
  return Math.min(Math.max(rawStep - 1, 0), Math.max(Math.min(total, VIDEO_PROGRESS_TOTAL_STEPS) - 1, 0))
}
