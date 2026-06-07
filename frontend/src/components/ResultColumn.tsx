// ===== 结果列组件 =====

import type { ExecutionResult, Goal, PlanningResult, PlanOption } from '../types'
import { sceneLabel, travelLabel, formatScore } from '../utils/helpers'
import { MetaBlock } from './MetaBlock'
import { PlanCompareCard } from './PlanCompareCard'
import { ExecutionSidebar } from './ExecutionSidebar'
import { useMemo } from 'react'

type Props = {
  resultError: string
  planningResult: PlanningResult | null
  planOptions: PlanOption[]
  selectedPlan: PlanOption | null
  selectedPlanIndex: number
  comparisonPeer: PlanOption | null
  onSelectPlan: (index: number) => void
  mapStatus: string
  mapRef: { current: HTMLDivElement | null }
  amapJsKey: string
  selectedExecutionPayload: PlanningResult | null
  executing: boolean
  executionResult: ExecutionResult | null
  onExecute: () => void
}

export function ResultColumn({
  resultError,
  planningResult,
  planOptions,
  selectedPlan,
  selectedPlanIndex,
  comparisonPeer,
  onSelectPlan,
  mapStatus,
  mapRef,
  amapJsKey,
  selectedExecutionPayload,
  executing,
  executionResult,
  onExecute,
}: Props) {
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

  return (
    <section className="result-column">
      {resultError && <div className="panel error-panel">{resultError}</div>}

      {!planningResult && (
        <section className="panel empty-state-panel">
          <h2>方案会显示在这里</h2>
          <p>先把需求聊清楚，我再给你安排路线和吃喝玩方案。</p>
        </section>
      )}

      {planningResult && (
        <div className="content-grid">
          <section className="main-column">
            <section className="panel">
              <div className="panel-heading">
                <div>
                  <h2>先选一个更想要的方案</h2>
                  <p>我先给你几张方案卡片，你选中之后，再展开完整路线和执行细节。</p>
                </div>
              </div>
              <div className="plan-option-grid">
                {planOptions.map((option, index) => (
                  <button
                    key={option.key}
                    type="button"
                    className={`plan-option-card ${selectedPlanIndex === index ? 'plan-option-card-active' : ''}`}
                    onClick={() => onSelectPlan(index)}
                  >
                    <div className="plan-option-head">
                      <div>
                        <span className="plan-badge">{option.badge}</span>
                        <strong>{option.label}</strong>
                      </div>
                      <span className="plan-score">{formatScore(option.itinerary.score)}</span>
                    </div>
                    <h3>{option.itinerary.title}</h3>
                    <p className="alternative-route">{option.itinerary.stops.map((stop) => stop.title).join(' → ')}</p>
                    <p className="muted-copy">{option.itinerary.recommendation_reason}</p>
                    <span className="plan-footer">{option.itinerary.total_minutes} 分钟 · 通勤 {option.itinerary.total_travel_minutes} 分钟</span>
                  </button>
                ))}
              </div>
            </section>

            {selectedPlan && (
              <>
                <section className="panel recommendation-panel">
                  <div className="recommendation-header">
                    <div>
                      <p className="section-kicker">{selectedPlan.isPrimary ? '当前选中方案' : '当前查看方案'}</p>
                      <h2>{selectedPlan.itinerary.title}</h2>
                      <p>{selectedPlan.itinerary.recommendation_reason}</p>
                    </div>
                    <div className="score-card">
                      <span>综合评分</span>
                      <strong>{formatScore(selectedPlan.itinerary.score)}</strong>
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
                    <MetaBlock label="路线通勤" value={`${selectedPlan.itinerary.total_travel_minutes} 分钟`} />
                  </div>

                  <div className="section-block">
                    <h3>为什么推荐这条</h3>
                    <p className="reason-paragraph">{selectedPlan.itinerary.recommendation_reason}</p>
                    <ul className="plain-list">
                      {selectedPlan.itinerary.rationale.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}
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
                    {selectedPlan.itinerary.score_breakdown.map((item) => (
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
                    {selectedPlan.itinerary.stops.map((stop, index) => (
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
                      {selectedPlan.itinerary.route_summary.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}
                    </ul>
                  </div>

                  {selectedPlan.itinerary.alerts.length > 0 && (
                    <div className="section-block">
                      <h3>执行提醒</h3>
                      <ul className="plain-list">
                        {selectedPlan.itinerary.alerts.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}
                      </ul>
                    </div>
                  )}
                </section>
              </>
            )}

            <section className="panel">
              <div className="panel-heading">
                <div>
                  <h2>主备方案对比</h2>
                  <p>评委可以直接看到为什么主方案比备选更值得推荐。</p>
                </div>
              </div>
              <div className="alternative-grid">
                {planOptions.map((option, index) => (
                  <PlanCompareCard
                    key={option.key}
                    title={option.label}
                    badge={option.badge}
                    itinerary={option.itinerary}
                    isPrimary={option.isPrimary}
                    isSelected={selectedPlanIndex === index}
                    onSelect={() => onSelectPlan(index)}
                  />
                ))}
              </div>
              {selectedPlan && comparisonPeer && (
                <div className="comparison-summary">
                  当前查看方案比 {comparisonPeer.label} 高 <strong>{formatScore(selectedPlan.itinerary.score - comparisonPeer.itinerary.score)}</strong> 分，
                  你可以直接按当前卡片继续执行。
                </div>
              )}
            </section>
          </section>

          <ExecutionSidebar
            mapStatus={mapStatus}
            mapRef={mapRef}
            amapJsKey={amapJsKey}
            selectedExecutionPayload={selectedExecutionPayload}
            executing={executing}
            executionResult={executionResult}
            onExecute={onExecute}
          />
        </div>
      )}
    </section>
  )
}
