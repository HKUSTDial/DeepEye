import { http } from './client'

export const workflowFilesApi = {
  run: (sessionId: string, path: string) =>
    http.post<{
      status: string
      task_id?: string
      turn_id?: string | null
      draft_id?: string | null
      run_id?: string | null
      error?: string
      outputs?: Record<string, unknown>
    }>(
      '/workflow-files/run',
      {
        session_id: sessionId,
        path,
      },
    ),
}
