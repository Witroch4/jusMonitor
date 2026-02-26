'use client'

import { AttentionCaseItem } from '@/types'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import Link from 'next/link'
import { AlertTriangle, Calendar } from 'lucide-react'

interface AttentionCasesProps {
  cases: AttentionCaseItem[]
  isLoading?: boolean
}

export function AttentionCases({ cases, isLoading }: AttentionCasesProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-yellow-600" />
            Precisam de Atenção
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

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-yellow-600" />
          Precisam de Atenção
          <Badge variant="secondary" className="ml-auto">
            {cases.length}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {cases.length === 0 ? (
          <p className="text-sm text-gray-500 text-center py-8">
            Todos os casos estão atualizados
          </p>
        ) : (
          <div className="space-y-3">
            {cases.map((item) => (
              <Link
                key={item.caseId}
                href={`/clientes/${item.clientId}`}
                className="block p-4 border rounded-lg hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <p className="font-medium text-gray-900">{item.clientName}</p>
                    <p className="text-sm text-gray-600 mt-1">{item.cnjNumber}</p>
                    {item.status && (
                      <p className="text-xs text-gray-500 mt-1">{item.status}</p>
                    )}
                  </div>
                  <Badge variant="outline" className="ml-2">
                    {item.daysSinceMovement} dias parado
                  </Badge>
                </div>
                {item.lastMovementDate && (
                  <div className="flex items-center gap-2 mt-2 text-xs text-gray-500">
                    <Calendar className="h-3 w-3" />
                    Última movimentação:{' '}
                    {new Date(item.lastMovementDate).toLocaleDateString('pt-BR')}
                  </div>
                )}
              </Link>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
