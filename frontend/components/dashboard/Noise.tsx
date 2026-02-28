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
    <Card className="border-border/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)] rounded-xl overflow-hidden hover:shadow-[0_8px_30px_rgb(0,0,0,0.08)] transition-all duration-300">
      <CardHeader className="bg-muted/30 border-b border-border/40 pb-4">
        <CardTitle className="flex items-center gap-2 font-serif text-xl text-primary">
          <Volume2 className="h-5 w-5 text-muted-foreground" />
          Eventos Secundários
          <Badge variant="outline" className="ml-auto bg-background shadow-sm font-medium">
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
          <div className="space-y-4 mt-2">
            {visibleItems.map((item) => (
              <div
                key={item.movementId}
                className="p-5 border border-border/40 rounded-xl bg-card hover:bg-muted/30 transition-all duration-300 group shadow-sm"
              >
                <div className="flex items-start justify-between">
                  <Link
                    href={`/clientes/${item.clientId}`}
                    className="flex-1 pr-4"
                  >
                    <p className="font-serif font-semibold text-lg text-foreground group-hover:text-primary transition-colors">{item.clientName}</p>
                    <p className="text-sm font-medium text-muted-foreground mt-1">{item.cnjNumber}</p>
                    <p className="text-sm font-medium text-muted-foreground mt-3 line-clamp-2 leading-relaxed">
                      {item.description}
                    </p>
                    <div className="flex items-center gap-2 mt-4 text-sm font-medium text-muted-foreground">
                      <Calendar className="h-4 w-4" />
                      Registrado em: <span className="text-foreground tracking-wide">{new Date(item.movementDate).toLocaleDateString('pt-BR')}</span>
                    </div>
                  </Link>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => handleMarkAsRead(item.movementId, e)}
                    className="ml-2 text-muted-foreground hover:text-primary hover:bg-primary/5 transition-colors"
                    title="Marcar como lido"
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
