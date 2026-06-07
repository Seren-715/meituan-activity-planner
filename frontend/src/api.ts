// ===== API 请求层 =====

import type { ChatMessage, GoalFromChat, PlanningResult, ExecutionResult, SlotState } from './types'
import { API_BASE_URL } from './utils/helpers'

export async function postChatStream(
  messages: ChatMessage[],
  signal: AbortSignal,
): Promise<Response> {
  const res = await fetch(`${API_BASE_URL}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages }),
    signal,
  })
  if (!res.ok) throw new Error('服务器或网络异常，请稍后重试。')
  if (!res.body) throw new Error('服务器或网络异常，请稍后重试。')
  return res
}

export async function postPlanDirect(
  goal: GoalFromChat,
  signal: AbortSignal,
): Promise<PlanningResult> {
  const res = await fetch(`${API_BASE_URL}/plan/direct`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(goal),
    signal,
  })
  if (!res.ok) throw new Error('规划请求失败')
  return res.json()
}

export async function postPlan(
  userText: string,
  slots: SlotState,
  signal: AbortSignal,
): Promise<PlanningResult> {
  const res = await fetch(`${API_BASE_URL}/plan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_text: userText,
      city: slots.city,
      origin_name: '当前位置',
      origin_lat: null,
      origin_lng: null,
      travel_mode: slots.travelMode,
    }),
    signal,
  })
  if (!res.ok) throw new Error('规划请求失败')
  return res.json()
}

export async function postExecute(
  payload: PlanningResult,
  signal: AbortSignal,
): Promise<ExecutionResult> {
  const res = await fetch(`${API_BASE_URL}/execute`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal,
  })
  if (!res.ok) throw new Error('执行请求失败')
  return res.json()
}
