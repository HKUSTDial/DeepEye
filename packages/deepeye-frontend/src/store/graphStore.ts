import { create } from 'zustand'
import { Node, Edge, Viewport } from 'reactflow'
import { GraphState } from '@/shared/types'

// ============ 配置常量 ============
const HISTORY_CONFIG = {
  MAX_HISTORY_SIZE: 50, // 最大历史记录数
  DEBOUNCE_DELAY: 300,  // 防抖延迟（毫秒）
} as const

// ============ 工具函数 ============

/**
 * 深拷贝图状态，避免引用问题
 */
function deepCloneGraphState(state: GraphState): GraphState {
  return {
    nodes: JSON.parse(JSON.stringify(state.nodes)),
    edges: JSON.parse(JSON.stringify(state.edges)),
    viewport: { ...state.viewport },
    timestamp: state.timestamp,
  }
}

/**
 * 比较两个状态是否相同（浅比较，性能考虑）
 */
function isStateSame(a: GraphState, b: GraphState): boolean {
  return (
    a.nodes.length === b.nodes.length &&
    a.edges.length === b.edges.length &&
    JSON.stringify(a.nodes) === JSON.stringify(b.nodes) &&
    JSON.stringify(a.edges) === JSON.stringify(b.edges)
  )
}

// ============ Store 接口 ============
interface GraphStore {
  // 核心状态
  nodes: Node[]
  edges: Edge[]
  selectedNodes: string[]
  selectedEdges: string[]
  viewport: Viewport
  
  // 历史记录
  history: GraphState[]
  currentHistoryIndex: number
  isUndoRedoing: boolean // 标记是否正在撤销/重做（避免重复保存）
  
  // 剪贴板
  clipboard: {
    nodes: Node[]
    edges: Edge[]
  } | null
  
  // 节点操作
  addNode: (node: Node) => void
  updateNode: (id: string, data: Partial<Node>) => void
  updateNodeData: (id: string, data: Record<string, any>) => void
  removeNode: (id: string) => void
  removeNodes: (ids: string[]) => void
  setNodes: (nodes: Node[] | ((nodes: Node[]) => Node[])) => void
  duplicateNodes: (ids: string[]) => void

  // 边操作
  addEdge: (edge: Edge) => void
  updateEdge: (id: string, data: Partial<Edge>) => void
  removeEdge: (id: string) => void
  setEdges: (edges: Edge[] | ((edges: Edge[]) => Edge[])) => void

  // 选择操作
  setSelectedNodes: (ids: string[]) => void
  setSelectedEdges: (ids: string[]) => void
  clearSelection: () => void
  selectAll: () => void

  // 视图操作
  setViewport: (viewport: Viewport) => void

  // 剪贴板操作
  copyNodes: (ids: string[]) => void
  cutNodes: (ids: string[]) => void
  pasteNodes: (position?: { x: number; y: number }) => void

  // 历史记录操作
  undo: () => void
  redo: () => void
  saveToHistory: () => void
  canUndo: () => boolean
  canRedo: () => boolean

  // 节点历史记录操作
  addNodeHistory: (nodeId: string, entry: Omit<import('@/shared/types').NodeHistoryEntry, 'id' | 'timestamp'>) => void
  getNodeHistory: (nodeId: string) => import('@/shared/types').NodeHistoryEntry[]
  restoreNodeHistory: (nodeId: string, historyId: string) => void
  clearNodeHistory: (nodeId: string) => void

  // 工具方法
  clear: () => void
  getHistoryInfo: () => { current: number; total: number; canUndo: boolean; canRedo: boolean }
}

// ============ 防抖定时器（模块级别） ============
let saveHistoryTimer: ReturnType<typeof setTimeout> | null = null

// ============ Store 实现 ============
export const useGraphStore = create<GraphStore>((set, get) => ({
  // 初始状态
  nodes: [],
  edges: [],
  selectedNodes: [],
  selectedEdges: [],
  viewport: { x: 0, y: 0, zoom: 1 },
  history: [],
  currentHistoryIndex: -1,
  isUndoRedoing: false,
  clipboard: null,

  // ============ 节点操作 ============
  
  addNode: (node) => {
    set((state) => ({
      nodes: [...state.nodes, node],
    }))
    get().saveToHistory()
  },

  updateNode: (id, data) => {
    set((state) => ({
      nodes: state.nodes.map((node) =>
        node.id === id ? { ...node, ...data } : node
      ),
    }))
    // 节点更新使用防抖保存
    get().saveToHistory()
  },

  updateNodeData: (id, data) => {
    set((state) => ({
      nodes: state.nodes.map((node) =>
        node.id === id ? { ...node, data: { ...node.data, ...data } } : node
      ),
    }))
    // 节点数据更新使用防抖保存
    get().saveToHistory()
  },

  removeNode: (id) => {
    set((state) => ({
      nodes: state.nodes.filter((node) => node.id !== id),
      edges: state.edges.filter(
        (edge) => edge.source !== id && edge.target !== id
      ),
    }))
    get().saveToHistory()
  },

  removeNodes: (ids) => {
    set((state) => ({
      nodes: state.nodes.filter((node) => !ids.includes(node.id)),
      edges: state.edges.filter(
        (edge) => !ids.includes(edge.source) && !ids.includes(edge.target)
      ),
      selectedNodes: state.selectedNodes.filter((id) => !ids.includes(id)),
    }))
    get().saveToHistory()
  },

  duplicateNodes: (ids) => {
    const state = get()
    const nodesToDuplicate = state.nodes.filter((n) => ids.includes(n.id))
    
    if (nodesToDuplicate.length === 0) return

    const timestamp = Date.now()
    
    // 生成新节点（偏移位置）
    const newNodes = nodesToDuplicate.map((node, index) => ({
      ...node,
      id: `${node.id}-duplicate-${timestamp}-${index}`,
      position: {
        x: node.position.x + 50,
        y: node.position.y + 50,
      },
      selected: true, // 复制后选中新节点
    }))

    // 取消旧节点选中，添加新节点
    set((state) => ({
      nodes: [
        ...state.nodes.map(n => ({ ...n, selected: false })),
        ...newNodes
      ],
      selectedNodes: newNodes.map(n => n.id),
    }))
    
    get().saveToHistory()

    if (import.meta.env.DEV) {
      console.log('📋 Duplicated nodes:', {
        count: newNodes.length,
        newIds: newNodes.map(n => n.id),
      })
    }
  },

  setNodes: (nodesOrUpdater) => {
    const { isUndoRedoing } = get()
    set((state) => ({
      nodes:
        typeof nodesOrUpdater === 'function'
          ? nodesOrUpdater(state.nodes)
          : nodesOrUpdater,
    }))
    // 如果不是撤销/重做操作，则保存历史
    if (!isUndoRedoing) {
      get().saveToHistory()
    }
  },

  // ============ 边操作 ============
  
  addEdge: (edge) => {
    set((state) => ({
      edges: [...state.edges, edge],
    }))
    get().saveToHistory()
  },

  updateEdge: (id, data) => {
    set((state) => ({
      edges: state.edges.map((edge) =>
        edge.id === id ? { ...edge, ...data } : edge
      ),
    }))
    get().saveToHistory()
  },

  removeEdge: (id) => {
    set((state) => ({
      edges: state.edges.filter((edge) => edge.id !== id),
    }))
    get().saveToHistory()
  },

  setEdges: (edgesOrUpdater) => {
    const { isUndoRedoing } = get()
    set((state) => ({
      edges:
        typeof edgesOrUpdater === 'function'
          ? edgesOrUpdater(state.edges)
          : edgesOrUpdater,
    }))
    // 如果不是撤销/重做操作，则保存历史
    if (!isUndoRedoing) {
      get().saveToHistory()
    }
  },

  // ============ 选择操作 ============
  
  setSelectedNodes: (ids) => {
    set({ selectedNodes: ids })
  },

  setSelectedEdges: (ids) => {
    set({ selectedEdges: ids })
  },

  clearSelection: () => {
    set((state) => ({
      nodes: state.nodes.map(n => ({ ...n, selected: false })),
      selectedNodes: [],
      selectedEdges: [],
    }))

    if (import.meta.env.DEV) {
      console.log('🔄 Selection cleared')
    }
  },

  selectAll: () => {
    const { nodes } = get()
    const allNodeIds = nodes.map((n) => n.id)
    
    // 更新节点的 selected 属性
    set({
      nodes: nodes.map((n) => ({ ...n, selected: true })),
      selectedNodes: allNodeIds,
    })

    if (import.meta.env.DEV) {
      console.log('✅ Select all:', allNodeIds.length, 'nodes')
    }
  },

  // ============ 视图操作 ============
  
  setViewport: (viewport) => {
    set({ viewport })
  },

  // ============ 剪贴板操作 ============

  copyNodes: (ids) => {
    if (ids.length === 0) {
      if (import.meta.env.DEV) {
        console.warn('⚠️ Cannot copy: no nodes selected')
      }
      return
    }

    const { nodes, edges } = get()
    const nodesToCopy = nodes.filter((n) => ids.includes(n.id))
    
    // 只复制两端节点都被选中的边
    const edgesToCopy = edges.filter(
      (e) => ids.includes(e.source) && ids.includes(e.target)
    )

    // 深拷贝并转换为绝对位置
    const nodesWithAbsolutePosition = nodesToCopy.map((node) => {
      // 如果节点在组内，需要计算其绝对位置
      let absoluteX = node.position.x
      let absoluteY = node.position.y
      
      if (node.parentNode) {
        const parentGroup = nodes.find((n) => n.id === node.parentNode)
        if (parentGroup) {
          absoluteX = parentGroup.position.x + node.position.x
          absoluteY = parentGroup.position.y + node.position.y
        }
      }
      
      return {
        ...JSON.parse(JSON.stringify(node)),
        position: { x: absoluteX, y: absoluteY },
        // 复制时就清除父子关系，避免粘贴时出现问题
        parentNode: undefined,
        extent: undefined,
      }
    })

    set({
      clipboard: {
        nodes: nodesWithAbsolutePosition,
        edges: JSON.parse(JSON.stringify(edgesToCopy)),
      },
    })

    if (import.meta.env.DEV) {
      console.log('📋 Copied to clipboard:', {
        nodes: nodesToCopy.length,
        edges: edgesToCopy.length,
        nodeIds: nodesToCopy.map(n => n.id),
      })
    }
  },

  cutNodes: (ids) => {
    get().copyNodes(ids)
    get().removeNodes(ids)
    
    if (import.meta.env.DEV) {
      console.log('✂️ Cut nodes:', ids.length)
    }
  },

  pasteNodes: (position) => {
    const { clipboard } = get()
    if (!clipboard || clipboard.nodes.length === 0) {
      if (import.meta.env.DEV) {
        console.warn('⚠️ Cannot paste: clipboard is empty')
      }
      return
    }

    // 计算粘贴位置（如果提供了位置，使用它；否则偏移）
    const pasteOffset = position 
      ? { 
          x: position.x - clipboard.nodes[0].position.x,
          y: position.y - clipboard.nodes[0].position.y,
        }
      : { x: 50, y: 50 }

    // 创建 ID 映射（旧 ID -> 新 ID）
    const timestamp = Date.now()
    const idMap = new Map<string, string>()
    clipboard.nodes.forEach((node, index) => {
      const newId = `${node.id}-paste-${timestamp}-${index}`
      idMap.set(node.id, newId)
    })

    // 创建新节点（取消旧节点选中，选中新节点）
    const newNodes = clipboard.nodes.map((node) => ({
      ...node,
      id: idMap.get(node.id)!,
      position: {
        x: node.position.x + pasteOffset.x,
        y: node.position.y + pasteOffset.y,
      },
      selected: true, // 粘贴后选中
      // 清除父子关系相关的属性，粘贴的节点应该是独立的顶层节点
      parentNode: undefined,
      extent: undefined,
    }))

    // 创建新边（使用新的节点 ID）
    const newEdges = clipboard.edges
      .filter((edge) => idMap.has(edge.source) && idMap.has(edge.target)) // 只复制两端都存在的边
      .map((edge, index) => ({
        ...edge,
        id: `${edge.id}-paste-${timestamp}-${index}`,
        source: idMap.get(edge.source)!,
        target: idMap.get(edge.target)!,
      }))

    // 更新状态：取消所有旧节点选中，添加新节点
    set((state) => ({
      nodes: [
        ...state.nodes.map(n => ({ ...n, selected: false })),
        ...newNodes
      ],
      edges: [...state.edges, ...newEdges],
      selectedNodes: newNodes.map((n) => n.id),
    }))

    // 延迟保存历史，确保状态更新完成
    setTimeout(() => {
      get().saveToHistory()
    }, 0)

    if (import.meta.env.DEV) {
      console.log('📋 Pasted from clipboard:', {
        nodes: newNodes.length,
        edges: newEdges.length,
        position: position || 'offset',
        newNodeIds: newNodes.map(n => n.id),
      })
    }
  },

  // ============ 历史记录操作 ============
  
  /**
   * 保存当前状态到历史记录（带防抖）
   */
  saveToHistory: () => {
    // 如果正在撤销/重做，不保存历史
    if (get().isUndoRedoing) {
      return
    }

    // 清除之前的定时器
    if (saveHistoryTimer) {
      clearTimeout(saveHistoryTimer)
    }

    // 设置防抖定时器
    saveHistoryTimer = setTimeout(() => {
      const state = get()
      
      // 创建当前状态的快照
      const currentState: GraphState = {
        nodes: JSON.parse(JSON.stringify(state.nodes)),
        edges: JSON.parse(JSON.stringify(state.edges)),
        viewport: { ...state.viewport },
        timestamp: Date.now(),
      }

      // 如果与上一个状态相同，不保存
      if (state.history.length > 0) {
        const lastState = state.history[state.currentHistoryIndex]
        if (lastState && isStateSame(currentState, lastState)) {
          return
        }
      }

      // 限制历史记录大小
      let newHistory = [
        ...state.history.slice(0, state.currentHistoryIndex + 1),
        currentState,
      ]

      // 如果超过最大历史记录数，移除最旧的
      if (newHistory.length > HISTORY_CONFIG.MAX_HISTORY_SIZE) {
        newHistory = newHistory.slice(1)
        set({
          history: newHistory,
          currentHistoryIndex: newHistory.length - 1,
        })
      } else {
        set({
          history: newHistory,
          currentHistoryIndex: state.currentHistoryIndex + 1,
        })
      }

      // 开发者日志
      if (import.meta.env.DEV) {
        console.log('📝 History saved:', {
          index: get().currentHistoryIndex,
          total: get().history.length,
          nodes: currentState.nodes.length,
          edges: currentState.edges.length,
        })
      }
    }, HISTORY_CONFIG.DEBOUNCE_DELAY)
  },

  /**
   * 撤销到上一个状态
   */
  undo: () => {
    const state = get()
    if (!state.canUndo()) {
      console.warn('⚠️ Cannot undo: no history available')
      return
    }

    const previousState = state.history[state.currentHistoryIndex - 1]
    
    // 标记正在撤销，避免触发 saveToHistory
    set({ isUndoRedoing: true })

    set({
      nodes: deepCloneGraphState(previousState).nodes,
      edges: deepCloneGraphState(previousState).edges,
      viewport: previousState.viewport,
      currentHistoryIndex: state.currentHistoryIndex - 1,
    })

    // 恢复标记
    setTimeout(() => set({ isUndoRedoing: false }), 0)

    // 开发者日志
    if (import.meta.env.DEV) {
      console.log('↶ Undo:', {
        index: get().currentHistoryIndex,
        total: get().history.length,
      })
    }
  },

  /**
   * 重做到下一个状态
   */
  redo: () => {
    const state = get()
    if (!state.canRedo()) {
      console.warn('⚠️ Cannot redo: no future history available')
      return
    }

    const nextState = state.history[state.currentHistoryIndex + 1]
    
    // 标记正在重做，避免触发 saveToHistory
    set({ isUndoRedoing: true })

    set({
      nodes: deepCloneGraphState(nextState).nodes,
      edges: deepCloneGraphState(nextState).edges,
      viewport: nextState.viewport,
      currentHistoryIndex: state.currentHistoryIndex + 1,
    })

    // 恢复标记
    setTimeout(() => set({ isUndoRedoing: false }), 0)

    // 开发者日志
    if (import.meta.env.DEV) {
      console.log('↷ Redo:', {
        index: get().currentHistoryIndex,
        total: get().history.length,
      })
    }
  },

  /**
   * 是否可以撤销
   */
  canUndo: () => {
    const state = get()
    return state.currentHistoryIndex > 0
  },

  /**
   * 是否可以重做
   */
  canRedo: () => {
    const state = get()
    return state.currentHistoryIndex < state.history.length - 1
  },

  /**
   * 获取历史记录信息（用于调试）
   */
  getHistoryInfo: () => {
    const state = get()
    return {
      current: state.currentHistoryIndex,
      total: state.history.length,
      canUndo: state.canUndo(),
      canRedo: state.canRedo(),
    }
  },

  // ============ 节点历史记录操作 ============

  /**
   * 添加节点历史记录
   */
  addNodeHistory: (nodeId, entry) => {
    set((state) => ({
      nodes: state.nodes.map((node) => {
        if (node.id !== nodeId) return node

        const history = (node.data?.history || []) as import('@/shared/types').NodeHistoryEntry[]
        const newEntry: import('@/shared/types').NodeHistoryEntry = {
          ...entry,
          id: `history-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          timestamp: Date.now(),
        }

        // 限制历史记录数量（最多保留 20 条）
        const updatedHistory = [...history, newEntry].slice(-20)

        return {
          ...node,
          data: {
            ...node.data,
            history: updatedHistory,
          },
        }
      }),
    }))
  },

  /**
   * 获取节点历史记录
   */
  getNodeHistory: (nodeId) => {
    const node = get().nodes.find((n) => n.id === nodeId)
    return (node?.data?.history || []) as import('@/shared/types').NodeHistoryEntry[]
  },

  /**
   * 恢复到某个历史状态
   */
  restoreNodeHistory: (nodeId, historyId) => {
    set((state) => ({
      nodes: state.nodes.map((node) => {
        if (node.id !== nodeId) return node

        const history = (node.data?.history || []) as import('@/shared/types').NodeHistoryEntry[]
        const historyEntry = history.find((h) => h.id === historyId)

        if (!historyEntry) return node

        // 恢复输出数据到 attributes
        return {
          ...node,
          data: {
            ...node.data,
            attributes: {
              ...node.data?.attributes,
              ...historyEntry.outputs,
            },
          },
        }
      }),
    }))
    get().saveToHistory()
  },

  /**
   * 清空节点历史记录
   */
  clearNodeHistory: (nodeId) => {
    set((state) => ({
      nodes: state.nodes.map((node) => {
        if (node.id !== nodeId) return node

        return {
          ...node,
          data: {
            ...node.data,
            history: [],
          },
        }
      }),
    }))
  },

  // ============ 工具方法 ============

  /**
   * 清空画布和历史记录
   */
  clear: () => {
    if (saveHistoryTimer) {
      clearTimeout(saveHistoryTimer)
      saveHistoryTimer = null
    }
    set({
      nodes: [],
      edges: [],
      selectedNodes: [],
      selectedEdges: [],
      history: [],
      currentHistoryIndex: -1,
      isUndoRedoing: false,
    })

    if (import.meta.env.DEV) {
      console.log('🗑️ Graph cleared')
    }
  },
}))

