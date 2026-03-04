import type { ReactNode } from 'react'
import { FolderOpen, Workflow as WorkflowIcon, FileText, LayoutDashboard, Video } from 'lucide-react'
import { FilesPanel } from './plugins/FilesPanel'
import { WorkflowLivePanel } from './plugins/WorkflowLivePanel'
import { ReportPanel } from './plugins/ReportPanel'
import { DashboardPanel } from './plugins/DashboardPanel'
import { VideoPreviewPanel } from './plugins/VideoPreviewPanel'

export type PanelRenderContext = {
  sessionId: string | null
  dataSourceIds: string[]
}

export type PanelPlugin = {
  id: string
  title: string | ((params?: Record<string, unknown>) => string)
  icon?: ReactNode
  render: (context: PanelRenderContext, params?: Record<string, unknown>) => ReactNode
}

export const panelRegistry: PanelPlugin[] = [
  {
    id: 'files',
    title: 'Files',
    icon: <FolderOpen className="h-4 w-4" />,
    render: (context) => <FilesPanel sessionId={context.sessionId} />,
  },
  {
    id: 'workflow',
    title: 'Workflow',
    icon: <WorkflowIcon className="h-4 w-4" />,
    render: (context) => (
      <WorkflowLivePanel 
        sessionId={context.sessionId} 
        dataSourceIds={context.dataSourceIds} 
      />
    ),
  },
  {
    id: 'report',
    title: 'Report',
    icon: <FileText className="h-4 w-4" />,
    render: () => <ReportPanel />,
  },
  {
    id: 'dashboard',
    title: 'Dashboard',
    icon: <LayoutDashboard className="h-4 w-4" />,
    render: (context) => <DashboardPanel sessionId={context.sessionId} />,
  },
  {
    id: 'video-preview',
    title: (params) => (params?.taskId ? `Video: ${params.taskId}` : 'Video Preview'),
    icon: <Video className="h-4 w-4" />,
    render: (context, params) => (
      <VideoPreviewPanel
        sessionId={context.sessionId}
        taskId={params?.taskId as string | undefined}
        configPath={params?.configPath as string | undefined}
      />
    ),
  },
]

export const getPanelPlugin = (id: string) => panelRegistry.find((plugin) => plugin.id === id)
