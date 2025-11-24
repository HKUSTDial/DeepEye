import { apiClient } from './client'

export interface LLMModel {
  id: string
  user_id: string
  base_url: string
  model_endpoint_name: string
  model_name?: string | null
  created_at: string
  updated_at: string
}

export interface LLMModelCreate {
  base_url: string
  model_endpoint_name: string
  model_name?: string
  api_key: string
}

export interface LLMModelUpdate {
  base_url?: string
  model_endpoint_name?: string
  model_name?: string | null
  api_key?: string
}

export const llmModelsAPI = {
  list: (skip = 0, limit = 100) => apiClient.get<LLMModel[]>('/llm-models', { skip, limit }),
  create: (data: LLMModelCreate) => apiClient.post<LLMModel>('/llm-models', data),
  update: (id: string, data: LLMModelUpdate) =>
    apiClient.put<LLMModel>(`/llm-models/${id}`, data),
  delete: (id: string) => apiClient.delete<void>(`/llm-models/${id}`),
}


