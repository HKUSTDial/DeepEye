import { useEffect, useRef, useState } from 'react'

type HighlightState = {
  newNodeIds: Set<string>
  newEdgeIds: Set<string>
}

export function useTransientWorkflowHighlights(
  nodeIds: string[],
  edgeIds: string[],
  durationMs = 900,
): HighlightState {
  const [newNodeIds, setNewNodeIds] = useState<Set<string>>(new Set())
  const [newEdgeIds, setNewEdgeIds] = useState<Set<string>>(new Set())
  const prevNodeIdsRef = useRef<Set<string>>(new Set())
  const prevEdgeIdsRef = useRef<Set<string>>(new Set())
  const timeoutsRef = useRef<number[]>([])

  useEffect(() => {
    return () => {
      timeoutsRef.current.forEach((timeoutId) => window.clearTimeout(timeoutId))
      timeoutsRef.current = []
    }
  }, [])

  useEffect(() => {
    const currentNodeIds = new Set(nodeIds)
    const currentEdgeIds = new Set(edgeIds)

    const addedNodes = Array.from(currentNodeIds).filter((id) => !prevNodeIdsRef.current.has(id))
    const addedEdges = Array.from(currentEdgeIds).filter((id) => !prevEdgeIdsRef.current.has(id))

    if (addedNodes.length > 0) {
      setNewNodeIds((prev) => {
        const next = new Set(prev)
        addedNodes.forEach((id) => next.add(id))
        return next
      })
      addedNodes.forEach((id) => {
        const timeoutId = window.setTimeout(() => {
          setNewNodeIds((prev) => {
            const next = new Set(prev)
            next.delete(id)
            return next
          })
        }, durationMs)
        timeoutsRef.current.push(timeoutId)
      })
    }

    if (addedEdges.length > 0) {
      setNewEdgeIds((prev) => {
        const next = new Set(prev)
        addedEdges.forEach((id) => next.add(id))
        return next
      })
      addedEdges.forEach((id) => {
        const timeoutId = window.setTimeout(() => {
          setNewEdgeIds((prev) => {
            const next = new Set(prev)
            next.delete(id)
            return next
          })
        }, durationMs)
        timeoutsRef.current.push(timeoutId)
      })
    }

    prevNodeIdsRef.current = currentNodeIds
    prevEdgeIdsRef.current = currentEdgeIds
  }, [nodeIds, edgeIds, durationMs])

  return { newNodeIds, newEdgeIds }
}
