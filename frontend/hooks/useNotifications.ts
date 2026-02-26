'use client'

import { useState, useEffect, useCallback } from 'react'
import { useWebSocket } from './useWebSocket'
import type { Notification } from '@/components/notifications/NotificationCenter'

export function useNotifications() {
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [unreadCount, setUnreadCount] = useState(0)
  
  const { lastMessage, sendMessage, isConnected } = useWebSocket()

  // Load initial notifications from API
  useEffect(() => {
    const loadNotifications = async () => {
      try {
        const response = await fetch('/api/v1/notifications', {
          credentials: 'include',
        })
        if (response.ok) {
          const data = await response.json()
          setNotifications(data.notifications || [])
          setUnreadCount(data.unread_count || 0)
        }
      } catch (error) {
        console.error('Failed to load notifications:', error)
      }
    }

    loadNotifications()
  }, [])

  // Handle incoming WebSocket messages
  useEffect(() => {
    if (lastMessage) {
      try {
        const data = JSON.parse(lastMessage)
        
        if (data.type === 'notification') {
          const newNotification: Notification = {
            id: data.id,
            type: data.notification_type,
            title: data.title,
            message: data.message,
            read: false,
            createdAt: data.created_at || new Date().toISOString(),
            metadata: data.metadata,
          }
          
          setNotifications((prev) => [newNotification, ...prev])
          setUnreadCount((prev) => prev + 1)
          
          // Show browser notification if permission granted
          if ('Notification' in window && Notification.permission === 'granted') {
            new Notification(newNotification.title, {
              body: newNotification.message,
              icon: '/favicon.ico',
              tag: newNotification.id,
            })
          }
        }
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error)
      }
    }
  }, [lastMessage])

  // Request browser notification permission
  useEffect(() => {
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission()
    }
  }, [])

  const markAsRead = useCallback(async (notificationId: string) => {
    try {
      const response = await fetch(`/api/v1/notifications/${notificationId}/read`, {
        method: 'POST',
        credentials: 'include',
      })
      
      if (response.ok) {
        setNotifications((prev) =>
          prev.map((n) =>
            n.id === notificationId ? { ...n, read: true } : n
          )
        )
        setUnreadCount((prev) => Math.max(0, prev - 1))
      }
    } catch (error) {
      console.error('Failed to mark notification as read:', error)
    }
  }, [])

  const markAllAsRead = useCallback(async () => {
    try {
      const response = await fetch('/api/v1/notifications/read-all', {
        method: 'POST',
        credentials: 'include',
      })
      
      if (response.ok) {
        setNotifications((prev) =>
          prev.map((n) => ({ ...n, read: true }))
        )
        setUnreadCount(0)
      }
    } catch (error) {
      console.error('Failed to mark all notifications as read:', error)
    }
  }, [])

  return {
    notifications,
    unreadCount,
    markAsRead,
    markAllAsRead,
    isConnected,
  }
}
