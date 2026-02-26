'use client'

import { useState, useEffect } from 'react'
import { Bell, Check, X } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { useNotifications } from '@/hooks/useNotifications'
import { formatDistanceToNow } from 'date-fns'
import { ptBR } from 'date-fns/locale'

export interface Notification {
  id: string
  type: 'urgent_movement' | 'qualified_lead' | 'briefing_available' | 'mention'
  title: string
  message: string
  read: boolean
  createdAt: string
  metadata?: {
    processId?: string
    leadId?: string
    clientId?: string
    userId?: string
  }
}

export function NotificationCenter() {
  const [isOpen, setIsOpen] = useState(false)
  const { notifications, unreadCount, markAsRead, markAllAsRead } = useNotifications()

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as HTMLElement
      if (!target.closest('[data-notification-center]')) {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('click', handleClickOutside)
      return () => document.removeEventListener('click', handleClickOutside)
    }
  }, [isOpen])

  const getNotificationIcon = (type: Notification['type']) => {
    switch (type) {
      case 'urgent_movement':
        return '⚠️'
      case 'qualified_lead':
        return '🎯'
      case 'briefing_available':
        return '📋'
      case 'mention':
        return '💬'
      default:
        return '🔔'
    }
  }

  const getNotificationColor = (type: Notification['type']) => {
    switch (type) {
      case 'urgent_movement':
        return 'text-red-600 bg-red-50'
      case 'qualified_lead':
        return 'text-green-600 bg-green-50'
      case 'briefing_available':
        return 'text-blue-600 bg-blue-50'
      case 'mention':
        return 'text-purple-600 bg-purple-50'
      default:
        return 'text-gray-600 bg-gray-50'
    }
  }

  return (
    <div className="relative" data-notification-center>
      {/* Notification Bell Button */}
      <Button
        variant="ghost"
        size="icon"
        className="relative"
        onClick={() => setIsOpen(!isOpen)}
        aria-label="Notificações"
      >
        <Bell className="h-5 w-5" />
        {unreadCount > 0 && (
          <Badge
            variant="destructive"
            className="absolute -top-1 -right-1 h-5 w-5 flex items-center justify-center p-0 text-xs"
          >
            {unreadCount > 99 ? '99+' : unreadCount}
          </Badge>
        )}
      </Button>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-96 z-50">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
              <CardTitle className="text-lg font-semibold">Notificações</CardTitle>
              {unreadCount > 0 && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={markAllAsRead}
                  className="text-xs"
                >
                  Marcar todas como lidas
                </Button>
              )}
            </CardHeader>
            <CardContent className="p-0">
              <div className="max-h-[500px] overflow-y-auto">
                {notifications.length === 0 ? (
                  <div className="p-8 text-center text-gray-500">
                    <Bell className="h-12 w-12 mx-auto mb-2 opacity-20" />
                    <p>Nenhuma notificação</p>
                  </div>
                ) : (
                  <div className="divide-y">
                    {notifications.map((notification) => (
                      <div
                        key={notification.id}
                        className={cn(
                          'p-4 hover:bg-gray-50 transition-colors cursor-pointer',
                          !notification.read && 'bg-blue-50/50'
                        )}
                        onClick={() => markAsRead(notification.id)}
                      >
                        <div className="flex items-start gap-3">
                          {/* Icon */}
                          <div
                            className={cn(
                              'flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center text-lg',
                              getNotificationColor(notification.type)
                            )}
                          >
                            {getNotificationIcon(notification.type)}
                          </div>

                          {/* Content */}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-start justify-between gap-2">
                              <h4 className="text-sm font-semibold text-gray-900">
                                {notification.title}
                              </h4>
                              {!notification.read && (
                                <div className="flex-shrink-0 w-2 h-2 bg-blue-600 rounded-full mt-1" />
                              )}
                            </div>
                            <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                              {notification.message}
                            </p>
                            <p className="text-xs text-gray-400 mt-2">
                              {formatDistanceToNow(new Date(notification.createdAt), {
                                addSuffix: true,
                                locale: ptBR,
                              })}
                            </p>
                          </div>

                          {/* Mark as read button */}
                          {!notification.read && (
                            <Button
                              variant="ghost"
                              size="icon"
                              className="flex-shrink-0 h-8 w-8"
                              onClick={(e) => {
                                e.stopPropagation()
                                markAsRead(notification.id)
                              }}
                              aria-label="Marcar como lida"
                            >
                              <Check className="h-4 w-4" />
                            </Button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
