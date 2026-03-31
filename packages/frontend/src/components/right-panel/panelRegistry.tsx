import { Suspense, lazy, type ReactNode } from 'react'
import { FolderOpen, Workflow as WorkflowIcon, FileText, LayoutDashboard, Video } from 'lucide-react'

export type PanelRenderContext = {
  sessionId: string | null
  dataSourceIds: string[]
}

export type PanelPlugin = {
  id: string
  title: string | ((params?: Record<string, unknown>) => string)
  description: string
  icon?: ReactNode
  render: (context: PanelRenderContext, params?: Record<string, unknown>) => ReactNode
}

const FilesPanel = lazy(() =>
  import('./plugins/FilesPanel').then((module) => ({ default: module.FilesPanel })),
)
const WorkflowLivePanel = lazy(() =>
  import('./plugins/WorkflowLivePanel').then((module) => ({ default: module.WorkflowLivePanel })),
)
const ReportPanel = lazy(() =>
  import('./plugins/ReportPanel').then((module) => ({ default: module.ReportPanel })),
)
const DashboardPanel = lazy(() =>
  import('./plugins/DashboardPanel').then((module) => ({ default: module.DashboardPanel })),
)
const VideoPreviewPanel = lazy(() =>
  import('./plugins/VideoPreviewPanel').then((module) => ({ default: module.VideoPreviewPanel })),
)

function PanelLoadingFallback({ title }: { title: string }) {
  return (
    <div className="right-panel-empty">
      <div className="right-panel-empty-title">Loading {title}...</div>
    </div>
  )
}

function renderLazyPanel(node: ReactNode, title: string) {
  return <Suspense fallback={<PanelLoadingFallback title={title} />}>{node}</Suspense>
}

export const panelRegistry: PanelPlugin[] = [
  {
    id: 'files',
    title: 'Files',
    description: 'Browse session files and generated outputs.',
    icon: <FolderOpen className="h-4 w-4" />,
    render: (context) => renderLazyPanel(<FilesPanel sessionId={context.sessionId} />, 'Files'),
  },
  {
    id: 'workflow',
    title: 'Workflow',
    description: 'Inspect node graph and runtime progression.',
    icon: <WorkflowIcon className="h-4 w-4" />,
    render: (context) => renderLazyPanel(
      <WorkflowLivePanel
        sessionId={context.sessionId}
        dataSourceIds={context.dataSourceIds}
      />,
      'Workflow',
    ),
  },
  {
    id: 'report',
    title: 'Report',
    description: 'Read generated report content and steps.',
    icon: <FileText className="h-4 w-4" />,
    render: (context) => renderLazyPanel(<ReportPanel sessionId={context.sessionId} />, 'Report'),
  },
  {
    id: 'dashboard',
    title: 'Dashboard',
    description: 'Preview charts and visual analytics results.',
    icon: <LayoutDashboard className="h-4 w-4" />,
    render: (context) => renderLazyPanel(<DashboardPanel sessionId={context.sessionId} />, 'Dashboard'),
  },
  {
    id: 'video-preview',
    title: (params) => (params?.taskId ? `Video: ${params.taskId}` : 'Video Preview'),
    description: 'Track and preview generated video artifacts.',
    icon: <Video className="h-4 w-4" />,
    render: (context, params) => renderLazyPanel(
      <VideoPreviewPanel
        sessionId={context.sessionId}
        taskId={params?.taskId as string | undefined}
      />,
      'Video Preview',
    ),
  },
]

export const getPanelPlugin = (id: string) => panelRegistry.find((plugin) => plugin.id === id)
