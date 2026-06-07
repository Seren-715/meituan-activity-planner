import { useEffect, useMemo, useRef } from 'react'
import './App.css'

import type { MapStop } from './types'
import { AMAP_JS_KEY } from './utils/helpers'
import { loadAmapScript, initMap } from './utils/amap'
import { useChat } from './hooks/useChat'
import { usePlanning } from './hooks/usePlanning'
import { useExecution } from './hooks/useExecution'
import { WelcomeScreen } from './components/WelcomeScreen'
import { ChatPanel } from './components/ChatPanel'
import { ResultColumn } from './components/ResultColumn'

function App() {
  const chat = useChat()
  const planning = usePlanning({
    goalFromChat: chat.goalFromChat,
    planText: chat.planText,
    slots: chat.slots,
    readyToPlan: chat.readyToPlan,
    setMessages: chat.setMessages,
  })
  const execution = useExecution({
    planningResult: planning.planningResult,
    selectedPlan: planning.selectedPlan,
    planOptions: planning.planOptions,
    selectedPlanIndex: planning.selectedPlanIndex,
    setMessages: chat.setMessages,
  })

  const handleResetConversation = () => {
    chat.reset()
    planning.reset()
    execution.reset()
  }

  const hasStartedConversation = chat.messages.length > 0
  const showResultsLayout = Boolean(planning.planningResult)

  const comparisonPeer = useMemo(
    () => planning.planOptions.find((_, index) => index !== planning.selectedPlanIndex) ?? null,
    [planning.planOptions, planning.selectedPlanIndex],
  )

  const stageError = !showResultsLayout ? chat.chatError || planning.planError : chat.chatError
  const resultError = planning.planError || execution.executeError

  const mapStops = useMemo(
    () =>
      planning.selectedPlan?.itinerary.stops.filter(
        (stop): stop is MapStop => stop.lat !== null && stop.lng !== null,
      ) ?? [],
    [planning.selectedPlan],
  )

  const mapRef = useRef<HTMLDivElement | null>(null)

  // 地图渲染
  useEffect(() => {
    if (!mapRef.current || mapStops.length === 0) return
    if (!AMAP_JS_KEY) return

    const itinerary = planning.selectedPlan?.itinerary
    if (!itinerary) return

    let mapInstance: ReturnType<typeof initMap> = null
    let disposed = false

    loadAmapScript(AMAP_JS_KEY)
      .then(() => {
        if (disposed || !window.AMap || !mapRef.current) return
        const centerLng = itinerary.map_center_lng
        const centerLat = itinerary.map_center_lat
        const center: [number, number] =
          centerLng !== null && centerLat !== null ? [centerLng, centerLat] : [mapStops[0].lng, mapStops[0].lat]
        mapInstance = initMap(mapRef.current, center, mapStops)
      })
      .catch(() => {
        // map script load failed, text fallback already shown
      })

    return () => {
      disposed = true
      if (mapInstance) mapInstance.destroy()
    }
  }, [mapStops, planning.selectedPlan])

  return (
    <div className="page-shell">
      {!hasStartedConversation && !planning.planningResult && (
        <WelcomeScreen
          inputText={chat.inputText}
          setInputText={chat.setInputText}
          chatLoading={chat.chatLoading}
          suggestedReplies={chat.suggestedReplies}
          onSubmit={chat.sendMessage}
        />
      )}

      {(hasStartedConversation || planning.planningResult) && (
        <div className={showResultsLayout ? 'chat-layout' : 'chat-stage'}>
          <ChatPanel
            messages={chat.messages}
            chatError={stageError}
            chatLoading={chat.chatLoading}
            readyToPlan={chat.readyToPlan}
            loading={planning.loading}
            inputText={chat.inputText}
            setInputText={chat.setInputText}
            suggestedReplies={chat.suggestedReplies}
            onSubmit={chat.sendMessage}
            onReset={handleResetConversation}
            showResultsLayout={showResultsLayout}
          />

          {showResultsLayout && (
            <ResultColumn
              resultError={resultError}
              planningResult={planning.planningResult}
              planOptions={planning.planOptions}
              selectedPlan={planning.selectedPlan}
              selectedPlanIndex={planning.selectedPlanIndex}
              comparisonPeer={comparisonPeer}
              onSelectPlan={planning.handleSelectPlan}
              mapStatus={planning.mapStatus}
              mapRef={mapRef}
              amapJsKey={AMAP_JS_KEY}
              selectedExecutionPayload={execution.selectedExecutionPayload}
              executing={execution.executing}
              executionResult={execution.executionResult}
              onExecute={execution.handleExecute}
            />
          )}
        </div>
      )}
    </div>
  )
}

export default App
