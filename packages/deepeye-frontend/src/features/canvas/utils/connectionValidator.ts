/**
 * 连接验证工具
 * 定义节点端口之间的连接规则
 */

import { Node, Edge, Connection } from 'reactflow'
import { registry } from '@/nodes/registry'

/**
 * 端口数据类型
 */
export type PortDataType = 'number' | 'string' | 'boolean' | 'object' | 'array' | 'any'

/**
 * 端口信息接口
 */
export interface PortInfo {
  id: string
  type: 'exec' | 'data'
  dataType?: PortDataType
  allowMultiple?: boolean // 是否允许多个连接（仅对输入端口有效）
}

/**
 * 检测图中是否存在环路（使用 DFS）
 * @param newConnection 即将添加的新连接
 * @param existingEdges 现有的所有边
 * @returns 如果添加新连接会形成环路则返回 true
 */
function wouldCreateCycle(newConnection: Connection, existingEdges: Edge[]): boolean {
  // 构建邻接表（包含新连接）
  const adjacencyList = new Map<string, Set<string>>()
  
  // 添加所有现有边
  existingEdges.forEach(edge => {
    if (!adjacencyList.has(edge.source)) {
      adjacencyList.set(edge.source, new Set())
    }
    adjacencyList.get(edge.source)!.add(edge.target)
  })
  
  // 添加新连接
  const { source, target } = newConnection
  if (!source || !target) return false
  
  if (!adjacencyList.has(source)) {
    adjacencyList.set(source, new Set())
  }
  adjacencyList.get(source)!.add(target)
  
  // 使用 DFS 检测环路
  const visited = new Set<string>()
  const recursionStack = new Set<string>()
  
  function hasCycleDFS(node: string): boolean {
    visited.add(node)
    recursionStack.add(node)
    
    const neighbors = adjacencyList.get(node)
    if (neighbors) {
      for (const neighbor of neighbors) {
        if (!visited.has(neighbor)) {
          if (hasCycleDFS(neighbor)) {
            return true
          }
        } else if (recursionStack.has(neighbor)) {
          // 发现环路
          return true
        }
      }
    }
    
    recursionStack.delete(node)
    return false
  }
  
  // 从所有节点开始检测（处理非连通图）
  const allNodes = new Set<string>()
  adjacencyList.forEach((neighbors, node) => {
    allNodes.add(node)
    neighbors.forEach(n => allNodes.add(n))
  })
  
  for (const node of allNodes) {
    if (!visited.has(node)) {
      if (hasCycleDFS(node)) {
        return true
      }
    }
  }
  
  return false
}

/**
 * 从节点获取端口信息
 */
function getPortInfo(node: Node, handleId: string, isSource: boolean): PortInfo | null {
  // 从注册表获取节点定义
  const nodeType = node.type
  if (!nodeType) {
    return null
  }

  const definition = registry.get(nodeType)
  if (!definition) {
    return null
  }

  // 判断是否是 exec 端口（通常 exec 端口的 ID 包含 'exec'）
  const isExecPort = handleId.includes('exec')

  if (isExecPort) {
    return {
      id: handleId,
      type: 'exec',
    }
  }

  // 数据端口 - 从节点定义中查找端口信息
  if (isSource) {
    // 输出端口
    const portConfig = definition.outputs[handleId]
    if (!portConfig) {
      return null
    }

    return {
      id: handleId,
      type: 'data',
      dataType: portConfig.type as PortDataType,
      allowMultiple: true, // 输出端口总是允许多个连接
    }
  } else {
    // 输入端口
    const portConfig = definition.inputs[handleId]
    if (!portConfig) {
      return null
    }

    return {
      id: handleId,
      type: 'data',
      dataType: portConfig.type as PortDataType,
      allowMultiple: portConfig.multiple ?? false, // 输入端口根据配置，默认不允许多个连接
    }
  }
}

/**
 * 检查数据类型是否兼容
 */
function isDataTypeCompatible(sourceType: PortDataType, targetType: PortDataType): boolean {
  // object 类型可以连接任何类型
  if (sourceType === 'object' || targetType === 'object') {
    return true
  }
  
  // any 类型可以连接任何类型
  if (sourceType === 'any' || targetType === 'any') {
    return true
  }
  
  // 其他类型必须完全匹配
  return sourceType === targetType
}

/**
 * 验证连接是否有效
 *
 * 规则：
 * 1. 不能自连接（同一个节点的端口不能相互连接）
 * 2. 不能形成循环（防止无限循环和死锁）
 * 3. exec 端口只能连接 exec 端口，data 端口只能连接 data 端口
 * 4. data 端口必须类型兼容（object 类型可以连接任何类型）
 *
 * 注意：单输入端口的旧连接会在 onConnect 中自动替换，这里不需要检查
 */
export function isValidConnection(
  connection: Connection,
  nodes: Node[],
  edges: Edge[]
): boolean {
  const { source, target, sourceHandle, targetHandle } = connection

  // 规则 1: 不能自连接
  if (source === target) {
    console.log('[ConnectionValidator] ❌ Self-connection not allowed')
    return false
  }

  // 必须有 handle ID
  if (!sourceHandle || !targetHandle) {
    console.log('[ConnectionValidator] ❌ Missing handle ID')
    return false
  }

  // 规则 2: 不能形成循环
  if (wouldCreateCycle(connection, edges)) {
    console.log('[ConnectionValidator] ❌ Connection would create a cycle')
    return false
  }

  // 查找源节点和目标节点
  const sourceNode = nodes.find(n => n.id === source)
  const targetNode = nodes.find(n => n.id === target)

  if (!sourceNode || !targetNode) {
    console.log('[ConnectionValidator] ❌ Node not found')
    return false
  }

  // 获取端口信息
  const sourcePort = getPortInfo(sourceNode, sourceHandle, true)
  const targetPort = getPortInfo(targetNode, targetHandle, false)

  if (!sourcePort || !targetPort) {
    console.log('[ConnectionValidator] ❌ Port info not found')
    return false
  }

  // 规则 3: exec 和 data 端口类型必须匹配
  if (sourcePort.type !== targetPort.type) {
    console.log('[ConnectionValidator] ❌ Port type mismatch:', sourcePort.type, 'vs', targetPort.type)
    return false
  }

  // 规则 4: 数据端口类型兼容性检查
  if (sourcePort.type === 'data' && targetPort.type === 'data') {
    const sourceDataType = sourcePort.dataType || 'any'
    const targetDataType = targetPort.dataType || 'any'

    if (!isDataTypeCompatible(sourceDataType, targetDataType)) {
      console.log('[ConnectionValidator] ❌ Data type incompatible:', sourceDataType, 'vs', targetDataType)
      return false
    }
  }

  console.log('[ConnectionValidator] ✅ Connection valid')
  return true
}


