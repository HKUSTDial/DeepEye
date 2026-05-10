import { Suspense, type ReactNode } from 'react'
import { FolderOpen, Workflow as WorkflowIcon, FileText, LayoutDashboard, Video } from 'lucide-react'
import { translateApp } from '../../locale'
import { PanelLoadingFallback } from './PanelLoadingFallback'
import {
  DashboardPanel,
  FilesPanel,
  ReportPanel,
  VideoPreviewPanel,
  WorkflowLivePanel,
} from './panelComponents'

export type PanelRenderContext = {
  sessionId: string | null
  dataSourceIds: string[]
}

export type PanelPlugin = {
  id: string
  title: string | ((params?: Record<string, unknown>) => string)
  description: string | (() => string)
  icon?: ReactNode
  render: (context: PanelRenderContext, params?: Record<string, unknown>) => ReactNode
}

function renderLazyPanel(node: ReactNode, title: string) {
  return <Suspense fallback={<PanelLoadingFallback title={title} />}>{node}</Suspense>
}

export const panelRegistry: PanelPlugin[] = [
  {
    id: 'workflow',
    title: () => translateApp('panel.workflow.title'),
    description: () => translateApp('panel.workflow.description'),
    icon: <WorkflowIcon className="h-4 w-4" />,
    render: (context) => renderLazyPanel(
      <WorkflowLivePanel
        sessionId={context.sessionId}
        dataSourceIds={context.dataSourceIds}
      />,
      translateApp('panel.workflow.title'),
    ),
  },
  {
    id: 'files',
    title: () => translateApp('panel.files.title'),
    description: () => translateApp('panel.files.description'),
    icon: <FolderOpen className="h-4 w-4" />,
    render: (context) => renderLazyPanel(<FilesPanel sessionId={context.sessionId} />, translateApp('panel.files.title')),
  },
  {
    id: 'report',
    title: () => translateApp('panel.report.title'),
    description: () => translateApp('panel.report.description'),
    icon: <FileText className="h-4 w-4" />,
    render: (context) => renderLazyPanel(<ReportPanel sessionId={context.sessionId} />, translateApp('panel.report.title')),
  },
  {
    id: 'dashboard',
    title: () => translateApp('panel.dashboard.title'),
    description: () => translateApp('panel.dashboard.description'),
    icon: <LayoutDashboard className="h-4 w-4" />,
    render: (context) => renderLazyPanel(<DashboardPanel sessionId={context.sessionId} />, translateApp('panel.dashboard.title')),
  },
  {
    id: 'video-preview',
    title: (params) => (params?.taskId ? translateApp('panel.video.titleWithTask', { taskId: String(params.taskId) }) : translateApp('panel.video.title')),
    description: () => translateApp('panel.video.description'),
    icon: <Video className="h-4 w-4" />,
    render: (context, params) => renderLazyPanel(
      <VideoPreviewPanel
        sessionId={context.sessionId}
        taskId={params?.taskId as string | undefined}
      />,
      translateApp('panel.video.title'),
    ),
  },
]

export const getPanelPlugin = (id: string) => panelRegistry.find((plugin) => plugin.id === id)
