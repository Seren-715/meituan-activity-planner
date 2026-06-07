// ===== 规划 Hook =====

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { ChatMessage, GoalFromChat, PlanningResult, PlanningPhase, PlanOption, SlotState } from '../types'
import { buildPlanTextFromSlots, isAbortError } from '../utils/helpers'
import { postPlanDirect, postPlan } from '../api'

export function usePlanning(opts: {
  goalFromChat: GoalFromChat | null
  planText: string
  slots: SlotState
  readyToPlan: boolean
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>
}) {
  const { goalFromChat, planText, slots, readyToPlan, setMessages } = opts

  const [loading, setLoading] = useState(false)
  const [planError, setPlanError] = useState('')
  const [planningResult, setPlanningResult] = useState<PlanningResult | null>(null)
  const [phase, setPhase] = useState<PlanningPhase>('idle')
  const [selectedPlanIndex, setSelectedPlanIndex] = useState(0)
  const [mapStatus, setMapStatus] = useState('等待规划结果')

  const planAbortRef = useRef<AbortController | null>(null)
  const planRequestIdRef = useRef(0)
  const autoPlanKeyRef = useRef('')

  const planOptions = useMemo<PlanOption[]>(() => {
    if (!planningResult) return []
    return [
      {
        key: 'primary',
        label: '方案 1',
        badge: '推荐',
        itinerary: planningResult.itinerary,
        actions: planningResult.actions,
        isPrimary: true,
      },
      ...planningResult.alternatives.map((item, index) => ({
        key: `alt-${index}`,
        label: `方案 ${index + 2}`,
        badge: '可选',
        itinerary: item,
        actions: planningResult.alternative_actions[index] ?? [],
        isPrimary: false,
      })),
    ]
  }, [planningResult])

  const selectedPlan = planOptions[selectedPlanIndex] ?? null

  const handlePlan = useCallback(async () => {
    if (!readyToPlan) return
    const userText = planText || buildPlanTextFromSlots(slots)
    const requestId = planRequestIdRef.current + 1
    planRequestIdRef.current = requestId
    planAbortRef.current?.abort()
    const controller = new AbortController()
    planAbortRef.current = controller
    setLoading(true)
    setPlanError('')
    setPlanningResult(null)
    setPhase('understanding')

    const timers = [
      window.setTimeout(() => setPhase('screening'), 650),
      window.setTimeout(() => setPhase('comparing'), 1300),
    ]

    try {
      let data: PlanningResult
      if (goalFromChat) {
        try {
          data = await postPlanDirect(goalFromChat, controller.signal)
        } catch {
          data = await postPlan(userText, slots, controller.signal)
        }
      } else {
        data = await postPlan(userText, slots, controller.signal)
      }
      if (planRequestIdRef.current !== requestId) return
      setPlanningResult(data)
      setSelectedPlanIndex(0)
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: '我先整理了几套方案卡片，你先挑一张更喜欢的，我再把完整安排展开给你看。',
        },
      ])
      setPhase('ready')
      setMapStatus(
        data.data_mode === 'real'
          ? '已获取真实地点与路线，可用于比赛演示'
          : '当前展示为 Mock 候选，但完整闭环仍可演示',
      )
    } catch (err) {
      if (!isAbortError(err) && planRequestIdRef.current === requestId) {
        setPlanError(err instanceof Error ? err.message : '规划失败')
        setPhase('idle')
      }
    } finally {
      timers.forEach((timer) => window.clearTimeout(timer))
      if (planRequestIdRef.current === requestId) {
        setLoading(false)
        planAbortRef.current = null
      }
    }
  }, [goalFromChat, planText, readyToPlan, setMessages, slots])

  // Auto-trigger plan when ready_to_plan and goal is available
  useEffect(() => {
    if (!readyToPlan || planningResult || loading) return
    const nextKey = JSON.stringify(goalFromChat || { planText, slots })
    if (autoPlanKeyRef.current === nextKey) return
    autoPlanKeyRef.current = nextKey
    handlePlan()
  }, [readyToPlan, goalFromChat, planText, planningResult, loading, slots, handlePlan])

  const handleSelectPlan = useCallback((index: number) => {
    setSelectedPlanIndex(index)
  }, [])

  const reset = useCallback(() => {
    planAbortRef.current?.abort()
    setPlanError('')
    setPlanningResult(null)
    setLoading(false)
    setPhase('idle')
    setSelectedPlanIndex(0)
    setMapStatus('等待规划结果')
    autoPlanKeyRef.current = ''
  }, [])

  return {
    loading,
    planError, setPlanError,
    planningResult, setPlanningResult,
    phase,
    selectedPlanIndex,
    planOptions,
    selectedPlan,
    mapStatus,
    handlePlan,
    handleSelectPlan,
    reset,
  }
}
