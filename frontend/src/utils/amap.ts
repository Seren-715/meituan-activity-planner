// ===== 高德地图加载 =====

import type { AMapMap } from '../types'

let amapPromise: Promise<void> | null = null

export function loadAmapScript(key: string): Promise<void> {
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

export function initMap(
  container: HTMLElement,
  center: [number, number],
  mapStops: Array<{ lng: number; lat: number; title: string }>,
): AMapMap | null {
  const AMap = window.AMap
  if (!AMap) return null

  const mapInstance = new AMap.Map(container, { zoom: 12, center })

  const markers = mapStops.map(
    (stop, index) =>
      new AMap.Marker({
        position: [stop.lng, stop.lat],
        title: stop.title,
        label: { content: `${index + 1}. ${stop.title}`, direction: 'top' },
      }),
  )
  mapInstance.add(markers)
  mapInstance.addControl(new AMap.Scale())
  mapInstance.addControl(new AMap.ToolBar())

  const polyline = new AMap.Polyline({
    path: mapStops.map((stop) => [stop.lng, stop.lat] as [number, number]),
    strokeColor: '#ffbe00',
    strokeWeight: 5,
    strokeOpacity: 0.9,
  })
  mapInstance.add(polyline)
  mapInstance.setFitView([...markers, polyline])

  return mapInstance
}
