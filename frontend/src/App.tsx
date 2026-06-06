import { useEffect, useMemo, useRef, useState } from 'react'
import './App.css'

type Stop = {
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

type MapStop = Stop & { lat: number; lng: number }

type ScoreBreakdownItem = {
  label: string
  score: number
  detail: string
}

type Itinerary = {
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

type Goal = {
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

type PlanningResult = {
  goal: Goal
  itinerary: Itinerary
  alternatives: Itinerary[]
  actions: Array<{ action_type: string; target: string; payload?: Record<string, string> }>
  data_mode: string
  recommendation_reason: string
}

type ExecutionResult = {
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


type PlanningPhase = 'idle' | 'understanding' | 'screening' | 'comparing' | 'ready'

type ChatMessage = {
  role: 'assistant' | 'user'
  content: string
}

type SlotState = {
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

type ChatSlotsApi = {
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

type AMapMap = {
  add: (items: unknown) => void
  addControl: (control: unknown) => void
  setFitView: (items: unknown[]) => void
  destroy: () => void
}

type AMapNamespace = {
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

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
const AMAP_JS_KEY = import.meta.env.VITE_AMAP_JS_KEY || ''

const INITIAL_SLOTS: SlotState = {
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

function sceneLabel(scene: string): string {
  if (scene === 'family') return '家庭场景'
  if (scene === 'friends') return '朋友场景'
  return '泛化场景'
}

function travelLabel(mode: string): string {
  return mode === 'walking' ? '步行' : '驾车 / 打车'
}

function formatScore(score: number): string {
  return score.toFixed(1)
}

// 后端 /chat 返回的是 snake_case，这里统一映射成前端使用的 camelCase 状态。
function normalizeChatSlots(slots: ChatSlotsApi): SlotState {
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

// 纯标点或纯符号这类内容不发给后端，避免页面里出现无意义的往返对话。
function isClearlyInvalidInput(value: string): boolean {
  const normalized = value.trim()
  if (!normalized) return true
  const semantic = normalized.replace(/[\s\p{P}\p{S}_]+/gu, '')
  return semantic.length === 0
}

function buildPlanText(slots: SlotState): string {
  const parts: string[] = []
  const timeText = slots.timeWindow || '下午'
  const sceneText =
    slots.scene === 'family'
      ? '和家人出去玩'
      : slots.scene === 'friends'
        ? '和朋友出去玩和吃饭'
        : '出去放松一下'
  parts.push(`今天${timeText}想${sceneText}`)
  if (slots.groupSize) parts.push(`一共${slots.groupSize}个人`)
  if (slots.durationHours) parts.push(`计划安排${slots.durationHours}小时左右`)
  if (slots.distancePreference === '近场') parts.push('别离家太远')
  if (slots.distancePreference === '可稍远') parts.push('稍远一点也可以')
  if (slots.childAgeHint) parts.push(`孩子大概${slots.childAgeHint}`)
  if (slots.diningPreference && slots.diningPreference !== '无特别要求') parts.push(`吃饭偏好是${slots.diningPreference}`)
  if (slots.pacePreference) parts.push(`整体节奏希望${slots.pacePreference}`)
  if (slots.specialNeeds && slots.specialNeeds !== '没有') parts.push(`还需要注意${slots.specialNeeds}`)
  if (slots.goal) parts.push(`补充目标：${slots.goal}`)
  return parts.join('，')
}

function App() {
  const [slots, setSlots] = useState<SlotState>(INITIAL_SLOTS)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputText, setInputText] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const [loading, setLoading] = useState(false)
  const [, setPhase] = useState<PlanningPhase>('idle')
  const [planningResult, setPlanningResult] = useState<PlanningResult | null>(null)
  const [executing, setExecuting] = useState(false)
  const [executionResult, setExecutionResult] = useState<ExecutionResult | null>(null)
  const [error, setError] = useState('')
  const [mapStatus, setMapStatus] = useState('等待规划结果')
  const [readyToPlan, setReadyToPlan] = useState(false)
  const [planText, setPlanText] = useState('')
  const [suggestedReplies, setSuggestedReplies] = useState<string[]>([
    '今天下午想和老婆孩子出去玩几个小时，别离家太远',
    '晚上想和朋友聚个会，先玩再吃饭',
    '周末想一个人随便逛逛放松一下',
  ])
  const [originName] = useState('当前位置')
  const [originLat] = useState<number | null>(null)
  const [originLng] = useState<number | null>(null)
  const chatEndRef = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<HTMLDivElement | null>(null)

  const hasStartedConversation = messages.length > 0
  const showResultsLayout = Boolean(planningResult)
  const mapStops = useMemo(
    () =>
      planningResult?.itinerary.stops.filter(
        (stop): stop is MapStop => stop.lat !== null && stop.lng !== null,
      ) ?? [],
    [planningResult],
  )
  const bestAlternative = planningResult?.alternatives[0] ?? null

  const demandChips = useMemo(() => {
    if (!planningResult) return []
    const goal = planningResult.goal
    const chips = [
      sceneLabel(goal.scene),
      `${goal.group_size} 人`,
      `${goal.time_window}${goal.duration_hours} 小时`,
      goal.distance_preference,
      travelLabel(goal.travel_mode),
      ...(goal.city ? [goal.city] : []),
      ...(goal.child_age_hint ? [goal.child_age_hint] : []),
      ...goal.preferences,
      ...goal.dining_preferences,
      ...goal.special_needs,
    ]
    return Array.from(new Set(chips.filter(Boolean)))
  }, [planningResult])

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleUserReply = async (rawValue?: string) => {
    const value = (rawValue ?? inputText).trim()
    if (!value || chatLoading) return
    if (isClearlyInvalidInput(value)) {
      setError('这句我没太看懂，你可以直接说和谁出门、想玩多久，或者你现在在哪个城市。')
      return
    }

    const nextMessages = [...messages, { role: 'user' as const, content: value }]
    setMessages(nextMessages)
    setInputText('')
    setChatLoading(true)
    setError('')

    try {
      const res = await fetch(`${API_BASE_URL}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: nextMessages }),
      })
      if (!res.ok) {
        throw new Error('对话请求失败')
      }

      // Add placeholder for streaming response
      setMessages((prev) => [...prev, { role: 'assistant' as const, content: '' }])

      // Read SSE stream
      const reader = res.body!.getReader()
      const decoder = new TextDecoder()
      let buf = ''
      let acc = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buf += decoder.decode(value, { stream: true })
        const lines = buf.split(String.fromCharCode(10))
        buf = lines.pop() || ''
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const raw = line.slice(6)
            if (raw === '[DONE]') continue
            const ev = JSON.parse(raw)
            if (ev.type === 'token') {
              acc += ev.text
              setMessages((prev) => {
                const cp = [...prev]
                const last = cp[cp.length - 1]
                if (last?.role === 'assistant') cp[cp.length - 1] = { ...last, content: acc }
                return cp
              })
            } else if (ev.type === 'done' && ev.slots) {
              setSlots(normalizeChatSlots(ev.slots))
              setReadyToPlan(ev.ready_to_plan)
              setSuggestedReplies(ev.suggested_replies || [])
              setPlanText(ev.plan_text || '')
            }
          }
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '对话失败')
    }
    finally {
      setChatLoading(false)
    }
  }

  const handleResetConversation = () => {
    setSlots(INITIAL_SLOTS)
    setMessages([])
    setInputText('')
    setPlanningResult(null)
    setExecutionResult(null)
    setError('')
    setReadyToPlan(false)
    setPlanText('')
    setSuggestedReplies([
      '今天下午想和老婆孩子出去玩几个小时，别离家太远',
      '晚上想和朋友聚个会，先玩再吃饭',
      '周末想一个人随便逛逛放松一下',
    ])
    setPhase('idle')
  }

  const handlePlan = async () => {
    if (!readyToPlan) return
    const userText = planText || buildPlanText(slots)
    setLoading(true)
    setError('')
    setPlanningResult(null)
    setExecutionResult(null)
    setPhase('understanding')

    const timers = [
      window.setTimeout(() => {
        setPhase('screening')
      }, 650),
      window.setTimeout(() => {
        setPhase('comparing')
      }, 1300),
    ]

    try {
      const res = await fetch(`${API_BASE_URL}/plan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_text: userText,
          city: slots.city,
          origin_name: originName,
          origin_lat: originLat,
          origin_lng: originLng,
          travel_mode: slots.travelMode,
        }),
      })
      if (!res.ok) {
        throw new Error('规划请求失败')
      }
      const data: PlanningResult = await res.json()
      setPlanningResult(data)
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: '我先给你整理出了一版，你看看右边这套安排合不合适。',
        },
      ])
      setPhase('ready')
      if (!AMAP_JS_KEY) {
        setMapStatus(data.data_mode === 'real' ? '已拿到真实地点，地图底图缺省时用文字路线兜底' : '当前为 Mock 降级模式，先保留文字路线说明')
      } else {
        setMapStatus(data.data_mode === 'real' ? '已获取真实地点与路线，可用于比赛演示' : '当前展示为 Mock 候选，但完整闭环仍可演示')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '规划失败')
      setPhase('idle')
    } finally {
      timers.forEach((timer) => window.clearTimeout(timer))
      setLoading(false)
    }
  }

  const handleExecute = async () => {
    if (!planningResult) return
    setExecuting(true)
    setError('')
    try {
      const res = await fetch(`${API_BASE_URL}/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(planningResult),
      })
      if (!res.ok) {
        throw new Error('执行请求失败')
      }
      const data: ExecutionResult = await res.json()
      setExecutionResult(data)
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: '行，那我继续往下帮你推进，结果我会同步放在右边。',
        },
      ])
    } catch (err) {
      setError(err instanceof Error ? err.message : '执行失败')
    } finally {
      setExecuting(false)
    }
  }

  useEffect(() => {
    if (!mapRef.current || mapStops.length === 0) return
    if (!AMAP_JS_KEY) return

    const itinerary = planningResult?.itinerary
    if (!itinerary) return

    let mapInstance: AMapMap | null = null
    let disposed = false

    loadAmapScript(AMAP_JS_KEY)
      .then(() => {
        const AMap = window.AMap
        if (disposed || !AMap || !mapRef.current) return
        const centerLng = itinerary.map_center_lng
        const centerLat = itinerary.map_center_lat
        const center: [number, number] =
          centerLng !== null && centerLat !== null ? [centerLng, centerLat] : [mapStops[0].lng, mapStops[0].lat]

        mapInstance = new AMap.Map(mapRef.current, {
          zoom: 12,
          center,
        })

        const markers = mapStops.map((stop, index) => new AMap.Marker({
          position: [stop.lng, stop.lat],
          title: stop.title,
          label: { content: `${index + 1}. ${stop.title}`, direction: 'top' },
        }))
        mapInstance.add(markers)
        mapInstance.addControl(new AMap.Scale())
        mapInstance.addControl(new AMap.ToolBar())

        const polyline = new AMap.Polyline({
          path: mapStops.map((stop) => [stop.lng, stop.lat]),
          strokeColor: '#ffbe00',
          strokeWeight: 5,
          strokeOpacity: 0.9,
        })
        mapInstance.add(polyline)
        mapInstance.setFitView([...markers, polyline])
        setMapStatus('地图已加载，可看到真实地点与路线连线')
      })
      .catch(() => {
        setMapStatus('地图脚本加载失败，已回退为文字路线与卡片说明')
      })

    return () => {
      disposed = true
      if (mapInstance) {
        mapInstance.destroy()
      }
    }
  }, [mapStops, planningResult])

  return (
    <div className="page-shell">
      {!hasStartedConversation && !planningResult && (
        <section className="welcome-shell">
          <div className="welcome-card">
            <div className="welcome-copy">
              <h1>你好呀，今天想做点什么？</h1>
              <p>你可以直接告诉我想和谁出门、想玩多久，或者想吃点什么。</p>
            </div>

            <div className="welcome-input-wrap">
              <textarea
                value={inputText}
                onChange={(event) => setInputText(event.target.value)}
                placeholder="比如：今天下午想和老婆孩子出去玩几个小时，别离家太远"
                rows={2}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault()
                    handleUserReply()
                  }
                }}
              />
              <button
                className="welcome-submit"
                onClick={() => handleUserReply()}
                disabled={!inputText.trim() || chatLoading}
                aria-label="发送"
                title="发送"
              >
                {chatLoading ? '…' : '>'}
              </button>
            </div>

            <div className="welcome-suggestions">
              {suggestedReplies.map((option) => (
                <button
                  key={`welcome-${option}`}
                  className="quick-reply"
                  onClick={() => handleUserReply(option)}
                >
                  {option}
                </button>
              ))}
            </div>
          </div>
        </section>
      )}

      {(hasStartedConversation || planningResult) && (
      <div className={showResultsLayout ? 'chat-layout' : 'chat-stage'}>
        <section className="panel chat-panel">
          <div className="chat-panel-header">
            <div>
              <h2>说说你想怎么安排这次出行</h2>
              <p>我会边聊边帮你理清需求。</p>
            </div>
            <button className="secondary-button" onClick={handleResetConversation}>重新开始</button>
          </div>

          {error && !showResultsLayout && <div className="panel error-panel">{error}</div>}

          <div className="chat-messages">
            {messages.map((message, index) => (
              <div key={`${message.role}-${index}`} className={`chat-bubble-row ${message.role}`}>
                {message.role === 'assistant' && <div className="chat-avatar">AI</div>}
                <div className={`chat-bubble ${message.role}`}>{message.content}</div>
              </div>
            ))}
            <div ref={chatEndRef} />
          </div>

          {!readyToPlan && (
            <>
              {suggestedReplies.length > 0 && (
                <div className="quick-reply-row">
                  {suggestedReplies.map((option) => (
                    <button
                      key={option}
                      className="quick-reply"
                      onClick={() => handleUserReply(option)}
                    >
                      {option}
                    </button>
                  ))}
                </div>
              )}
              <div className="chat-input-row">
                <textarea
                  value={inputText}
                  onChange={(event) => setInputText(event.target.value)}
                  placeholder="继续告诉我你的想法，我会边听边帮你整理"
                  rows={2}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' && !event.shiftKey) {
                      event.preventDefault()
                      handleUserReply()
                    }
                  }}
                />
                <button className="primary-button" onClick={() => handleUserReply()} disabled={!inputText.trim() || chatLoading}>
                  {chatLoading ? '思考中...' : '发送'}
                </button>
              </div>
            </>
          )}

          {readyToPlan && (
            <div className="ready-action-card">
              <strong>我已经抓到重点了</strong>
              <p>如果你觉得差不多，我现在就开始给你安排。</p>
              <button className="primary-button" onClick={handlePlan} disabled={loading}>
                {loading ? '规划中...' : '开始生成方案'}
              </button>
            </div>
          )}
        </section>

        {showResultsLayout && (
        <section className="result-column">
          {error && <div className="panel error-panel">{error}</div>}

          {!planningResult && (
            <section className="panel empty-state-panel">
              <h2>方案会显示在这里</h2>
              <p>先把需求聊清楚，我再给你安排路线和吃喝玩方案。</p>
            </section>
          )}

          {planningResult && (
            <div className="content-grid">
              <section className="main-column">
                <section className="panel recommendation-panel">
                  <div className="recommendation-header">
                    <div>
                      <p className="section-kicker">推荐主方案</p>
                      <h2>{planningResult.itinerary.title}</h2>
                      <p>{planningResult.recommendation_reason || planningResult.itinerary.recommendation_reason}</p>
                    </div>
                    <div className="score-card">
                      <span>综合评分</span>
                      <strong>{formatScore(planningResult.itinerary.score)}</strong>
                    </div>
                  </div>

                  <div className="chip-row">
                    {demandChips.map((chip) => (
                      <span className="goal-chip" key={chip}>{chip}</span>
                    ))}
                  </div>

                  <div className="meta-grid">
                    <MetaBlock label="城市 / 出发点" value={`${planningResult.goal.city || '未指定'} / ${planningResult.goal.origin_name || '未指定'}`} />
                    <MetaBlock label="时间与时长" value={`${planningResult.goal.time_window} / ${planningResult.goal.duration_hours} 小时`} />
                    <MetaBlock label="距离与节奏" value={`${planningResult.goal.distance_preference} / ${planningResult.goal.pace_preference}`} />
                    <MetaBlock label="路线通勤" value={`${planningResult.itinerary.total_travel_minutes} 分钟`} />
                  </div>

                  <div className="section-block">
                    <h3>为什么推荐这条</h3>
                    <p className="reason-paragraph">{planningResult.itinerary.recommendation_reason}</p>
                    <ul className="plain-list">
                      {planningResult.itinerary.rationale.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}
                    </ul>
                  </div>
                </section>

                <section className="panel">
                  <div className="panel-heading">
                    <div>
                      <h2>评分依据</h2>
                      <p>系统不是直接拼接地点，而是按统一标准比较主备方案。</p>
                    </div>
                  </div>
                  <div className="score-breakdown-grid">
                    {planningResult.itinerary.score_breakdown.map((item) => (
                      <div className="score-breakdown-card" key={item.label}>
                        <div className="score-breakdown-head">
                          <strong>{item.label}</strong>
                          <span>{formatScore(item.score)}</span>
                        </div>
                        <p>{item.detail}</p>
                      </div>
                    ))}
                  </div>
                </section>

                <section className="panel">
                  <div className="panel-heading">
                    <div>
                      <h2>行程时间线</h2>
                      <p>主活动、餐饮、补充活动按顺路关系串起来，避免只给孤立推荐。</p>
                    </div>
                  </div>

                  <div className="timeline">
                    {planningResult.itinerary.stops.map((stop, index) => (
                      <div className="timeline-item" key={`${stop.title}-${index}`}>
                        <div className="timeline-dot">{index + 1}</div>
                        <div className="timeline-card">
                          <div className="timeline-head">
                            <strong>{stop.title}</strong>
                            <span>{stop.start_time}</span>
                          </div>
                          <div className="timeline-sub">
                            {stop.location} · {stop.address || '地址待补充'} · 停留 {stop.duration_minutes} 分钟
                          </div>
                          <div className="timeline-route">
                            从上一站出发约 {stop.travel_minutes_from_prev} 分钟 / {stop.distance_from_prev_meters || 0} 米
                          </div>
                          <p>{stop.note}</p>
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="section-block">
                    <h3>路线摘要</h3>
                    <ul className="plain-list">
                      {planningResult.itinerary.route_summary.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}
                    </ul>
                  </div>

                  {planningResult.itinerary.alerts.length > 0 && (
                    <div className="section-block">
                      <h3>执行提醒</h3>
                      <ul className="plain-list">
                        {planningResult.itinerary.alerts.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}
                      </ul>
                    </div>
                  )}
                </section>

                <section className="panel">
                  <div className="panel-heading">
                    <div>
                      <h2>主备方案对比</h2>
                      <p>评委可以直接看到为什么主方案比备选更值得推荐。</p>
                    </div>
                  </div>
                  <div className="alternative-grid">
                    <PlanCompareCard title="主方案" badge="推荐" itinerary={planningResult.itinerary} isPrimary />
                    {planningResult.alternatives.map((item, index) => (
                      <PlanCompareCard key={`${item.title}-${index}`} title={`备选 ${index + 1}`} badge="备选" itinerary={item} />
                    ))}
                  </div>
                  {bestAlternative && (
                    <div className="comparison-summary">
                      主方案比备选 1 高 <strong>{formatScore(planningResult.itinerary.score - bestAlternative.score)}</strong> 分，
                      更适合作为优先执行版本。
                    </div>
                  )}
                </section>
              </section>

              <aside className="side-column">
                <section className="panel map-panel">
                  <div className="panel-heading compact">
                    <div>
                      <h2>地图与本地感</h2>
                      <p>{mapStatus}</p>
                    </div>
                  </div>
                  <div className="map-canvas" ref={mapRef}>
                    {!AMAP_JS_KEY && <div className="map-placeholder">未提供 `VITE_AMAP_JS_KEY`，当前使用文字路线与真实地点卡片兜底。</div>}
                  </div>
                </section>

                <section className="panel">
                  <h2>将会执行什么</h2>
                  <div className="action-preview-list">
                    {planningResult.actions.map((action, index) => (
                      <div className="action-preview-item" key={`${action.target}-${index}`}>
                        <strong>{action.action_type}</strong>
                        <p>{action.target}</p>
                      </div>
                    ))}
                  </div>
                  <div className="action-row vertical">
                    <div className="helper-copy">确认后会依次推进预约、排号、下单或配送，失败时显示补偿动作。</div>
                    <button className="confirm-button" onClick={handleExecute} disabled={executing}>
                      {executing ? '执行中...' : '确认并一键执行'}
                    </button>
                  </div>
                </section>

                <section className="panel">
                  <h2>执行状态</h2>
                  {!executionResult && <p className="muted-copy">尚未执行。确认后将展示关键动作、失败原因与补偿路径。</p>}
                  {executionResult && (
                    <div className="execution-list">
                      {executionResult.execution_results.map((result, index) => (
                        <div className={`execution-item ${result.status}`} key={`${result.target}-${index}`}>
                          <div className="execution-head">
                            <strong>{result.details.stage || result.action_type}</strong>
                            <span>{result.status}</span>
                          </div>
                          <p>{result.target}</p>
                          <p className="muted-copy">{result.message}</p>
                          {result.reference_id && <p className="muted-copy">凭证：{result.reference_id}</p>}
                          {result.recovery_hint && <p className="hint-copy">补偿建议：{result.recovery_hint}</p>}
                        </div>
                      ))}
                    </div>
                  )}
                </section>

                <section className="panel">
                  <h2>可分享结果</h2>
                  <p className="share-copy">{executionResult?.share_text || '执行完成后，这里会生成可直接发给家人或朋友的摘要。'}</p>
                </section>
              </aside>
            </div>
          )}
        </section>
        )}
      </div>
      )}
    </div>
  )
}

function MetaBlock({ label, value }: { label: string; value: string }) {
  return (
    <div className="meta-block">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function PlanCompareCard({
  title,
  badge,
  itinerary,
  isPrimary = false,
}: {
  title: string
  badge: string
  itinerary: Itinerary
  isPrimary?: boolean
}) {
  return (
    <div className={`alternative-card ${isPrimary ? 'alternative-card-primary' : ''}`}>
      <div className="alternative-head">
        <div>
          <span className="plan-badge">{badge}</span>
          <strong>{title}</strong>
        </div>
        <span className="plan-score">{formatScore(itinerary.score)}</span>
      </div>
      <p className="alternative-route">{itinerary.stops.map((stop) => stop.title).join(' → ')}</p>
      <p className="muted-copy">{itinerary.recommendation_reason}</p>
      <div className="mini-score-list">
        {itinerary.score_breakdown.slice(0, 3).map((item) => (
          <div className="mini-score-item" key={item.label}>
            <span>{item.label}</span>
            <strong>{formatScore(item.score)}</strong>
          </div>
        ))}
      </div>
      <span className="plan-footer">{itinerary.total_minutes} 分钟 · 通勤 {itinerary.total_travel_minutes} 分钟</span>
    </div>
  )
}

let amapPromise: Promise<void> | null = null

function loadAmapScript(key: string): Promise<void> {
  if (window.AMap) return Promise.resolve()
  if (amapPromise) return amapPromise
  amapPromise = new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.src = `https://webapi.amap.com/maps?v=2.0&key=${key}&plugin=AMap.Scale,AMap.ToolBar`
    script.async = true
    script.onload = () => resolve()
    script.onerror = () => {
      amapPromise = null
      script.remove()
      reject(new Error('高德地图脚本加载失败'))
    }
    document.body.appendChild(script)
  })
  return amapPromise
}

export default App
