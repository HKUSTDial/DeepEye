import { create } from 'zustand'
import { workflowNodesApi, type NodeSpec } from '../api'

export type NodeDefParam = {
  default: string | number | boolean
  required?: boolean
  placeholder?: string
}

export type NodeDefPort = {
  id: string
  label: string
  schema: string
  required?: boolean
  multiple?: boolean
}

export type NodeDef = {
  label: string
  description?: string
  inputs: NodeDefPort[]
  outputs: NodeDefPort[]
  params: Record<string, NodeDefParam>
}

type WorkflowNodesState = {
  nodeDefs: Record<string, NodeDef>
  isLoading: boolean
  error: string | null
  loadNodeDefs: () => Promise<void>
}

const toDefaultValue = (meta: Record<string, unknown> | null) => {
  const type = meta?.type
  if (type === 'integer' || type === 'number') {
    return 0
  }
  if (type === 'boolean') {
    return false
  }
  return ''
}

const typeToLabel = (type: string) =>
  type
    .replace(/[._]/g, ' ')
    .split(' ')
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(' ')

const toSchemaLabel = (schema: string | Record<string, unknown> | null | undefined) => {
  if (typeof schema === 'string' && schema.trim()) {
    return schema
  }
  if (schema && typeof schema === 'object') {
    try {
      return JSON.stringify(schema)
    } catch {
      return 'object'
    }
  }
  return 'any'
}

const mapNodeSpec = (spec: NodeSpec): NodeDef => {
  const inputs = Object.entries(spec.inputs || {}).map(([id, port]) => ({
    id,
    label: id,
    schema: toSchemaLabel(port.schema),
    required: port.required,
    multiple: port.multiple,
  }))
  const outputs = Object.entries(spec.outputs || {}).map(([id, port]) => ({
    id,
    label: id,
    schema: toSchemaLabel(port.schema),
    required: port.required,
    multiple: port.multiple,
  }))
  const params: Record<string, NodeDefParam> = {}
  Object.entries(spec.params_schema || {}).forEach(([key, meta]) => {
    if (meta && typeof meta === 'object') {
      const metaObj = meta as Record<string, unknown>
      params[key] = {
        default: toDefaultValue(metaObj),
        required: Boolean(metaObj.required),
        placeholder: typeof metaObj.description === 'string' ? metaObj.description : undefined,
      }
    } else {
      params[key] = { default: '' }
    }
  })

  return {
    label: typeToLabel(spec.type),
    description: typeof spec.description === 'string' ? spec.description : undefined,
    inputs,
    outputs,
    params,
  }
}

export const useWorkflowNodesStore = create<WorkflowNodesState>((set, get) => ({
  nodeDefs: {},
  isLoading: false,
  error: null,
  loadNodeDefs: async () => {
    if (get().isLoading) return
    if (Object.keys(get().nodeDefs).length > 0) return
    set({ isLoading: true, error: null })
    try {
      const specs = await workflowNodesApi.list()
      const defs = Object.fromEntries(specs.map((spec) => [spec.type, mapNodeSpec(spec)]))
      set({ nodeDefs: defs, isLoading: false })
    } catch (err) {
      set({
        nodeDefs: {},
        isLoading: false,
        error: err instanceof Error ? err.message : 'Failed to load node definitions.',
      })
    }
  },
}))
