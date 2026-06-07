// ===== 对话面板组件 =====

import { useEffect, useRef } from 'react'
import type { ChatMessage } from '../types'
import { renderMessage } from '../utils/helpers'

type Props = {
  messages: ChatMessage[]
  chatError: string
  chatLoading: boolean
  readyToPlan: boolean
  loading: boolean
  inputText: string
  setInputText: (v: string) => void
  suggestedReplies: string[]
  onSubmit: (value?: string) => void
  onReset: () => void
  showResultsLayout: boolean
}

export function ChatPanel({
  messages,
  chatError,
  chatLoading,
  readyToPlan,
  loading,
  inputText,
  setInputText,
  suggestedReplies,
  onSubmit,
  onReset,
  showResultsLayout,
}: Props) {
  const chatEndRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <section className="panel chat-panel">
      <div className="chat-panel-header">
        <div>
          <h2>说说你想怎么安排这次出行</h2>
          <p>我会边聊边帮你理清需求。</p>
        </div>
        <button className="secondary-button" onClick={onReset}>重新开始</button>
      </div>

      {!showResultsLayout && chatError && <div className="panel error-panel">{chatError}</div>}

      <div className="chat-messages">
        {messages.map((message, index) => (
          <div key={`${message.role}-${index}`} className={`chat-bubble-row ${message.role}`}>
            {message.role === 'assistant' && <div className="chat-avatar">AI</div>}
            {message.role === 'assistant' ? (
              <div className={`chat-bubble ${message.role}`} dangerouslySetInnerHTML={{ __html: renderMessage(message.content) }} />
            ) : (
              <div className={`chat-bubble ${message.role}`}>{message.content}</div>
            )}
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
                  onClick={() => onSubmit(option)}
                >
                  {option}
                </button>
              ))}
            </div>
          )}
          <div className="chat-input-row">
            <div className="chat-input-wrap">
              <textarea
                value={inputText}
                onChange={(event) => setInputText(event.target.value)}
                placeholder="继续跟我说说你的想法..."
                rows={2}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault()
                    onSubmit()
                  }
                }}
              />
              <button
                className="send-btn"
                onClick={() => onSubmit()}
                disabled={!inputText.trim() || chatLoading}
                aria-label="发送"
                title="发送 (Enter)"
              >
                {chatLoading ? (
                  <span className="loading-dots"><span></span><span></span><span></span></span>
                ) : (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="12" y1="19" x2="12" y2="5"/>
                    <polyline points="5 12 12 5 19 12"/>
                  </svg>
                )}
              </button>
            </div>
          </div>
        </>
      )}

      {readyToPlan && (
        <div className="ready-action-card">
          <strong>信息收集完毕</strong>
          <p>{loading ? (
            <div>
              <div className="skeleton skeleton-line medium" style={{marginBottom:8}} />
              <div className="skeleton skeleton-line short" style={{marginBottom:8}} />
              <div className="skeleton skeleton-block" />
            </div>
          ) : '方案已生成，请先从右侧卡片里选一个更想要的方向。'}</p>
        </div>
      )}
    </section>
  )
}
