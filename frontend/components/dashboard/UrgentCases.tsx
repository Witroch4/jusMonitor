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
    <Card className="border-border/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)] rounded-xl overflow-hidden hover:shadow-[0_8px_30px_rgb(0,0,0,0.08)] transition-all duration-300">
      <CardHeader className="bg-red-50/50 border-b border-red-100/50 pb-4">
        <CardTitle className="flex items-center gap-2 font-serif text-xl text-primary">
          <AlertCircle className="h-5 w-5 text-red-600" />
          Atenção Imediata Necessária
          <Badge variant="destructive" className="ml-auto font-sans">
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
          <div className="space-y-4 mt-2">
            {cases.map((item) => (
              <Link
                key={item.caseId}
                href={`/clientes/${item.clientId}`}
                className="block p-5 border border-border/40 rounded-xl bg-card hover:bg-muted/30 transition-all duration-300 group"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <p className="font-serif font-semibold text-lg text-foreground group-hover:text-primary transition-colors">{item.clientName}</p>
                    <p className="text-sm font-medium text-muted-foreground mt-1">{item.cnjNumber}</p>
                    {item.caseType && (
                      <p className="text-xs font-medium text-muted-foreground mt-1.5 px-2 py-0.5 bg-muted rounded-md inline-block">{item.caseType}</p>
                    )}
                  </div>
                  <Badge
                    variant={item.daysRemaining <= 1 ? 'destructive' : 'default'}
                    className="ml-2 shadow-sm font-medium"
                  >
                    <Clock className="h-3 w-3 mr-1.5" />
                    {item.daysRemaining} {item.daysRemaining === 1 ? 'dia restante' : 'dias restantes'}
                  </Badge>
                </div>
                <div className="flex items-center gap-2 mt-4 text-sm font-medium text-muted-foreground bg-secondary/5 p-2 rounded-lg border border-secondary/10">
                  <Calendar className="h-4 w-4 text-secondary-foreground/60" />
                  Prazo final limite: <span className="text-foreground tracking-wide">{new Date(item.nextDeadline).toLocaleDateString('pt-BR')}</span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
