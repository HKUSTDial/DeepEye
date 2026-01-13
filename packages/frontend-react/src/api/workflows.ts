import type { Workflow, WorkflowRun } from '../types'
import { http } from './client'

export const workflowsApi = {
  list: () => http.get<Workflow[]>('/workflows'),
  get: (id: string) => http.get<Workflow>(`/workflows/${id}`),
  create: (data: Omit<Workflow, 'id' | 'created_at' | 'updated_at'>) =>
    http.post<Workflow>('/workflows', data),
  update: (id: string, data: Partial<Omit<Workflow, 'id' | 'created_at' | 'updated_at'>>) =>
    http.patch<Workflow>(`/workflows/${id}`, data),
  delete: (id: string) => http.delete<void>(`/workflows/${id}`),
  run: (id: string) => http.post<WorkflowRun>(`/workflows/${id}/runs`),
  getRun: (id: string) => http.get<WorkflowRun>(`/workflows/runs/${id}`),
}
