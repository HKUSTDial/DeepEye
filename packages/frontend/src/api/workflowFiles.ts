import { http } from './client'

export const workflowFilesApi = {
  run: (sessionId: string, path: string) =>
    http.post<{ status: string; task_id?: string; error?: string; outputs?: Record<string, unknown> }>(
      '/workflow-files/run',
      {
        session_id: sessionId,
        path,
      },
    ),
}
