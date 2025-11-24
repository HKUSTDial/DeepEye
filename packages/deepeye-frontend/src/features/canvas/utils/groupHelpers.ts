/**
 * 组（Group）系统辅助函数 - 扁平化设计
 * 
 * 设计原则：
 * 1. 所有节点都是顶层节点（无 parentNode）
 * 2. 所有位置都是绝对位置
 * 3. 组节点通过 data.memberIds 记录成员
 * 4. 组移动时手动同步成员位置
 * 5. 支持嵌套：组可以是另一个组的成员
 */

import { Node } from 'reactflow'

/**
 * 获取节点的尺寸
 */
export function getNodeSize(node: Node): { width: number; height: number } {
  const width = (node.style?.width as number) || (node.width as number) || 200
  const height = (node.style?.height as number) || (node.height as number) || 100
  return { width, height }
}

/**
 * 计算多个节点的包围盒
 */
export function calculateBoundingBox(
  nodes: Node[],
  padding: number = 30
): {
  x: number
  y: number
  width: number
  height: number
} {
  if (nodes.length === 0) {
    return { x: 0, y: 0, width: 200, height: 150 }
  }

  const bounds = nodes.map((node) => {
    const size = getNodeSize(node)
    return {
      left: node.position.x,
      top: node.position.y,
      right: node.position.x + size.width,
      bottom: node.position.y + size.height,
    }
  })

  const minX = Math.min(...bounds.map((b) => b.left))
  const minY = Math.min(...bounds.map((b) => b.top))
  const maxX = Math.max(...bounds.map((b) => b.right))
  const maxY = Math.max(...bounds.map((b) => b.bottom))

  return {
    x: minX - padding,
    y: minY - padding,
    width: maxX - minX + padding * 2,
    height: maxY - minY + padding * 2,
  }
}

/**
 * 获取组的所有成员ID（扁平的，不递归）
 */
export function getGroupMemberIds(groupNode: Node): string[] {
  if (groupNode.type !== 'group') return []
  return groupNode.data.memberIds || []
}

/**
 * 递归获取组的所有后代成员（包括嵌套组的成员）
 */
export function getAllDescendantIds(groupId: string, allNodes: Node[]): string[] {
  const groupNode = allNodes.find((n) => n.id === groupId && n.type === 'group')
  if (!groupNode) return []

  const memberIds = getGroupMemberIds(groupNode)
  const allDescendants = [...memberIds]

  // 递归查找嵌套组的成员
  memberIds.forEach((memberId) => {
    const member = allNodes.find((n) => n.id === memberId)
    if (member?.type === 'group') {
      const descendants = getAllDescendantIds(memberId, allNodes)
      allDescendants.push(...descendants)
    }
  })

  return allDescendants
}

/**
 * 查找节点所属的直接父组
 */
export function findParentGroup(nodeId: string, allNodes: Node[]): Node | null {
  return allNodes.find((n) => {
    if (n.type !== 'group') return false
    const memberIds = getGroupMemberIds(n)
    return memberIds.includes(nodeId)
  }) || null
}

/**
 * 查找节点所属的所有祖先组（从直接父组到最顶层）
 */
export function findAncestorGroups(nodeId: string, allNodes: Node[]): Node[] {
  const ancestors: Node[] = []
  let currentId = nodeId
  
  while (true) {
    const parentGroup = findParentGroup(currentId, allNodes)
    if (!parentGroup) break
    ancestors.push(parentGroup)
    currentId = parentGroup.id
  }
  
  return ancestors
}

/**
 * 计算组的嵌套深度（0 = 顶层组）
 */
export function getGroupDepth(groupId: string, allNodes: Node[]): number {
  const ancestors = findAncestorGroups(groupId, allNodes)
  return ancestors.length
}

/**
 * 计算组的 zIndex（基于嵌套深度）
 * 越深的组 zIndex 越小（越靠后）
 */
export function calculateGroupZIndex(groupNode: Node, allNodes: Node[]): number {
  const depth = getGroupDepth(groupNode.id, allNodes)
  return -1 - depth
}

/**
 * 更新所有组节点的 zIndex
 */
export function updateAllGroupZIndex(allNodes: Node[]): Node[] {
  return allNodes.map((node) => {
    if (node.type === 'group') {
      const zIndex = calculateGroupZIndex(node, allNodes)
      return {
        ...node,
        style: {
          ...node.style,
          zIndex,
        },
      }
    }
    return node
  })
}

/**
 * 从所有组中移除节点
 */
export function removeNodeFromAllGroups(nodeId: string, allNodes: Node[]): Node[] {
  return allNodes.map((node) => {
    if (node.type === 'group') {
      const memberIds = getGroupMemberIds(node)
      if (memberIds.includes(nodeId)) {
        return {
          ...node,
          data: {
            ...node.data,
            memberIds: memberIds.filter((id) => id !== nodeId),
          },
        }
      }
    }
    return node
  })
}

/**
 * 将节点添加到组
 */
export function addNodeToGroup(nodeId: string, groupId: string, allNodes: Node[]): Node[] {
  // 先从所有组中移除
  let updatedNodes = removeNodeFromAllGroups(nodeId, allNodes)
  
  // 添加到新组
  return updatedNodes.map((node) => {
    if (node.id === groupId && node.type === 'group') {
      const memberIds = getGroupMemberIds(node)
      if (!memberIds.includes(nodeId)) {
        return {
          ...node,
          data: {
            ...node.data,
            memberIds: [...memberIds, nodeId],
          },
        }
      }
    }
    return node
  })
}


