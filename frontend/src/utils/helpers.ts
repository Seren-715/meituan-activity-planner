// ===== 工具函数 =====

import type { SlotState, ChatSlotsApi } from '../types'

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8002'
export const AMAP_JS_KEY = import.meta.env.VITE_AMAP_JS_KEY || ''

export const INITIAL_SLOTS: SlotState = {
  goal: '',
  scene: '',
  groupSize: '',
  city: '',
  timeWindow: '',
  durationHours: '',
  distancePreference: '',
  travelMode: 'driving',
  childAgeHint: '',
  diningPreference: '',
  pacePreference: '',
  specialNeeds: '',
}

export function sceneLabel(scene: string): string {
  if (scene === 'family') return '家庭场景'
  if (scene === 'friends') return '朋友场景'
  return '泛化场景'
}

export function travelLabel(mode: string): string {
  return mode === 'walking' ? '步行' : '驾车 / 打车'
}

export function formatScore(score: number): string {
  return score.toFixed(1)
}

// 后端 /chat 返回的是 snake_case，这里统一映射成前端使用的 camelCase 状态。
export function normalizeChatSlots(slots: ChatSlotsApi): SlotState {
  return {
    goal: slots.goal || '',
    scene: slots.scene || '',
    groupSize: slots.group_size || '',
    city: slots.city || '',
    timeWindow: slots.time_window || '',
    durationHours: slots.duration_hours || '',
    distancePreference: slots.distance_preference || '',
    travelMode: slots.travel_mode === 'walking' ? 'walking' : 'driving',
    childAgeHint: slots.child_age_hint || '',
    diningPreference: slots.dining_preference || '',
    pacePreference: slots.pace_preference || '',
    specialNeeds: slots.special_needs || '',
  }
}

// 只有真正的空输入才在前端拦截，纯符号等交给后端做引导回复。
export function isClearlyInvalidInput(value: string): boolean {
  return value.trim().length === 0
}

// buildPlanText removed - goal now built directly as structured GoalFromChat
export function buildPlanTextFromSlots(slots: SlotState): string {
  // direct goal 缺失时，前端用这段文本兜底，保证旧规划接口仍可工作。
  const parts = [
    slots.goal,
    slots.city ? `在${slots.city}` : '',
    slots.timeWindow,
    slots.durationHours ? `${slots.durationHours}个小时` : '',
    slots.distancePreference,
    slots.childAgeHint ? `孩子${slots.childAgeHint}` : '',
    slots.diningPreference,
    slots.pacePreference,
    slots.specialNeeds,
  ]
  return parts.filter(Boolean).join('，')
}

// 被主动取消的旧请求不应该再覆盖当前界面状态。
export function isAbortError(error: unknown): boolean {
  return error instanceof Error && error.name === 'AbortError'
}

export function renderMessage(content: string): string {
  let html = content
    // Escape HTML first
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    // Bold
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    // Italic
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    // Headers
    .replace(/^### (.+)$/gm, '<h4 class="msg-h4">$1</h4>')
    .replace(/^## (.+)$/gm, '<h3 class="msg-h3">$1</h3>')
    // Horizontal rules
    .replace(/^---$/gm, '<hr class="msg-hr" />')
    // Numbered emoji items (1️⃣ 2️⃣ 3️⃣) -> cards
    .replace(/^(\d️⃣) \*\*(.+?)\*\*/gm, '<div class="msg-card"><div class="msg-card-num">$1</div><div class="msg-card-body"><strong>$2</strong>')
    // Bullet items within cards
    .replace(/^- \*\*(.+?)\*\*:\s*(.+)$/gm, '<div class="msg-card-field"><strong>$1</strong><span>$2</span></div>')
    // Close card at next empty line or next number
    .replace(/<div class="msg-card-num">/g, (match, offset) => {
      return offset === 0 ? match : '</div>' + match
    })
    // Line breaks
    .replace(/\n\n/g, '<br/><br/>')
    .replace(/\n/g, '<br/>')

  // Ensure all cards are closed
  if ((html.match(/<div class="msg-card">/g) || []).length > (html.match(/<\/div>/g) || []).length - (html.match(/<div /g) || []).length + 1) {
    html += '</div>'
  }

  return html
}
