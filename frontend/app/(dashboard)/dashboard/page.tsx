'use client'

import { useState, useEffect, useCallback } from 'react'
import { apiClient } from '@/lib/api-client'
import { UrgentCases } from '@/components/dashboard/UrgentCases'
import { AttentionCases } from '@/components/dashboard/AttentionCases'
import { GoodNews } from '@/components/dashboard/GoodNews'
import { Noise } from '@/components/dashboard/Noise'
import { Metrics } from '@/components/dashboard/Metrics'
import { useDashboardRealtime } from '@/hooks/useDashboardRealtime'
import { Button } from '@/components/ui/button'
import { RefreshCw, Filter, Bell } from 'lucide-react'
import type {
  UrgentCaseItem,
  AttentionCaseItem,
  GoodNewsItem,
  NoiseItem,
  DashboardMetrics,
} from '@/types'

interface DashboardData {
  urgent: UrgentCaseItem[]
  attention: AttentionCaseItem[]
  goodNews: GoodNewsItem[]
  noise: NoiseItem[]
  metrics: DashboardMetrics | null
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData>({
    urgent: [],
    attention: [],
    goodNews: [],
    noise: [],
    metrics: null,
  })
  const [isLoading, setIsLoading] = useState(true)
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date())
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [hasNewData, setHasNewData] = useState(false)
  const [filters, setFilters] = useState({
    period: 30,
    assignedTo: null as string | null,
  })

  const fetchDashboardData = useCallback(async (silent = false) => {
    if (!silent) {
      setIsLoading(true)
    }
    try {
      const [urgentRes, attentionRes, goodNewsRes, noiseRes, metricsRes] =
        await Promise.all([
          apiClient.get('/dashboard/urgent', {
            params: { limit: 20, assigned_to: filters.assignedTo },
          }),
          apiClient.get('/dashboard/attention', {
            params: { limit: 20, assigned_to: filters.assignedTo },
          }),
          apiClient.get('/dashboard/good-news', {
            params: { limit: 20, days: 7, assigned_to: filters.assignedTo },
          }),
          apiClient.get('/dashboard/noise', {
            params: { limit: 20, days: 7, assigned_to: filters.assignedTo },
          }),
          apiClient.get('/dashboard/metrics', {
            params: { days: filters.period },
          }),
        ])

      const newData = {
        urgent: urgentRes.data.items || [],
        attention: attentionRes.data.items || [],
        goodNews: goodNewsRes.data.items || [],
        noise: noiseRes.data.items || [],
        metrics: metricsRes.data || null,
      }

      // Check if there's new data
      if (silent && JSON.stringify(newData) !== JSON.stringify(data)) {
        setHasNewData(true)
      }

      setData(newData)
      setLastUpdate(new Date())
      setHasNewData(false)
    } catch (error) {
      console.error('Error fetching dashboard data:', error)
    } finally {
      if (!silent) {
        setIsLoading(false)
      }
    }
  }, [filters, data])

  // Real-time updates
  useDashboardRealtime({
    onUpdate: () => fetchDashboardData(true),
    interval: 60000, // 1 minute
    enabled: autoRefresh,
  })

  useEffect(() => {
    fetchDashboardData()
  }, [])

  useEffect(() => {
    // Refetch when filters change
    fetchDashboardData()
  }, [filters.period, filters.assignedTo])

  const handleRefresh = () => {
    fetchDashboardData()
  }

  const toggleAutoRefresh = () => {
    setAutoRefresh(!autoRefresh)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            Central Operacional
          </h1>
          <p className="mt-2 text-sm text-gray-600">
            Última atualização:{' '}
            {lastUpdate.toLocaleTimeString('pt-BR', {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={toggleAutoRefresh}
            className={autoRefresh ? 'bg-green-50' : ''}
          >
            <Bell className="h-4 w-4 mr-2" />
            {autoRefresh ? 'Auto-atualização ativa' : 'Auto-atualização pausada'}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={isLoading}
          >
            <RefreshCw
              className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`}
            />
            Atualizar
          </Button>
          {hasNewData && (
            <span className="text-xs text-green-600 font-medium">
              Novos dados disponíveis
            </span>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 p-4 bg-white rounded-lg border">
        <Filter className="h-4 w-4 text-gray-500" />
        <span className="text-sm font-medium text-gray-700">Filtros:</span>
        <select
          value={filters.period}
          onChange={(e) =>
            setFilters({ ...filters, period: Number(e.target.value) })
          }
          className="px-3 py-1.5 text-sm border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value={7}>Últimos 7 dias</option>
          <option value={30}>Últimos 30 dias</option>
          <option value={60}>Últimos 60 dias</option>
          <option value={90}>Últimos 90 dias</option>
        </select>
      </div>

      {/* Metrics Section */}
      <Metrics data={data.metrics} isLoading={isLoading} />

      {/* Dashboard Grid - 5 blocks */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Urgent Cases */}
        <UrgentCases cases={data.urgent} isLoading={isLoading} />

        {/* Attention Cases */}
        <AttentionCases cases={data.attention} isLoading={isLoading} />

        {/* Good News */}
        <GoodNews news={data.goodNews} isLoading={isLoading} />

        {/* Noise */}
        <Noise items={data.noise} isLoading={isLoading} />
      </div>
    </div>
  )
}
