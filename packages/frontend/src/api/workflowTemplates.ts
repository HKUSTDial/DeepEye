import type { WorkflowRun } from '../types'
import { http } from './client'

export interface WorkflowTemplateParam {
  key: string
  required: boolean
  placeholder?: string
  default?: string | number
}

export interface WorkflowTemplate {
  id: string
  name: string
  description?: string
  params: WorkflowTemplateParam[]
}

export const workflowTemplatesApi = {
  list: () => http.get<WorkflowTemplate[]>('/workflow-templates'),
  run: (id: string, params: Record<string, string | number>) =>
    http.post<WorkflowRun>(`/workflow-templates/${id}/runs`, { params }),
}
