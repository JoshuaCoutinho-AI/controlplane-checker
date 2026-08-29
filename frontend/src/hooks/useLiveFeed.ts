import { useEffect, useRef, useState } from 'react'
import type { ScoredResponse } from '../types'

const API_BASE = '/api'
const WS_URL = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/api/ws`

export function useLiveFeed(maxRecords = 100) {
  const [records, setRecords] = useState<ScoredResponse[]>([])
  const [connected, setConnected] = useState(false)
  const retryDelay = useRef(1000)

  useEffect(() => {
    let cancelled = false

    // bootstrap with recent history over REST
    fetch(`${API_BASE}/history?limit=${maxRecords}`)
      .then((r) => r.json())
      .then((data: ScoredResponse[]) => {
        if (!cancelled) setRecords(data)
      })
      .catch(() => {
        /* backend may not be up yet; the WS loop below will still try */
      })

    let ws: WebSocket
    let closedByUs = false

    function connect() {
      ws = new WebSocket(WS_URL)

      ws.onopen = () => {
        setConnected(true)
        retryDelay.current = 1000
      }

      ws.onmessage = (event) => {
        try {
          const record: ScoredResponse = JSON.parse(event.data)
          setRecords((prev) => {
            const index = prev.findIndex((r) => r.id === record.id)
            if (index !== -1) {
              const updated = [...prev]
              updated[index] = record
              return updated
            }
            return [record, ...prev].slice(0, maxRecords)
          })
        } catch {
          /* ignore malformed frames */
        }
      }

      ws.onclose = () => {
        setConnected(false)
        if (!closedByUs) {
          setTimeout(connect, retryDelay.current)
          retryDelay.current = Math.min(retryDelay.current * 2, 15000)
        }
      }

      ws.onerror = () => {
        ws.close()
      }
    }

    connect()

    return () => {
      cancelled = true
      closedByUs = true
      ws?.close()
    }
  }, [maxRecords])

  return { records, connected }
}
