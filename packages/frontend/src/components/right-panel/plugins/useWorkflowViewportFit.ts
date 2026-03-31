import { useCallback, useEffect, useRef } from 'react'
import type { ReactFlowInstance } from 'reactflow'

type UseWorkflowViewportFitArgs = {
  nodeCount: number
  edgeCount: number
  displaySessionId: string | null
  activeViewState: string
  lastUpdated: number | null | undefined
}

export function useWorkflowViewportFit({
  nodeCount,
  edgeCount,
  displaySessionId,
  activeViewState,
  lastUpdated,
}: UseWorkflowViewportFitArgs) {
  const reactFlowRef = useRef<ReactFlowInstance | null>(null)
  const graphHostRef = useRef<HTMLDivElement | null>(null)

  const fitWorkflowView = useCallback(
    (duration = 260) => {
      if (!reactFlowRef.current || nodeCount === 0) return
      window.requestAnimationFrame(() => {
        reactFlowRef.current?.fitView({
          padding: 0.22,
          minZoom: 0.55,
          maxZoom: 1.08,
          duration,
        })
      })
    },
    [nodeCount],
  )

  useEffect(() => {
    if (nodeCount === 0) return
    fitWorkflowView(nodeCount > 12 ? 340 : 260)
  }, [fitWorkflowView, nodeCount, edgeCount, displaySessionId, activeViewState, lastUpdated])

  useEffect(() => {
    const host = graphHostRef.current
    if (!host || nodeCount === 0) return
    let timeoutId: number | null = null
    const observer = new ResizeObserver(() => {
      if (timeoutId) {
        window.clearTimeout(timeoutId)
      }
      timeoutId = window.setTimeout(() => fitWorkflowView(180), 90)
    })
    observer.observe(host)
    return () => {
      observer.disconnect()
      if (timeoutId) {
        window.clearTimeout(timeoutId)
      }
    }
  }, [fitWorkflowView, nodeCount])

  const handleGraphInit = useCallback(
    (instance: ReactFlowInstance) => {
      reactFlowRef.current = instance
      fitWorkflowView(0)
    },
    [fitWorkflowView],
  )

  return {
    fitWorkflowView,
    graphHostRef,
    handleGraphInit,
  }
}
