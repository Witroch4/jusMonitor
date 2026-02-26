'use client'

import { useState, useEffect, useRef, useCallback } from 'react'

interface UseWebSocketOptions {
  url?: string
  reconnectInterval?: number
  maxReconnectAttempts?: number
  onOpen?: () => void
  onClose?: () => void
  onError?: (error: Event) => void
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const {
    url = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws',
    reconnectInterval = 3000,
    maxReconnectAttempts = 10,
    onOpen,
    onClose,
    onError,
  } = options

  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState<string | null>(null)
  const [reconnectAttempts, setReconnectAttempts] = useState(0)
  
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const shouldReconnectRef = useRef(true)

  const connect = useCallback(() => {
    try {
      // Get JWT token from cookie or localStorage
      const token = document.cookie
        .split('; ')
        .find((row) => row.startsWith('token='))
        ?.split('=')[1]

      if (!token) {
        console.warn('No authentication token found for WebSocket connection')
        return
      }

      // Create WebSocket connection with token as query parameter
      const wsUrl = `${url}?token=${encodeURIComponent(token)}`
      const ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        console.log('WebSocket connected')
        setIsConnected(true)
        setReconnectAttempts(0)
        onOpen?.()
      }

      ws.onmessage = (event) => {
        setLastMessage(event.data)
      }

      ws.onclose = () => {
        console.log('WebSocket disconnected')
        setIsConnected(false)
        wsRef.current = null
        onClose?.()

        // Attempt to reconnect if enabled and under max attempts
        if (
          shouldReconnectRef.current &&
          reconnectAttempts < maxReconnectAttempts
        ) {
          console.log(
            `Attempting to reconnect... (${reconnectAttempts + 1}/${maxReconnectAttempts})`
          )
          reconnectTimeoutRef.current = setTimeout(() => {
            setReconnectAttempts((prev) => prev + 1)
            connect()
          }, reconnectInterval)
        }
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        onError?.(error)
      }

      wsRef.current = ws
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error)
    }
  }, [url, reconnectInterval, maxReconnectAttempts, reconnectAttempts, onOpen, onClose, onError])

  const disconnect = useCallback(() => {
    shouldReconnectRef.current = false
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
  }, [])

  const sendMessage = useCallback((message: string | object) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      const data = typeof message === 'string' ? message : JSON.stringify(message)
      wsRef.current.send(data)
    } else {
      console.warn('WebSocket is not connected. Message not sent:', message)
    }
  }, [])

  // Connect on mount
  useEffect(() => {
    shouldReconnectRef.current = true
    connect()

    // Cleanup on unmount
    return () => {
      disconnect()
    }
  }, [connect, disconnect])

  // Handle page visibility changes (reconnect when tab becomes visible)
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible' && !isConnected) {
        console.log('Page became visible, attempting to reconnect...')
        connect()
      }
    }

    document.addEventListener('visibilitychange', handleVisibilityChange)
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [isConnected, connect])

  return {
    isConnected,
    lastMessage,
    sendMessage,
    disconnect,
    reconnect: connect,
  }
}
