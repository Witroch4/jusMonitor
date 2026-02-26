'use client'

import { useEffect, useRef } from 'react'

interface UseRealtimeOptions {
  onUpdate: () => void
  interval?: number // in milliseconds
  enabled?: boolean
}

/**
 * Hook for real-time dashboard updates
 * Uses polling for now, can be upgraded to WebSocket/SSE later
 */
export function useDashboardRealtime({
  onUpdate,
  interval = 60000, // 1 minute default
  enabled = true,
}: UseRealtimeOptions) {
  const intervalRef = useRef<NodeJS.Timeout | null>(null)

  useEffect(() => {
    if (!enabled) {
      return
    }

    // Set up polling
    intervalRef.current = setInterval(() => {
      onUpdate()
    }, interval)

    // Cleanup
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [onUpdate, interval, enabled])

  // Manual trigger
  const trigger = () => {
    onUpdate()
  }

  return { trigger }
}
