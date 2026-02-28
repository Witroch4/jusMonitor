'use client'

import { GoodNewsItem } from '@/types'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import Link from 'next/link'
import { CheckCircle, Calendar, Sparkles } from 'lucide-react'

interface GoodNewsProps {
  news: GoodNewsItem[]
  isLoading?: boolean
}

export function GoodNews({ news, isLoading }: GoodNewsProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CheckCircle className="h-5 w-5 text-green-600" />
            Boas Notícias
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="animate-pulse">
                <div className="h-24 bg-gray-200 rounded"></div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="border-border/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)] rounded-xl overflow-hidden hover:shadow-[0_8px_30px_rgb(0,0,0,0.08)] transition-all duration-300">
      <CardHeader className="bg-green-50/50 border-b border-green-100/50 pb-4">
        <CardTitle className="flex items-center gap-2 font-serif text-xl text-primary">
          <CheckCircle className="h-5 w-5 text-green-600" />
          Decisões Favoráveis
          <Badge variant="default" className="ml-auto bg-green-600 font-sans font-medium">
            {news.length}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {news.length === 0 ? (
          <p className="text-sm text-gray-500 text-center py-8">
            Nenhuma boa notícia recente
          </p>
        ) : (
          <div className="space-y-4 mt-2">
            {news.map((item) => (
              <Link
                key={item.movementId}
                href={`/clientes/${item.clientId}`}
                className="block p-5 border border-green-200/60 rounded-xl bg-green-50/30 hover:bg-green-50/80 transition-all duration-300 group shadow-sm"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <p className="font-serif font-semibold text-lg text-foreground group-hover:text-primary transition-colors">{item.clientName}</p>
                    <p className="text-sm font-medium text-muted-foreground mt-1">{item.cnjNumber}</p>
                  </div>
                  <Badge variant="default" className="ml-2 bg-green-600 shadow-sm font-medium">
                    <CheckCircle className="h-3 w-3 mr-1.5" />
                    Favorável
                  </Badge>
                </div>

                {item.aiSummary ? (
                  <div className="mt-4 p-4 bg-white/80 rounded-lg border border-green-100 shadow-sm">
                    <div className="flex items-center gap-2 mb-2">
                      <Sparkles className="h-4 w-4 text-green-600" />
                      <span className="text-xs font-semibold text-green-700 tracking-wide uppercase">Síntese de IA</span>
                    </div>
                    <p className="text-sm font-medium text-foreground leading-relaxed">{item.aiSummary}</p>
                  </div>
                ) : (
                  <p className="text-sm font-medium text-muted-foreground mt-3 line-clamp-2 leading-relaxed">
                    {item.description}
                  </p>
                )}

                <div className="flex items-center gap-2 mt-4 text-sm font-medium text-muted-foreground">
                  <Calendar className="h-4 w-4" />
                  Registrado em: <span className="text-foreground tracking-wide">{new Date(item.movementDate).toLocaleDateString('pt-BR')}</span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
