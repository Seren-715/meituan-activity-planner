// ===== 共享类型定义 =====

export type Stop = {
  start_time: string
  duration_minutes: number
  title: string
  category: 'activity' | 'restaurant' | 'addon'
  location: string
  note: string
  address: string
  business_area: string
  source: string
  lat: number | null
  lng: number | null
  distance_from_prev_meters: number
  travel_minutes_from_prev: number
}

export type MapStop = Stop & { lat: number; lng: number }

export type ScoreBreakdownItem = {
  label: string
  score: number
  detail: string
}

export type Itinerary = {
  title: string
  total_minutes: number
  score: number
  total_travel_minutes: number
  route_summary: string[]
  map_center_lat: number | null
  map_center_lng: number | null
  stops: Stop[]
  rationale: string[]
  alerts: string[]
  fallback_options: string[]
  score_breakdown: ScoreBreakdownItem[]
  recommendation_reason: string
  planning_basis: string[]
}

export type Goal = {
  raw_text: string
  scene: string
  group_size: number
  duration_hours: number
  time_window: string
  distance_preference: string
  city: string
  origin_name: string
  travel_mode: string
  child_age_hint: string
  share_target: string
  pace_preference: string
  preferences: string[]
  dining_preferences: string[]
  special_needs: string[]
  constraints: Array<{ key: string; value: string }>
}

export type PlanningResult = {
  goal: Goal
  itinerary: Itinerary
  alternatives: Itinerary[]
  actions: ExecutionAction[]
  alternative_actions: ExecutionAction[][]
  data_mode: string
  recommendation_reason: string
}

export type ExecutionResult = {
  planning: PlanningResult
  execution_results: Array<{
    action_type: string
    target: string
    status: 'success' | 'failed' | 'skipped'
    message: string
    reference_id: string
    recovery_hint: string
    details: Record<string, string>
  }>
  share_text: string
  summary: string[]
}

export type PlanOption = {
  key: string
  label: string
  badge: string
  itinerary: Itinerary
  actions: ExecutionAction[]
  isPrimary: boolean
}

export type ExecutionAction = {
  action_type: 'reserve' | 'queue' | 'order' | 'delivery' | 'share'
  target: string
  payload?: Record<string, string>
}

export type PlanningPhase = 'idle' | 'understanding' | 'screening' | 'comparing' | 'ready'

export type ChatMessage = {
  role: 'assistant' | 'user'
  content: string
}

export type GoalFromChat = {
  raw_text: string
  scene: string
  group_size: number
  duration_hours: number
  time_window: string
  distance_preference: string
  city: string
  origin_name: string
  origin_lat: number | null
  origin_lng: number | null
  travel_mode: string
  child_age_hint: string
  share_target: string
  pace_preference: string
  preferences: string[]
  dining_preferences: string[]
  special_needs: string[]
  constraints: Array<{ key: string; value: string }>
}

export type SlotState = {
  goal: string
  scene: 'family' | 'friends' | 'generic' | ''
  groupSize: string
  city: string
  timeWindow: string
  durationHours: string
  distancePreference: string
  travelMode: 'driving' | 'walking'
  childAgeHint: string
  diningPreference: string
  pacePreference: string
  specialNeeds: string
}

export type ChatSlotsApi = {
  goal: string
  scene: SlotState['scene']
  group_size: string
  city: string
  time_window: string
  duration_hours: string
  distance_preference: string
  travel_mode: '' | SlotState['travelMode']
  child_age_hint: string
  dining_preference: string
  pace_preference: string
  special_needs: string
}

export type AMapMap = {
  add: (items: unknown) => void
  addControl: (control: unknown) => void
  setFitView: (items: unknown[]) => void
  destroy: () => void
}

export type AMapNamespace = {
  Map: new (container: HTMLElement, options: { zoom: number; center: [number, number] }) => AMapMap
  Marker: new (options: {
    position: [number, number]
    title: string
    label?: { content: string; direction: string }
  }) => unknown
  Polyline: new (options: {
    path: Array<[number, number]>
    strokeColor: string
    strokeWeight: number
    strokeOpacity: number
  }) => unknown
  Scale: new () => unknown
  ToolBar: new () => unknown
}

declare global {
  interface Window {
    AMap?: AMapNamespace
  }
}
