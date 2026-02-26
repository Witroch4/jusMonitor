'use client'

import { UrgentCaseItem } from '@/types'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import Link from 'next/link'
import { AlertCircle, Calendar, Clock } from 'lucide-react'

interface UrgentCasesProps {
  cases: UrgentCaseItem[]
  isLoading?: boolean
}

export function UrgentCases({ cases, isLoading }: UrgentCasesProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-red-600" />
            Casos Urgentes
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
          <AlertCircle className="h-5 w-5 text-red-600" />
          Casos Urgentes
          <Badge variant="destructive" className="ml-auto">
            {cases.length}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {cases.length === 0 ? (
          <p className="text-sm text-gray-500 text-center py-8">
            Nenhum caso urgente no momento
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
                    {item.caseType && (
                      <p className="text-xs text-gray-500 mt-1">{item.caseType}</p>
                    )}
                  </div>
                  <Badge
                    variant={item.daysRemaining <= 1 ? 'destructive' : 'default'}
                    className="ml-2"
                  >
                    <Clock className="h-3 w-3 mr-1" />
                    {item.daysRemaining} {item.daysRemaining === 1 ? 'dia' : 'dias'}
                  </Badge>
                </div>
                <div className="flex items-center gap-2 mt-2 text-xs text-gray-500">
                  <Calendar className="h-3 w-3" />
                  Prazo: {new Date(item.nextDeadline).toLocaleDateString('pt-BR')}
                </div>
              </Link>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
