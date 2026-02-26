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
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <CheckCircle className="h-5 w-5 text-green-600" />
          Boas Notícias
          <Badge variant="default" className="ml-auto bg-green-600">
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
          <div className="space-y-3">
            {news.map((item) => (
              <Link
                key={item.movementId}
                href={`/clientes/${item.clientId}`}
                className="block p-4 border border-green-200 bg-green-50 rounded-lg hover:bg-green-100 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <p className="font-medium text-gray-900">{item.clientName}</p>
                    <p className="text-sm text-gray-600 mt-1">{item.cnjNumber}</p>
                  </div>
                  <Badge variant="default" className="ml-2 bg-green-600">
                    <CheckCircle className="h-3 w-3 mr-1" />
                    Favorável
                  </Badge>
                </div>
                
                {item.aiSummary ? (
                  <div className="mt-3 p-3 bg-white rounded border border-green-200">
                    <div className="flex items-center gap-2 mb-2">
                      <Sparkles className="h-4 w-4 text-green-600" />
                      <span className="text-xs font-medium text-green-700">Resumo IA</span>
                    </div>
                    <p className="text-sm text-gray-700">{item.aiSummary}</p>
                  </div>
                ) : (
                  <p className="text-sm text-gray-700 mt-2 line-clamp-2">
                    {item.description}
                  </p>
                )}
                
                <div className="flex items-center gap-2 mt-2 text-xs text-gray-500">
                  <Calendar className="h-3 w-3" />
                  {new Date(item.movementDate).toLocaleDateString('pt-BR')}
                </div>
              </Link>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
