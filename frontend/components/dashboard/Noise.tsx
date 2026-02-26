'use client'

import { NoiseItem } from '@/types'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import Link from 'next/link'
import { Volume2, Calendar, CheckCheck } from 'lucide-react'
import { useState } from 'react'

interface NoiseProps {
  items: NoiseItem[]
  isLoading?: boolean
  onMarkAsRead?: (movementId: string) => void
}

export function Noise({ items, isLoading, onMarkAsRead }: NoiseProps) {
  const [readItems, setReadItems] = useState<Set<string>>(new Set())

  const handleMarkAsRead = (movementId: string, e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setReadItems((prev) => new Set(prev).add(movementId))
    onMarkAsRead?.(movementId)
  }

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Volume2 className="h-5 w-5 text-gray-600" />
            Ruído
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="animate-pulse">
                <div className="h-20 bg-gray-200 rounded"></div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  const visibleItems = items.filter((item) => !readItems.has(item.movementId))

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Volume2 className="h-5 w-5 text-gray-600" />
          Ruído
          <Badge variant="outline" className="ml-auto">
            {visibleItems.length}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {visibleItems.length === 0 ? (
          <p className="text-sm text-gray-500 text-center py-8">
            Nenhuma movimentação irrelevante
          </p>
        ) : (
          <div className="space-y-3">
            {visibleItems.map((item) => (
              <div
                key={item.movementId}
                className="p-4 border rounded-lg bg-gray-50 hover:bg-gray-100 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <Link
                    href={`/clientes/${item.clientId}`}
                    className="flex-1"
                  >
                    <p className="font-medium text-gray-900">{item.clientName}</p>
                    <p className="text-sm text-gray-600 mt-1">{item.cnjNumber}</p>
                    <p className="text-sm text-gray-700 mt-2 line-clamp-2">
                      {item.description}
                    </p>
                    <div className="flex items-center gap-2 mt-2 text-xs text-gray-500">
                      <Calendar className="h-3 w-3" />
                      {new Date(item.movementDate).toLocaleDateString('pt-BR')}
                    </div>
                  </Link>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => handleMarkAsRead(item.movementId, e)}
                    className="ml-2"
                  >
                    <CheckCheck className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
