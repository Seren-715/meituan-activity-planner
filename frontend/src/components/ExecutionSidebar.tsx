// ===== 执行侧边栏组件 =====

import type { ExecutionResult, PlanningResult } from '../types'

type Props = {
  mapStatus: string
  mapRef: { current: HTMLDivElement | null }
  amapJsKey: string
  selectedExecutionPayload: PlanningResult | null
  executing: boolean
  executionResult: ExecutionResult | null
  onExecute: () => void
}

export function ExecutionSidebar({
  mapStatus,
  mapRef,
  amapJsKey,
  selectedExecutionPayload,
  executing,
  executionResult,
  onExecute,
}: Props) {
  return (
    <aside className="side-column">
      <section className="panel map-panel">
        <div className="panel-heading compact">
          <div>
            <h2>地图与本地感</h2>
            <p>{mapStatus}</p>
          </div>
        </div>
        <div className="map-canvas" ref={mapRef}>
          {!amapJsKey && <div className="map-placeholder">未提供 `VITE_AMAP_JS_KEY`，当前使用文字路线与真实地点卡片兜底。</div>}
        </div>
      </section>

      <section className="panel">
        <h2>将会执行什么</h2>
        <div className="action-preview-list">
          {(selectedExecutionPayload?.actions ?? []).map((action, index) => (
            <div className="action-preview-item" key={`${action.target}-${index}`}>
              <strong>{action.action_type}</strong>
              <p>{action.target}</p>
            </div>
          ))}
        </div>
        <div className="action-row vertical">
          <div className="helper-copy">确认后会依次推进预约、排号、下单或配送，失败时显示补偿动作。</div>
          <button className="confirm-button" onClick={onExecute} disabled={executing || !selectedExecutionPayload || selectedExecutionPayload.actions.length === 0}>
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
                  <span className={`status-badge ${result.status}`}>{result.status}</span>
                </div>
                {result.details.stage_type === 'compensation' && (
                  <p className="hint-copy">这是自动触发的补偿动作，用来接住上一步失败。</p>
                )}
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
  )
}
