import { lazy } from 'react'

export const FilesPanel = lazy(() =>
  import('./plugins/FilesPanel').then((module) => ({ default: module.FilesPanel })),
)

export const WorkflowLivePanel = lazy(() =>
  import('./plugins/WorkflowLivePanel').then((module) => ({ default: module.WorkflowLivePanel })),
)

export const ReportPanel = lazy(() =>
  import('./plugins/ReportPanel').then((module) => ({ default: module.ReportPanel })),
)

export const DashboardPanel = lazy(() =>
  import('./plugins/DashboardPanel').then((module) => ({ default: module.DashboardPanel })),
)

export const VideoPreviewPanel = lazy(() =>
  import('./plugins/VideoPreviewPanel').then((module) => ({ default: module.VideoPreviewPanel })),
)
