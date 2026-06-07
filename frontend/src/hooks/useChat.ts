// ===== 对话 Hook =====

import { useCallback, useRef, useState } from 'react'
import type { ChatMessage, GoalFromChat, SlotState } from '../types'
import { INITIAL_SLOTS, normalizeChatSlots, isClearlyInvalidInput, isAbortError } from '../utils/helpers'
import { postChatStream } from '../api'

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [slots, setSlots] = useState<SlotState>(INITIAL_SLOTS)
  const [inputText, setInputText] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const [chatError, setChatError] = useState('')
  const [readyToPlan, setReadyToPlan] = useState(false)
  const [planText, setPlanText] = useState('')
  const [goalFromChat, setGoalFromChat] = useState<GoalFromChat | null>(null)
  const [suggestedReplies, setSuggestedReplies] = useState<string[]>([
    '今天下午想和老婆孩子从公司附近出发玩几个小时，别太远',
    '晚上想和朋友聚个会，先玩再吃饭',
    '周末想一个人随便逛逛放松一下',
  ])

  const chatAbortRef = useRef<AbortController | null>(null)
  const chatRequestIdRef = useRef(0)

  const sendMessage = useCallback(async (rawValue?: string) => {
    const value = (rawValue ?? inputText).trim()
    if (!value || chatLoading) return
    if (isClearlyInvalidInput(value)) return

    const nextMessages = [...messages, { role: 'user' as const, content: value }]
    const requestId = chatRequestIdRef.current + 1
    chatRequestIdRef.current = requestId
    chatAbortRef.current?.abort()
    const controller = new AbortController()
    chatAbortRef.current = controller
    setMessages(nextMessages)
    setInputText('')
    setChatLoading(true)
    setChatError('')

    try {
      const res = await postChatStream(nextMessages, controller.signal)

      // Add placeholder for streaming response
      setMessages((prev) => [...prev, { role: 'assistant' as const, content: '' }])

      const reader = res.body!.getReader()
      const decoder = new TextDecoder()
      let buf = ''
      let acc = ''
      let gotTerminalEvent = false
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        if (chatRequestIdRef.current !== requestId) {
          await reader.cancel()
          return
        }
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
                if (chatRequestIdRef.current !== requestId) return prev
                const cp = [...prev]
                const last = cp[cp.length - 1]
                if (last?.role === 'assistant') cp[cp.length - 1] = { ...last, content: acc }
                return cp
              })
            } else if (ev.type === 'error') {
              gotTerminalEvent = true
              setMessages((prev) => {
                if (chatRequestIdRef.current !== requestId) return prev
                const cp = [...prev]
                const last = cp[cp.length - 1]
                if (last?.role === 'assistant' && !last.content) cp.pop()
                return cp
              })
              if (chatRequestIdRef.current === requestId) {
                setChatError(typeof ev.text === 'string' ? ev.text : '服务器或网络异常，请稍后重试。')
              }
            } else if (ev.type === 'done' && ev.slots) {
              gotTerminalEvent = true
              if (chatRequestIdRef.current !== requestId) continue
              setSlots(normalizeChatSlots(ev.slots))
              setReadyToPlan(ev.ready_to_plan)
              setSuggestedReplies(ev.suggested_replies || [])
              setPlanText(ev.plan_text || '')
              setGoalFromChat(ev.goal ?? null)
            }
          }
        }
      }
      if (!gotTerminalEvent) {
        setMessages((prev) => {
          const cp = [...prev]
          const last = cp[cp.length - 1]
          if (last?.role === 'assistant' && !last.content) cp.pop()
          return cp
        })
        throw new Error('服务器或网络异常，请稍后重试。')
      }
    } catch (err) {
      if (!isAbortError(err) && chatRequestIdRef.current === requestId) {
        setChatError(err instanceof Error ? err.message : '服务器或网络异常，请稍后重试。')
      }
    } finally {
      if (chatRequestIdRef.current === requestId) {
        setChatLoading(false)
        chatAbortRef.current = null
      }
    }
  }, [inputText, chatLoading, messages])

  const reset = useCallback(() => {
    chatAbortRef.current?.abort()
    setMessages([])
    setInputText('')
    setChatError('')
    setChatLoading(false)
    setReadyToPlan(false)
    setPlanText('')
    setGoalFromChat(null)
    setSuggestedReplies([
      '今天下午想和老婆孩子从公司附近出发玩几个小时，别太远',
      '晚上想和朋友聚个会，先玩再吃饭',
      '周末想一个人随便逛逛放松一下',
    ])
  }, [])

  return {
    messages, setMessages,
    slots, setSlots,
    inputText, setInputText,
    chatLoading,
    chatError, setChatError,
    readyToPlan, setReadyToPlan,
    planText, setPlanText,
    goalFromChat, setGoalFromChat,
    suggestedReplies,
    sendMessage,
    reset,
  }
}
