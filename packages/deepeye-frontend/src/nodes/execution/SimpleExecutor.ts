/**
 * 简单执行器
 * 负责根据节点连接关系执行节点的 compute 方法
 */

import { Node, Edge } from 'reactflow'
import { registry } from '../registry'

export class SimpleExecutor {
  private nodes: Node[]
  private edges: Edge[]
  private cache: Map<string, Record<string, any>> = new Map()

  constructor(nodes: Node[], edges: Edge[]) {
    this.nodes = nodes
    this.edges = edges
  }

  /**
   * 执行指定节点（会递归执行所有依赖的上游节点）
   * @param nodeId 要执行的节点 ID
   * @returns 节点的输出数据
   */
  async executeNode(nodeId: string): Promise<Record<string, any>> {
    // 检查缓存
    if (this.cache.has(nodeId)) {
      console.log(`📦 使用缓存: ${nodeId}`)
      return this.cache.get(nodeId)!
    }

    const node = this.nodes.find(n => n.id === nodeId)
    if (!node) {
      throw new Error(`Node ${nodeId} not found`)
    }

    console.log(`🔄 执行节点: ${node.type} (${nodeId})`)

    // 1. 收集输入数据
    const inputs = await this.collectInputs(nodeId)

    // 2. 执行节点（支持 async compute）
    const outputs = await registry.computeNode(node.type || '', inputs)

    // 3. 缓存结果
    this.cache.set(nodeId, outputs)

    console.log(`✅ 节点执行完成: ${node.type}`, { inputs, outputs })

    return outputs
  }

  /**
   * 获取节点的输入数据（不执行节点）
   * @param nodeId 节点 ID
   * @returns 输入数据映射
   */
  async getNodeInputs(nodeId: string): Promise<Record<string, any>> {
    return await this.collectInputs(nodeId)
  }

  /**
   * 收集节点的输入数据
   * @param nodeId 节点 ID
   * @returns 输入数据映射
   */
  private async collectInputs(nodeId: string): Promise<Record<string, any>> {
    const node = this.nodes.find(n => n.id === nodeId)
    if (!node) {
      return {}
    }

    const inputs: Record<string, any> = {}

    // 1. 从节点的 attributes 中获取属性值（用户设置的值）
    const attributes = node.data?.attributes || {}
    Object.assign(inputs, attributes)

    // 2. 从连接的边获取上游节点的输出
    const incomingEdges = this.edges.filter(e => e.target === nodeId)

    // 获取节点定义，检查哪些输入支持多个连接
    const definition = registry.get(node.type || '')
    const multiInputs = new Map<string, any[]>()  // 存储支持多输入的端口数据

    for (const edge of incomingEdges) {
      // 递归执行上游节点
      const sourceOutputs = await this.executeNode(edge.source)

      // 获取源端口的值
      const sourceHandle = edge.sourceHandle || 'output'
      const targetHandle = edge.targetHandle || 'input'

      if (sourceHandle in sourceOutputs) {
        const value = sourceOutputs[sourceHandle]

        // 检查目标端口是否支持多个输入
        const inputDef = definition?.inputs[targetHandle]
        const isMultiple = inputDef?.multiple ?? false

        if (isMultiple) {
          // 支持多输入：收集到数组中
          if (!multiInputs.has(targetHandle)) {
            multiInputs.set(targetHandle, [])
          }
          multiInputs.get(targetHandle)!.push(value)
          console.log(`  📥 输入 (多): ${targetHandle}[] += ${JSON.stringify(value)} (来自 ${edge.source}.${sourceHandle})`)
        } else {
          // 单输入：直接赋值
          inputs[targetHandle] = value
          console.log(`  📥 输入: ${targetHandle} = ${JSON.stringify(value)} (来自 ${edge.source}.${sourceHandle})`)
        }
      }
    }

    // 3. 将多输入数组合并到 inputs 中
    multiInputs.forEach((values, key) => {
      inputs[key] = values
    })

    return inputs
  }

  /**
   * 清除缓存
   */
  clearCache() {
    this.cache.clear()
  }

  /**
   * 清除指定节点及其下游节点的缓存
   * @param nodeId 节点 ID
   */
  invalidateCache(nodeId: string) {
    this.cache.delete(nodeId)

    // 递归清除下游节点的缓存
    const downstreamNodes = this.getDownstreamNodes(nodeId)
    for (const downstreamNodeId of downstreamNodes) {
      this.invalidateCache(downstreamNodeId)
    }
  }

  /**
   * 获取下游节点
   * @param nodeId 节点 ID
   * @returns 下游节点 ID 列表
   */
  private getDownstreamNodes(nodeId: string): string[] {
    const outgoingEdges = this.edges.filter(e => e.source === nodeId)
    return outgoingEdges.map(e => e.target)
  }
}

