/**
 * 节点注册表
 */

import { NodeDefinition } from '../types'

class NodeRegistry {
  private nodes = new Map<string, NodeDefinition>()

  register(def: NodeDefinition) {
    this.nodes.set(def.type, def)
    console.log(`✅ ${def.type}`)
  }

  get(type: string) {
    return this.nodes.get(type)
  }

  getAll() {
    return Array.from(this.nodes.values())
  }

  getByCategory(category: string) {
    return this.getAll().filter(n => n.category === category)
  }

  getCategories() {
    const cats = new Set<string>()
    this.nodes.forEach(n => cats.add(n.category))
    return Array.from(cats).sort()
  }

  async computeNode(type: string, inputs: Record<string, any>) {
    const def = this.get(type)
    if (!def) throw new Error(`Node type "${type}" not found`)

    const instance = new def.class()

    // 设置输入
    Object.keys(def.inputs).forEach(k => {
      instance[k] = k in inputs ? inputs[k] : def.inputs[k].default
    })

    // 设置属性
    Object.keys(def.properties).forEach(k => {
      instance[k] = k in inputs ? inputs[k] : def.properties[k].default
    })

    // 设置输出初始值
    Object.keys(def.outputs).forEach(k => {
      if (k in inputs) instance[k] = inputs[k]
    })

    // 执行
    if (typeof instance.compute === 'function') {
      await instance.compute()
    }

    // 收集输出
    const outputs: Record<string, any> = {}
    Object.keys(def.outputs).forEach(k => {
      if (k in instance) outputs[k] = instance[k]
    })

    return outputs
  }
}

export const registry = new NodeRegistry()

// ============================================================================
// React Flow 集成
// ============================================================================

import { UnifiedNode } from '../components'
import type { NodeTypes } from 'reactflow'

/**
 * 获取 React Flow 节点类型映射
 *
 * 所有节点统一使用 UnifiedNode 组件
 */
export function getNodeTypes(): NodeTypes {
  const nodeTypes: NodeTypes = {}

  registry.getAll().forEach(def => {
    nodeTypes[def.type] = UnifiedNode
  })

  return nodeTypes
}

