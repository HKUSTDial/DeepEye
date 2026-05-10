export const DASHBOARD_PROGRESS_STAGES = [
  'Generate title and framing',
  'Design visualizations',
  'Design key metrics',
  'Design interactions',
  'Consolidate layout',
  'Implement and deploy preview',
] as const

export const DASHBOARD_PROGRESS_STAGE_KEYS = [
  'dashboard.stage1',
  'dashboard.stage2',
  'dashboard.stage3',
  'dashboard.stage4',
  'dashboard.stage5',
  'dashboard.stage6',
] as const

const DASHBOARD_STAGE_RULES: Array<{ stage: number; patterns: RegExp[] }> = [
  {
    stage: 0,
    patterns: [/Generating dashboard title and description/i],
  },
  {
    stage: 1,
    patterns: [/Generating visualization/i],
  },
  {
    stage: 2,
    patterns: [/Designing key metrics/i],
  },
  {
    stage: 3,
    patterns: [/Designing dashboard interactions/i],
  },
  {
    stage: 4,
    patterns: [/Consolidating all configurations and optimizing layout/i],
  },
  {
    stage: 5,
    patterns: [
      /Implementing engineering features and filter binding/i,
      /Generation results successfully synchronized/i,
      /Starting independent dashboard service container/i,
      /Dashboard deployment complete/i,
    ],
  },
]

export function getDashboardProgressStage(message: string): number | null {
  for (const rule of DASHBOARD_STAGE_RULES) {
    if (rule.patterns.some((pattern) => pattern.test(message))) {
      return rule.stage
    }
  }
  return null
}

export function isDashboardProgressMessage(message: string): boolean {
  return getDashboardProgressStage(message) !== null
}
