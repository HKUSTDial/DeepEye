import { apiClient } from './client'

export type ColumnMetadata = Record<string, Record<string, unknown>>

export interface FileMetadataPayload {
  summary?: string | null
  annotations?: string | null
  column_metadata?: ColumnMetadata | null
}

export interface FileMetadata extends FileMetadataPayload {
  id: string
  file_id: string
  created_at: string
  updated_at: string
}

export interface ColumnDescription {
  id: string
  table_description_id: string
  column_name: string
  description?: string | null
  created_at: string
  updated_at: string
}

export interface ColumnDescriptionUpdatePayload {
  description?: string | null
}

export interface TableDescription {
  id: string
  connection_id: string
  schema_name: string
  table_name: string
  description?: string | null
  columns: ColumnDescription[]
  created_at: string
  updated_at: string
}

export interface TableDescriptionUpdatePayload {
  description?: string | null
}

export interface BusinessRuleCreatePayload {
  rule_name: string
  description: string
  rule_sql_snippet?: string | null
}

export interface BusinessRuleUpdatePayload {
  rule_name?: string
  description?: string
  rule_sql_snippet?: string | null
}

export interface BusinessRule extends BusinessRuleCreatePayload {
  id: string
  connection_id: string
  created_at: string
  updated_at: string
}

export type MetricDefinitionType = 'SQL_FRAGMENT' | 'NATURAL_LANGUAGE' | 'DERIVED'

export interface BusinessMetricCreatePayload {
  name: string
  alias?: string[] | null
  description: string
  definition_type: MetricDefinitionType
  definition_sql?: string | null
}

export interface BusinessMetricUpdatePayload {
  name?: string
  alias?: string[] | null
  description?: string
  definition_type?: MetricDefinitionType
  definition_sql?: string | null
}

export interface BusinessMetric extends BusinessMetricCreatePayload {
  id: string
  connection_id: string
  created_at: string
  updated_at: string
}

export interface ExampleQueryPayload {
  question: string
  sql_logic: string
}

export interface ExampleQuery extends ExampleQueryPayload {
  id: string
  connection_id: string
  created_at: string
  updated_at: string
}

export const knowledgeAPI = {
  getFileMetadata: (fileId: string) =>
    apiClient.post<FileMetadata>(`/knowledge/file/${fileId}`, {}),
  upsertFileMetadata: (fileId: string, data: FileMetadataPayload) =>
    apiClient.post<FileMetadata>(`/knowledge/file/${fileId}`, data),

  syncDatabaseSchema: (connectionId: string) =>
    apiClient.post<TableDescription[]>(`/knowledge/database/${connectionId}/sync`),
  getTablesByConnection: (connectionId: string) =>
    apiClient.get<TableDescription[]>(`/knowledge/database/${connectionId}/tables`),
  updateTableDescription: (tableId: string, data: TableDescriptionUpdatePayload) =>
    apiClient.put<TableDescription>(`/knowledge/database/tables/${tableId}`, data),
  updateColumnDescription: (columnId: string, data: ColumnDescriptionUpdatePayload) =>
    apiClient.put<ColumnDescription>(`/knowledge/database/columns/${columnId}`, data),

  getBusinessRules: (connectionId: string) =>
    apiClient.get<BusinessRule[]>(`/knowledge/database/${connectionId}/rules`),
  createBusinessRule: (connectionId: string, data: BusinessRuleCreatePayload) =>
    apiClient.post<BusinessRule>(`/knowledge/database/${connectionId}/rules`, data),
  updateBusinessRule: (ruleId: string, data: BusinessRuleUpdatePayload) =>
    apiClient.put<BusinessRule>(`/knowledge/database/rules/${ruleId}`, data),
  deleteBusinessRule: (ruleId: string) =>
    apiClient.delete<void>(`/knowledge/database/rules/${ruleId}`),

  getBusinessMetrics: (connectionId: string) =>
    apiClient.get<BusinessMetric[]>(`/knowledge/database/${connectionId}/metrics`),
  createBusinessMetric: (connectionId: string, data: BusinessMetricCreatePayload) =>
    apiClient.post<BusinessMetric>(`/knowledge/database/${connectionId}/metrics`, data),
  updateBusinessMetric: (metricId: string, data: BusinessMetricUpdatePayload) =>
    apiClient.put<BusinessMetric>(`/knowledge/database/metrics/${metricId}`, data),
  deleteBusinessMetric: (metricId: string) =>
    apiClient.delete<void>(`/knowledge/database/metrics/${metricId}`),

  getExampleQueries: (connectionId: string) =>
    apiClient.get<ExampleQuery[]>(`/knowledge/database/${connectionId}/examples`),
  createExampleQuery: (connectionId: string, data: ExampleQueryPayload) =>
    apiClient.post<ExampleQuery>(`/knowledge/database/${connectionId}/examples`, data),
  deleteExampleQuery: (exampleId: string) =>
    apiClient.delete<void>(`/knowledge/database/examples/${exampleId}`),
}


