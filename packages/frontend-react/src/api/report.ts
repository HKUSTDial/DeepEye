import { http } from './client'

export interface ReportGenerateResponse {
  session_id: string
  message: string
}

export const reportApi = {
  generate: (sessionId: string, message: string, files: File[]) => {
    const form = new FormData()
    form.append('session_id', sessionId)
    form.append('message', message)
    files.forEach((f) => form.append('files', f))
    return http.post<ReportGenerateResponse>('/report/generate', form)
  },
}
