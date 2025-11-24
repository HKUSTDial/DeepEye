import { useCallback, useRef, useMemo, useEffect, useState } from 'react'
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  addEdge,
  Connection,
  ReactFlowInstance,
  BackgroundVariant,
  NodeTypes,
  EdgeTypes,
  useNodesState,
  useEdgesState,
  Node,
  Edge,
  SelectionMode,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { useGraphStore, useThemeStore } from '@/store'
import { generateId } from '@/shared/utils'
import { registry, getNodeTypes } from '@/nodes/registry'
import { CustomEdge } from './CustomEdge'
import { ContextMenu, MenuSection } from '@/shared/components'
import { useContextMenu } from '@/shared/hooks'
import { useGraphSync } from '../hooks/useGraphSync'
import {
  Copy,
  Scissors,
  Clipboard,
  Trash2,
  CopyPlus,
  MousePointerClick,
  LogOut,
  FolderMinus,
  FolderInput,
} from 'lucide-react'
import {
  calculateBoundingBox,
  getGroupMemberIds,
  getAllDescendantIds,
  removeNodeFromAllGroups,
  addNodeToGroup as addNodeToGroupHelper,
  updateAllGroupZIndex,
  findParentGroup,
} from '../utils/groupHelpers'
import { isValidConnection as validateConnection } from '../utils/connectionValidator'

export function Canvas() {
  const reactFlowWrapper = useRef<HTMLDivElement>(null)
  const reactFlowInstance = useRef<ReactFlowInstance | null>(null)
  
  // ============ 拖动添加到组的状态 ============
  const [isDraggingToGroup, setIsDraggingToGroup] = useState(false)
  const [draggingNodeIds, setDraggingNodeIds] = useState<string[]>([])
  const [hoveredGroupId, setHoveredGroupId] = useState<string | null>(null)

  // ============ 全局右键菜单拦截 ============
  useEffect(() => {
    const handleContextMenu = (e: MouseEvent) => {
      const target = e.target as HTMLElement
      
      // 检查是否在 reactFlowWrapper 内 
      if (reactFlowWrapper.current?.contains(target)) {
        e.preventDefault()
      }
    }

    document.addEventListener('contextmenu', handleContextMenu)
    return () => {
      document.removeEventListener('contextmenu', handleContextMenu)
    }
  }, [])

  // ============ 从 Store 获取状态 ============
  const {
    nodes: storeNodes,
    edges: storeEdges,
    setNodes: setStoreNodes,
    setEdges: setStoreEdges,
    setSelectedNodes,
    isUndoRedoing,
    copyNodes,
    cutNodes,
    pasteNodes,
    duplicateNodes,
    clipboard,
    updateNodeData,
  } = useGraphStore()
  
  // 获取主题
  const theme = useThemeStore((state) => state.theme)
  const isDark = theme === 'dark'

  // ============ React Flow 本地状态 ============
  const [nodes, setNodes, onNodesChange] = useNodesState(storeNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(storeEdges)
  
  // 记录组节点的上一次位置（用于检测移动）
  const groupPositionsRef = useRef<Map<string, { x: number; y: number }>>(new Map())

  // ============ 右键菜单 ============
  const { menuState, showMenu, hideMenu } = useContextMenu()

  // ============ 统一的状态同步管理 ============
  useGraphSync({
    nodes,
    edges,
    setNodes,
    setEdges,
    storeNodes,
    storeEdges,
    setStoreNodes,
    setStoreEdges,
    isUndoRedoing,
  })

  // 注意：执行状态的可视化由 ExecutionHighlight 组件独立处理
  // 不再通过修改节点 data 来实现，避免与状态同步冲突
  
  // ============ 组移动同步 - 扁平化设计的关键 ============
  /**
   * 监听组节点的移动，同步移动所有成员
   * 这是扁平化设计的核心：手动维护组和成员的位置关系
   */
  useEffect(() => {
    // 检测组节点是否移动
    nodes.forEach((node) => {
      if (node.type === 'group') {
        const oldPos = groupPositionsRef.current.get(node.id)
        const newPos = node.position
        
        // 如果位置发生变化
        if (oldPos && (oldPos.x !== newPos.x || oldPos.y !== newPos.y)) {
          const deltaX = newPos.x - oldPos.x
          const deltaY = newPos.y - oldPos.y
          
          // 同步移动所有成员
          const memberIds = getGroupMemberIds(node)
          if (memberIds.length > 0) {
            setNodes((nds) =>
              nds.map((n) => {
                if (memberIds.includes(n.id)) {
                  return {
                    ...n,
                    position: {
                      x: n.position.x + deltaX,
                      y: n.position.y + deltaY,
                    },
                  }
                }
                return n
              })
            )
          }
        }
        
        // 更新记录的位置
        groupPositionsRef.current.set(node.id, { ...newPos })
      }
    })
    
    // 清理已删除的组
    const currentGroupIds = new Set(
      nodes.filter((n) => n.type === 'group').map((n) => n.id)
    )
    groupPositionsRef.current.forEach((_, id) => {
      if (!currentGroupIds.has(id)) {
        groupPositionsRef.current.delete(id)
      }
    })
  }, [nodes, setNodes])

  // ============ React Flow 配置 ============

  // 从注册表获取节点类型
  const nodeTypes: NodeTypes = useMemo(() => getNodeTypes(), [])

  const edgeTypes: EdgeTypes = useMemo(
    () => ({
      default: CustomEdge,
    }),
    []
  )

  // ============ 事件处理 ============

  // 连接验证函数
  const isValidConnection = useCallback(
    (connection: Connection) => {
      return validateConnection(connection, nodes, edges)
    },
    [nodes, edges]
  )

  const onConnect = useCallback(
    (connection: Connection) => {
      const { source, sourceHandle, target, targetHandle } = connection

      if (!target || !targetHandle) {
        setEdges((eds) => addEdge(connection, eds))
        return
      }

      // 检查目标端口是否支持多个连接
      const targetNode = nodes.find(n => n.id === target)
      if (!targetNode || !targetNode.type) {
        setEdges((eds) => addEdge(connection, eds))
        return
      }

      const definition = registry.get(targetNode.type)
      const inputDef = definition?.inputs[targetHandle]
      const isMultiple = inputDef?.multiple ?? false

      if (!isMultiple) {
        // 单输入端口：移除旧连接，添加新连接
        setEdges((eds) => {
          // 移除所有连接到该端口的旧边
          const filteredEdges = eds.filter(
            e => !(e.target === target && e.targetHandle === targetHandle)
          )
          // 添加新边
          return addEdge(connection, filteredEdges)
        })
        console.log(`🔄 替换单输入端口的连接: ${target}.${targetHandle}`)
      } else {
        // 多输入端口：直接添加新连接
        setEdges((eds) => addEdge(connection, eds))
      }

      // 🔥 新增：连接建立后，从上游节点获取缓存数据并更新下游节点
      if (source && sourceHandle) {
        const sourceNode = nodes.find(n => n.id === source)
        if (sourceNode && sourceNode.data?.attributes) {
          const sourceAttributes = sourceNode.data.attributes

          // 检查源节点的输出端口是否有值
          if (sourceHandle in sourceAttributes) {
            const value = sourceAttributes[sourceHandle]

            console.log(`🔗 连接建立，传递数据: ${source}.${sourceHandle} → ${target}.${targetHandle}`)
            console.log(`  数据:`, value)

            // 更新目标节点的属性
            updateNodeData(target, {
              attributes: {
                ...targetNode.data.attributes,
                [targetHandle]: value
              }
            })
          }
        }
      }
    },
    [setEdges, nodes, updateNodeData]
  )

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault()
    event.dataTransfer.dropEffect = 'move'
  }, [])

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault()

      const type = event.dataTransfer.getData('application/reactflow')
      if (typeof type === 'undefined' || !type) return
      if (!reactFlowInstance.current) return

      const position = reactFlowInstance.current.screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      })

      // 从注册表获取节点定义
      const nodeDef = registry.get(type)

      // 收集默认值
      const defaultAttributes: Record<string, any> = {}

      // 从 inputs 收集默认值
      if (nodeDef?.inputs) {
        Object.entries(nodeDef.inputs).forEach(([key, input]) => {
          if (input.default !== undefined) {
            defaultAttributes[key] = input.default
          }
        })
      }

      // 从 properties 收集默认值
      if (nodeDef?.properties) {
        Object.entries(nodeDef.properties).forEach(([key, prop]) => {
          if (prop.default !== undefined) {
            defaultAttributes[key] = prop.default
          }
        })
      }

      const newNode = {
        id: generateId(),
        type, // ✅ React Flow 会自动传递 type 给节点组件
        position,
        data: {
          label: nodeDef?.label || type,
          attributes: defaultAttributes, // 使用默认值初始化
        },
      }

      setNodes((nds) => nds.concat(newNode))
    },
    [setNodes]
  )

  // 处理节点选择
  const onSelectionChange = useCallback(
    ({ nodes: selectedNodes }: { nodes: any[] }) => {
      const selectedIds = selectedNodes.map((node) => node.id)
      
      // 只更新 selectedNodes 数组，不直接修改节点
      // ReactFlow 会自动处理节点的 selected 属性
      setSelectedNodes(selectedIds)
      
      if (import.meta.env.DEV) {
        console.log('🎯 Selection changed:', selectedIds.length, 'nodes')
      }
    },
    [setSelectedNodes]
  )

  // 双击节点处理 - UE 风格组不需要折叠/展开，移除此逻辑
  const onNodeDoubleClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      // 预留给其他节点类型的双击处理
      if (import.meta.env.DEV) {
        console.log('🖱️ Double clicked node:', node.id, node.type)
      }
    },
    []
  )

  // ============ 组（Comment Box）功能 - UE 蓝图风格 ============
  
  /**
   * 创建 Comment Box - 扁平化设计
   * 
   * 设计原则：
   * - 所有节点保持顶层（无 parentNode）
   * - 所有位置都是绝对位置
   * - 组通过 data.memberIds 记录成员
   * - 支持嵌套：组可以是另一个组的成员
   */
  const createGroup = useCallback((nodeIds: string[], color: string = 'orange') => {
    if (nodeIds.length === 0) return
    
    // 获取选中节点
    const selectedNodes = nodes.filter((n) => nodeIds.includes(n.id))
    if (selectedNodes.length === 0) return
    
    // 计算包围盒
    const bbox = calculateBoundingBox(selectedNodes)
    
    // 创建新组节点
    const groupId = generateId()
    const groupNode: Node = {
      id: groupId,
      type: 'group',
      position: { x: bbox.x, y: bbox.y },
      style: {
        width: bbox.width,
        height: bbox.height,
        zIndex: -1,
      },
      data: {
        label: `Comment ${Date.now().toString().slice(-4)}`,
        description: '',
        color,
        memberIds: nodeIds, // 记录成员ID
      },
    }
    
    // 从其他组中移除这些节点，然后添加新组
    setNodes((nds) => {
      let updatedNodes = nds
      // 从所有现有组中移除这些节点
      nodeIds.forEach((nodeId) => {
        updatedNodes = removeNodeFromAllGroups(nodeId, updatedNodes)
      })
      // 添加新组并重新计算 zIndex
      return updateAllGroupZIndex([...updatedNodes, groupNode])
    })
    
    // 清除选择
    setSelectedNodes([])
    
    console.log(`✅ Created group with ${nodeIds.length} nodes`)
  }, [nodes, setNodes, setSelectedNodes])

  /**
   * 将节点从组中移除
   */
  const removeNodeFromGroup = useCallback((nodeId: string) => {
    setNodes((nds) => removeNodeFromAllGroups(nodeId, nds))
    console.log(`✅ Removed node ${nodeId} from all groups`)
  }, [setNodes])

  /**
   * 开始拖动节点以添加到组（支持单选或多选）
   */
  const startDragToAddToGroup = useCallback((nodeIds: string[]) => {
    setIsDraggingToGroup(true)
    setDraggingNodeIds(nodeIds)
    setHoveredGroupId(null)
    hideMenu()
    console.log(`🎯 Started drag-to-group mode for ${nodeIds.length} node(s)`)
  }, [hideMenu])

  /**
   * 检测节点与哪些组重叠，返回最小的组
   */
  const getOverlappingGroup = useCallback((nodeId: string): string | null => {
    const node = nodes.find((n) => n.id === nodeId)
    if (!node) return null
    
    const nodeWidth = (node.width as number) || 200
    const nodeHeight = (node.height as number) || 100
    const nodeBounds = {
      left: node.position.x,
      top: node.position.y,
      right: node.position.x + nodeWidth,
      bottom: node.position.y + nodeHeight,
    }
    
    // 找出所有与节点重叠的组
    const overlappingGroups = nodes
      .filter((n) => n.type === 'group' && n.id !== nodeId)
      .map((group) => {
        const groupWidth = (group.width as number) || (group.style?.width as number) || 400
        const groupHeight = (group.height as number) || (group.style?.height as number) || 300
        const groupBounds = {
          left: group.position.x,
          top: group.position.y,
          right: group.position.x + groupWidth,
          bottom: group.position.y + groupHeight,
        }
        
        // 检测重叠
        const isOverlapping = !(
          nodeBounds.right < groupBounds.left ||
          nodeBounds.left > groupBounds.right ||
          nodeBounds.bottom < groupBounds.top ||
          nodeBounds.top > groupBounds.bottom
        )
        
        if (isOverlapping) {
          const area = groupWidth * groupHeight
          return { id: group.id, area }
        }
        return null
      })
      .filter((g): g is { id: string; area: number } => g !== null)
    
    // 返回面积最小的组（最内层）
    if (overlappingGroups.length === 0) return null
    overlappingGroups.sort((a, b) => a.area - b.area)
    return overlappingGroups[0].id
  }, [nodes])

  /**
   * 将节点加入到指定的组
   */
  const addNodeToGroup = useCallback((nodeId: string, groupId: string) => {
    setNodes((nds) => addNodeToGroupHelper(nodeId, groupId, nds))
    console.log(`✅ Added node ${nodeId} to group ${groupId}`)
  }, [setNodes])

  // ============ 拖动添加到组的事件处理 ============
  
  // 节点拖动时 - 检测是否与组重叠
  const onNodeDrag = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      if (isDraggingToGroup && draggingNodeIds.includes(node.id)) {
        const overlappingGroupId = getOverlappingGroup(node.id)
        if (overlappingGroupId !== hoveredGroupId) {
          setHoveredGroupId(overlappingGroupId)
        }
      }
    },
    [isDraggingToGroup, draggingNodeIds, hoveredGroupId, getOverlappingGroup]
  )

  // 节点拖动结束 - 自动添加到组
  const onNodeDragStop = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      if (isDraggingToGroup && draggingNodeIds.includes(node.id)) {
        const overlappingGroupId = getOverlappingGroup(node.id)
        
        if (overlappingGroupId) {
          // 将所有拖拽的节点都添加到组
          draggingNodeIds.forEach((nodeId) => {
            addNodeToGroup(nodeId, overlappingGroupId)
          })
          console.log(`✅ Added ${draggingNodeIds.length} node(s) to group ${overlappingGroupId}`)
        }
        
        // 退出拖动模式
        setIsDraggingToGroup(false)
        setDraggingNodeIds([])
        setHoveredGroupId(null)
      }
    },
    [isDraggingToGroup, draggingNodeIds, getOverlappingGroup, addNodeToGroup]
  )

  /**
   * 解散组 - 删除组节点，但保留所有成员
   */
  const ungroupNodes = useCallback((groupId: string) => {
    const groupNode = nodes.find((n) => n.id === groupId && n.type === 'group')
    if (!groupNode) return
    
    const memberIds = getGroupMemberIds(groupNode)
    
    // 直接删除组节点（成员已经是独立的顶层节点）
    setNodes((nds) => nds.filter((n) => n.id !== groupId))
    
    console.log(`✅ Ungrouped: ${groupNode.data.label}, released ${memberIds.length} nodes`)
  }, [nodes, setNodes])

  /**
   * 删除节点 - 扁平化设计，简单直接
   * - 如果删除组节点，连同所有成员一起删除（支持嵌套）
   * - 如果只想删除组但保留节点，使用"解散组"功能
   */
  const handleRemoveNodes = useCallback((nodeIds: string[]) => {
    const allNodesToDelete = new Set<string>(nodeIds)
    
    // 递归找出所有组节点的成员
    nodeIds.forEach((id) => {
      const descendants = getAllDescendantIds(id, nodes)
      descendants.forEach((descendantId) => allNodesToDelete.add(descendantId))
    })
    
    // 直接删除（扁平化设计，无需清理 parentNode）
    setNodes((nds) => {
      // 先从所有组中移除要删除的节点引用
      let updatedNodes = nds
      allNodesToDelete.forEach((nodeId) => {
        updatedNodes = removeNodeFromAllGroups(nodeId, updatedNodes)
      })
      // 然后删除节点
      return updatedNodes.filter((n) => !allNodesToDelete.has(n.id))
    })
    
    console.log(`🗑️ Deleted ${allNodesToDelete.size} nodes (including all descendants)`)
  }, [nodes, setNodes])
  
  // ============ 右键菜单处理 ============

  /**
   * 画布右键菜单
   */
  const handlePaneContextMenu = useCallback((event: React.MouseEvent) => {
    event.preventDefault()
    
    const flowPosition = reactFlowInstance.current?.screenToFlowPosition({
      x: event.clientX,
      y: event.clientY,
    })

    showMenu(event, {
      type: 'pane',
      position: flowPosition,
    })
  }, [showMenu])

  /**
   * 节点右键菜单
   */
  const handleNodeContextMenu = useCallback((event: React.MouseEvent, node: Node) => {
    event.preventDefault()
    event.stopPropagation()
    
    showMenu(event, {
      type: 'node',
      node,
    })
  }, [showMenu])

  /**
   * 边右键菜单
   */
  const handleEdgeContextMenu = useCallback((event: React.MouseEvent, edge: Edge) => {
    event.preventDefault()
    event.stopPropagation()
    
    showMenu(event, {
      type: 'edge',
      edge,
    })
  }, [showMenu])

  // ============ 菜单配置 ============

  const menuSections = useMemo((): MenuSection[] => {
    if (!menuState.visible) return []

    const { data } = menuState
    const isMac = typeof navigator !== 'undefined' && 
                  navigator.platform.toUpperCase().indexOf('MAC') >= 0
    const modKey = isMac ? '⌘' : 'Ctrl'

    // 画布菜单
    if (data?.type === 'pane') {
      return [
        {
          items: [
            {
              id: 'paste',
              label: 'Paste',
              icon: Clipboard,
              shortcut: `${modKey}+V`,
              disabled: !clipboard || clipboard.nodes.length === 0,
              onClick: () => {
                if (data.position) {
                  pasteNodes(data.position)
                } else {
                  pasteNodes()
                }
              },
            },
            {
              id: 'select-all',
              label: 'Select All',
              icon: MousePointerClick,
              shortcut: `${modKey}+A`,
              onClick: () => {
                useGraphStore.getState().selectAll()
              },
            },
          ],
        },
      ]
    }

    // 节点菜单
    if (data?.type === 'node') {
      const selectedNodes = useGraphStore.getState().selectedNodes
      const isMultiSelect = selectedNodes.length > 1
      const nodeIds = isMultiSelect ? selectedNodes : [data.node.id]
      
      // 找出所有可用的组节点（排除当前节点本身，如果是组的话）
      const availableGroups = nodes.filter(
        (n) => n.type === 'group' && n.id !== data.node.id
      )

      return [
        {
          items: [
            {
              id: 'copy',
              label: `Copy${isMultiSelect ? ` (${nodeIds.length})` : ''}`,
              icon: Copy,
              shortcut: `${modKey}+C`,
              onClick: () => copyNodes(nodeIds),
            },
            {
              id: 'cut',
              label: `Cut${isMultiSelect ? ` (${nodeIds.length})` : ''}`,
              icon: Scissors,
              shortcut: `${modKey}+X`,
              onClick: () => cutNodes(nodeIds),
            },
            {
              id: 'duplicate',
              label: `Duplicate${isMultiSelect ? ` (${nodeIds.length})` : ''}`,
              icon: CopyPlus,
              shortcut: `${modKey}+D`,
              onClick: () => duplicateNodes(nodeIds),
            },
            {
              id: 'divider-1',
              label: '',
              divider: true,
            },
            // 节点在组内：显示"移出组"（支持单选和多选）
            ...(() => {
              // 检查选中的节点中是否有在组内的
              const nodesInGroup = nodeIds.filter(id => findParentGroup(id, nodes) !== null)
              
              if (nodesInGroup.length > 0) {
                return [
                  {
                    id: 'remove-from-group',
                    label: isMultiSelect 
                      ? `Remove from Group (${nodesInGroup.length})` 
                      : 'Remove from Group',
                    icon: LogOut,
                    onClick: () => {
                      nodesInGroup.forEach(nodeId => removeNodeFromGroup(nodeId))
                      console.log(`✅ Removed ${nodesInGroup.length} node(s) from groups`)
                    },
                  },
                  {
                    id: 'divider-remove',
                    label: '',
                    divider: true,
                  },
                ]
              }
              return []
            })(),
            // 单个组节点：显示"解散组"
            ...(!isMultiSelect && data.node.type === 'group'
              ? [
                  {
                    id: 'ungroup',
                    label: 'Ungroup',
                    icon: FolderMinus,
                    shortcut: `${modKey}+Shift+G`,
                    onClick: () => ungroupNodes(data.node.id),
                  },
                  {
                    id: 'divider-ungroup',
                    label: '',
                    divider: true,
                  },
                ]
              : []),
            // 显示"添加到组（拖动）"选项（单选或多选，排除组节点本身）
            ...(availableGroups.length > 0 && 
                (!isMultiSelect ? data.node.type !== 'group' : !nodeIds.every(id => nodes.find(n => n.id === id)?.type === 'group'))
              ? [
                  {
                    id: 'drag-to-add-group',
                    label: isMultiSelect 
                      ? `Add to Group (Drag) (${nodeIds.length})` 
                      : 'Add to Group (Drag)',
                    icon: FolderInput,
                    onClick: () => startDragToAddToGroup(nodeIds),
                  },
                  {
                    id: 'divider-add-group',
                    label: '',
                    divider: true,
                  },
                ]
              : []),
            {
              id: 'delete',
              label: `Delete${isMultiSelect ? ` (${nodeIds.length})` : ''}`,
              icon: Trash2,
              shortcut: 'Del',
              danger: true,
              onClick: () => handleRemoveNodes(nodeIds),
            },
          ],
        },
        // Comment Box 创建菜单（多选时）
        ...(isMultiSelect
          ? [
              {
                title: `Add Comment Box (${nodeIds.length} items)`,
                items: [
                  {
                    id: 'comment-orange',
                    label: '🟠 Orange',
                    onClick: () => createGroup(nodeIds, 'orange'),
                  },
                  {
                    id: 'comment-blue',
                    label: '🔵 Blue',
                    onClick: () => createGroup(nodeIds, 'blue'),
                  },
                  {
                    id: 'comment-green',
                    label: '🟢 Green',
                    onClick: () => createGroup(nodeIds, 'green'),
                  },
                  {
                    id: 'comment-red',
                    label: '🔴 Red',
                    onClick: () => createGroup(nodeIds, 'red'),
                  },
                  {
                    id: 'comment-purple',
                    label: '🟣 Purple',
                    onClick: () => createGroup(nodeIds, 'purple'),
                  },
                  {
                    id: 'comment-gray',
                    label: '⚪ Gray',
                    onClick: () => createGroup(nodeIds, 'gray'),
                  },
                ],
              },
            ]
          : []),
      ]
    }

    // 边菜单
    if (data?.type === 'edge') {
      return [
        {
          items: [
            {
              id: 'delete-edge',
              label: 'Delete Edge',
              icon: Trash2,
              shortcut: 'Del',
              danger: true,
              onClick: () => {
                useGraphStore.getState().removeEdge(data.edge.id)
              },
            },
          ],
        },
      ]
    }

    return []
  }, [menuState, clipboard, copyNodes, cutNodes, pasteNodes, duplicateNodes, handleRemoveNodes, createGroup, removeNodeFromGroup, ungroupNodes, startDragToAddToGroup, nodes])

  return (
    <div ref={reactFlowWrapper} className="flex-1 relative">
      <ReactFlow
        nodes={nodes.map((node) => ({
          ...node,
          // 为 hover 的组添加视觉反馈
          className: node.id === hoveredGroupId ? 'group-hover-highlight' : undefined,
        }))}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        isValidConnection={isValidConnection}
        onSelectionChange={onSelectionChange}
        onNodeDoubleClick={onNodeDoubleClick}
        onNodeDrag={onNodeDrag}
        onNodeDragStop={onNodeDragStop}
        onInit={(instance) => {
          reactFlowInstance.current = instance
        }}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onPaneContextMenu={handlePaneContextMenu}
        onNodeContextMenu={handleNodeContextMenu}
        onEdgeContextMenu={handleEdgeContextMenu}
        onlyRenderVisibleElements={false}
        className="bg-background"
        // 操作逻辑优化
        selectionOnDrag={true}                  // 左键拖动框选节点
        panOnDrag={[1]}                         // 中键拖动画布
        panOnScroll={false}                     // 禁用滚轮平移
        zoomOnScroll={true}                     // 滚轮缩放
        zoomOnPinch={true}                      // 触摸板缩放
        zoomOnDoubleClick={true}                // 双击缩放
        selectionMode={SelectionMode.Partial}   // 部分重叠即可选中
        selectNodesOnDrag={true}                // 拖动时选中节点
        selectionKeyCode={null}                 // 无需按键即可框选
        panActivationKeyCode="Space"            // 空格键 + 拖动平移画布
        multiSelectionKeyCode="Shift"           // Shift 多选
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={16}
          size={2}
          color={isDark ? 'hsl(0 0% 35%)' : 'hsl(0 0% 65%)'}
          className="opacity-50"
        />
        <Controls />
        <MiniMap
          nodeColor={(node) => {
            const nodeDef = registry.get(node.type || '')
            return nodeDef?.color || 'hsl(var(--muted))'
          }}
        />
      </ReactFlow>

      {/* 右键菜单 */}
      {menuState.visible && (
        <ContextMenu
          x={menuState.x}
          y={menuState.y}
          sections={menuSections}
          onClose={hideMenu}
        />
      )}
    </div>
  )
}


