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
  const isPositive = change >= 0
  const TrendIcon = isPositive ? TrendingUp : TrendingDown

  return (
    <div className="p-4 border rounded-lg bg-white">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-600">{title}</span>
        <Icon className="h-4 w-4 text-gray-400" />
      </div>
      <div className="flex items-end justify-between">
        <div>
          <p className="text-2xl font-bold text-gray-900">
            {value.toFixed(suffix === '%' ? 1 : 0)}
            {suffix}
          </p>
          <div
            className={`flex items-center gap-1 mt-1 text-xs ${
              isPositive ? 'text-green-600' : 'text-red-600'
            }`}
          >
            <TrendIcon className="h-3 w-3" />
            <span>
              {Math.abs(change).toFixed(1)}% vs período anterior
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
    <Card>
      <CardHeader>
        <CardTitle>Métricas do Escritório</CardTitle>
        <p className="text-sm text-gray-500 mt-1">
          Período: {new Date(data.periodStart).toLocaleDateString('pt-BR')} -{' '}
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
          
          <div className="p-4 border rounded-lg bg-white">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-600">Processos Ativos</span>
              <Briefcase className="h-4 w-4 text-gray-400" />
            </div>
            <p className="text-2xl font-bold text-gray-900">
              {metrics.totalActiveCases}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              +{metrics.newCasesThisPeriod} novos neste período
            </p>
          </div>
          
          <div className="p-4 border rounded-lg bg-white">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-600">Clientes Ativos</span>
              <Users className="h-4 w-4 text-gray-400" />
            </div>
            <p className="text-2xl font-bold text-gray-900">
              {metrics.totalActiveClients}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              +{metrics.newClientsThisPeriod} novos neste período
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
