// ===== 方案对比卡片 =====

import type { Itinerary } from '../types'
import { formatScore } from '../utils/helpers'

type Props = {
  title: string
  badge: string
  itinerary: Itinerary
  isPrimary?: boolean
  isSelected?: boolean
  onSelect?: () => void
}

export function PlanCompareCard({ title, badge, itinerary, isPrimary = false, isSelected = false, onSelect }: Props) {
  return (
    <button
      type="button"
      className={`alternative-card ${isPrimary ? 'alternative-card-primary' : ''} ${isSelected ? 'alternative-card-selected' : ''}`}
      onClick={onSelect}
    >
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
    </button>
  )
}
