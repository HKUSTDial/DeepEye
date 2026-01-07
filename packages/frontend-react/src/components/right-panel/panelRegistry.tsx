import type { ReactNode } from 'react'
import { FolderOpen, Workflow as WorkflowIcon } from 'lucide-react'
import { FilesPanel } from './plugins/FilesPanel'
import { WorkflowLivePanel } from './plugins/WorkflowLivePanel'

export type PanelRenderContext = {
  sessionId: string | null
  dataSourceId: string | null
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
    render: (context) => <WorkflowLivePanel sessionId={context.sessionId} />,
  },
]

export const getPanelPlugin = (id: string) => panelRegistry.find((plugin) => plugin.id === id)
