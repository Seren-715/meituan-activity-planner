// ===== 欢迎页组件 =====

type Props = {
  inputText: string
  setInputText: (v: string) => void
  chatLoading: boolean
  suggestedReplies: string[]
  onSubmit: (value?: string) => void
}

export function WelcomeScreen({ inputText, setInputText, chatLoading, suggestedReplies, onSubmit }: Props) {
  return (
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
            placeholder="说说你想怎么安排，比如：今天下午想和老婆孩子出去玩几个小时..."
            rows={2}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault()
                onSubmit()
              }
            }}
          />
          <button
            className="welcome-submit"
            onClick={() => onSubmit()}
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
              onClick={() => onSubmit(option)}
            >
              {option}
            </button>
          ))}
        </div>
      </div>
    </section>
  )
}
