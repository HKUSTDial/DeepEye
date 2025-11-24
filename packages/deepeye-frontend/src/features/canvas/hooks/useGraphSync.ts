/**
 * 图状态同步管理 Hook
 * 统一管理 ReactFlow 和 Store 之间的双向同步
 * 
 * 设计原则：
 * 1. 明确的同步方向：ReactFlow → Store 或 Store → ReactFlow
 * 2. 使用标记防止循环同步
 * 3. 集中管理所有同步逻辑
 */

import { useEffect, useRef } from 'react'
import { Node, Edge } from 'reactflow'

interface UseGraphSyncProps {
  // ReactFlow 状态
  nodes: Node[]
  edges: Edge[]
  setNodes: (nodes: Node[]) => void
  setEdges: (edges: Edge[]) => void
  
  // Store 状态
  storeNodes: Node[]
  storeEdges: Edge[]
  setStoreNodes: (nodes: Node[] | ((nodes: Node[]) => Node[])) => void
  setStoreEdges: (edges: Edge[] | ((edges: Edge[]) => Edge[])) => void
  
  // 控制标记
  isUndoRedoing: boolean
}

/**
 * 统一的图状态同步管理
 */
export function useGraphSync({
  nodes,
  edges,
  setNodes,
  setEdges,
  storeNodes,
  storeEdges,
  setStoreNodes,
  setStoreEdges,
  isUndoRedoing,
}: UseGraphSyncProps) {
  // ============ 同步标记 ============
  const syncLock = useRef({
    isSyncingToStore: false,          // 正在同步到 Store
    isSyncingNodesFromStore: false,   // 正在同步 nodes 从 Store
    isSyncingEdgesFromStore: false,   // 正在同步 edges 从 Store
  })

  // ============ Store → ReactFlow 同步 ============
  
  /**
   * 同步 nodes：Store → ReactFlow
   */
  useEffect(() => {
    // 如果正在同步到 Store，跳过（避免循环）
    if (syncLock.current.isSyncingToStore) {
      return
    }

    const nodesChanged = JSON.stringify(nodes) !== JSON.stringify(storeNodes)
    
    if (nodesChanged) {
      if (import.meta.env.DEV) {
        console.log('📥 [Sync] Store → ReactFlow (nodes)', {
          storeNodes: storeNodes.length,
          localNodes: nodes.length,
        })
      }

      // 设置节点同步标记
      syncLock.current.isSyncingNodesFromStore = true

      // 同步节点
      setNodes(storeNodes)

      // 释放标记
      Promise.resolve().then(() => {
        syncLock.current.isSyncingNodesFromStore = false
      })
    }
  }, [storeNodes]) // 只监听 storeNodes

  /**
   * 同步 edges：Store → ReactFlow
   */
  useEffect(() => {
    // 如果正在同步到 Store，跳过
    if (syncLock.current.isSyncingToStore) {
      return
    }

    const edgesChanged = JSON.stringify(edges) !== JSON.stringify(storeEdges)
    
    if (edgesChanged) {
      if (import.meta.env.DEV) {
        console.log('📥 [Sync] Store → ReactFlow (edges)', {
          storeEdges: storeEdges.length,
          localEdges: edges.length,
        })
      }

      // 设置边同步标记
      syncLock.current.isSyncingEdgesFromStore = true

      // 同步边
      setEdges(storeEdges)

      // 释放标记
      Promise.resolve().then(() => {
        syncLock.current.isSyncingEdgesFromStore = false
      })
    }
  }, [storeEdges]) // 只监听 storeEdges

  // ============ ReactFlow → Store 同步 ============
  
  /**
   * 同步 nodes：ReactFlow → Store
   */
  useEffect(() => {
    // 如果正在从 Store 同步 nodes，跳过
    if (syncLock.current.isSyncingNodesFromStore) {
      return
    }

    // 撤销/重做时不同步（因为 Store 已经是正确的状态）
    if (isUndoRedoing) {
      return
    }

    // 初始化时跳过
    if (nodes.length === 0 && edges.length === 0 && storeNodes.length === 0) {
      return
    }

    const nodesChanged = JSON.stringify(nodes) !== JSON.stringify(storeNodes)
    
    if (nodesChanged) {

      // 设置同步标记
      syncLock.current.isSyncingToStore = true

      // 同步到 Store（会触发历史记录保存）
      setStoreNodes(nodes)

      // 释放标记
      Promise.resolve().then(() => {
        syncLock.current.isSyncingToStore = false
      })
    }
  }, [nodes, isUndoRedoing, storeNodes, setStoreNodes])

  /**
   * 同步 edges：ReactFlow → Store
   */
  useEffect(() => {
    // 如果正在从 Store 同步 edges，跳过
    if (syncLock.current.isSyncingEdgesFromStore) {
      return
    }

    if (isUndoRedoing) {
      return
    }

    if (nodes.length === 0 && edges.length === 0 && storeEdges.length === 0) {
      return
    }

    const edgesChanged = JSON.stringify(edges) !== JSON.stringify(storeEdges)
    
    if (edgesChanged) {

      syncLock.current.isSyncingToStore = true
      setStoreEdges(edges)

      Promise.resolve().then(() => {
        syncLock.current.isSyncingToStore = false
      })
    }
  }, [edges, isUndoRedoing, storeEdges, setStoreEdges])

  // ============ 调试信息 ============
  
  useEffect(() => {
    if (import.meta.env.DEV) {
      // 可以通过 window 访问同步状态（便于调试）
      (window as any).__GRAPH_SYNC_STATUS__ = {
        reactFlowNodes: nodes.length,
        storeNodes: storeNodes.length,
        reactFlowEdges: edges.length,
        storeEdges: storeEdges.length,
        isUndoRedoing,
        syncLock: { ...syncLock.current },
      }
    }
  }, [nodes.length, storeNodes.length, edges.length, storeEdges.length, isUndoRedoing])

  // 返回同步状态（可选，用于显示加载状态等）
  return {
    isSyncing: syncLock.current.isSyncingToStore || 
               syncLock.current.isSyncingNodesFromStore || 
               syncLock.current.isSyncingEdgesFromStore,
  }
}

