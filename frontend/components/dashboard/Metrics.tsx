'use client'

import { DashboardMetrics } from '@/types'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { TrendingUp, TrendingDown, Users, Briefcase, Clock, Star } from 'lucide-react'

interface MetricsProps {
  data: DashboardMetrics | null
  isLoading?: boolean
}

function MetricCard({
  title,
  value,
  change,
  icon: Icon,
  suffix = '',
}: {
  title: string
  value: number
  change: number
  icon: any
  suffix?: string
}) {
  const safeValue = value || 0
  const safeChange = change || 0
  const isPositive = safeChange >= 0
  const TrendIcon = isPositive ? TrendingUp : TrendingDown

  return (
    <div className="p-6 border border-border/40 rounded-2xl bg-card shadow-sm hover:shadow-md transition-all duration-300">
      <div className="flex items-center justify-between mb-4">
        <span className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">{title}</span>
        <div className="p-2.5 bg-primary/10 rounded-xl">
          <Icon className="h-5 w-5 text-primary" />
        </div>
      </div>
      <div className="flex items-end justify-between">
        <div className="w-full">
          <p className="text-4xl font-serif font-bold text-foreground">
            {safeValue.toFixed(suffix === '%' ? 1 : 0)}
            <span className="text-xl ml-1 text-muted-foreground/80 font-medium">{suffix}</span>
          </p>
          <div
            className={`flex items-center gap-1.5 mt-3 text-sm font-medium px-2.5 py-1 rounded-full inline-flex ${isPositive ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-rose-50 text-rose-700 border border-rose-200'
              }`}
          >
            <TrendIcon className="h-4 w-4" />
            <span>
              {Math.abs(safeChange).toFixed(1)}% vs anterior
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}

export function Metrics({ data, isLoading }: MetricsProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Métricas do Escritório</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="animate-pulse">
                <div className="h-24 bg-gray-200 rounded"></div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Métricas do Escritório</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-500 text-center py-8">
            Dados de métricas não disponíveis
          </p>
        </CardContent>
      </Card>
    )
  }

  const { metrics } = data

  return (
    <Card className="border-0 shadow-none bg-transparent">
      <CardHeader className="pb-4 px-6 pt-6">
        <CardTitle className="text-2xl font-serif text-primary">Visão Estratégica</CardTitle>
        <p className="text-sm font-medium text-muted-foreground mt-1 tracking-wide">
          Período analisado: {new Date(data.periodStart).toLocaleDateString('pt-BR')} a{' '}
          {new Date(data.periodEnd).toLocaleDateString('pt-BR')}
        </p>
      </CardHeader>
      <CardContent>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <MetricCard
            title="Taxa de Conversão"
            value={metrics.conversionRate}
            change={metrics.conversionRateChange}
            icon={TrendingUp}
            suffix="%"
          />

          <MetricCard
            title="Tempo Médio de Resposta"
            value={metrics.avgResponseTimeHours}
            change={metrics.avgResponseTimeChange}
            icon={Clock}
            suffix="h"
          />

          <MetricCard
            title="Satisfação do Cliente"
            value={metrics.satisfactionScore}
            change={metrics.satisfactionScoreChange}
            icon={Star}
            suffix="/100"
          />

          <div className="p-6 border border-border/40 rounded-2xl bg-card shadow-sm hover:shadow-md transition-all duration-300">
            <div className="flex items-center justify-between mb-4">
              <span className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Processos Ativos</span>
              <div className="p-2.5 bg-primary/10 rounded-xl">
                <Briefcase className="h-5 w-5 text-primary" />
              </div>
            </div>
            <p className="text-4xl font-serif font-bold text-foreground">
              {metrics.totalActiveCases}
            </p>
            <p className="text-sm font-semibold mt-3 px-2.5 py-1 rounded-full inline-flex bg-accent/10 text-accent-foreground border border-accent/20">
              +{metrics.newCasesThisPeriod} novos neste período
            </p>
          </div>

          <div className="p-6 border border-border/40 rounded-2xl bg-card shadow-sm hover:shadow-md transition-all duration-300">
            <div className="flex items-center justify-between mb-4">
              <span className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Clientes Ativos</span>
              <div className="p-2.5 bg-primary/10 rounded-xl">
                <Users className="h-5 w-5 text-primary" />
              </div>
            </div>
            <p className="text-4xl font-serif font-bold text-foreground">
              {metrics.totalActiveClients}
            </p>
            <p className="text-sm font-semibold mt-3 px-2.5 py-1 rounded-full inline-flex bg-accent/10 text-accent-foreground border border-accent/20">
              +{metrics.newClientsThisPeriod} novos neste período
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
