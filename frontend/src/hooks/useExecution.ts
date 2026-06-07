// ===== 执行 Hook =====

import { useCallback, useMemo, useRef, useState } from 'react'
import type { ChatMessage, ExecutionResult, PlanningResult, PlanOption } from '../types'
import { isAbortError } from '../utils/helpers'
import { postExecute } from '../api'

export function useExecution(opts: {
  planningResult: PlanningResult | null
  selectedPlan: PlanOption | null
  planOptions: PlanOption[]
  selectedPlanIndex: number
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>
}) {
  const { planningResult, selectedPlan, planOptions, selectedPlanIndex, setMessages } = opts

  const [executing, setExecuting] = useState(false)
  const [executionResult, setExecutionResult] = useState<ExecutionResult | null>(null)
  const [executeError, setExecuteError] = useState('')
  const executeAbortRef = useRef<AbortController | null>(null)
  const executeRequestIdRef = useRef(0)

  const selectedExecutionPayload = useMemo<PlanningResult | null>(() => {
    if (!planningResult || !selectedPlan) return null
    return {
      ...planningResult,
      itinerary: selectedPlan.itinerary,
      actions: selectedPlan.actions,
      alternatives: planOptions
        .filter((_, index) => index !== selectedPlanIndex)
        .map((option) => option.itinerary),
      recommendation_reason: selectedPlan.itinerary.recommendation_reason,
    }
  }, [planningResult, planOptions, selectedPlan, selectedPlanIndex])

  const handleExecute = useCallback(async () => {
    if (!selectedExecutionPayload) return
    const requestId = executeRequestIdRef.current + 1
    executeRequestIdRef.current = requestId
    executeAbortRef.current?.abort()
    const controller = new AbortController()
    executeAbortRef.current = controller
    setExecuting(true)
    setExecuteError('')
    try {
      const data = await postExecute(selectedExecutionPayload, controller.signal)
      if (executeRequestIdRef.current !== requestId) return
      setExecutionResult(data)
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: '行，那我继续往下帮你推进，结果我会同步放在右边。',
        },
      ])
    } catch (err) {
      if (!isAbortError(err) && executeRequestIdRef.current === requestId) {
        setExecuteError(err instanceof Error ? err.message : '执行失败')
      }
    } finally {
      if (executeRequestIdRef.current === requestId) {
        setExecuting(false)
        executeAbortRef.current = null
      }
    }
  }, [selectedExecutionPayload, setExecuteError, setMessages])

  const reset = useCallback(() => {
    executeAbortRef.current?.abort()
    setExecuting(false)
    setExecutionResult(null)
    setExecuteError('')
  }, [])

  return {
    executing,
    executionResult,
    executeError,
    selectedExecutionPayload,
    handleExecute,
    reset,
  }
}
