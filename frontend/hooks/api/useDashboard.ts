'use client'

import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import type {
  UrgentCaseItem,
  AttentionCaseItem,
  GoodNewsItem,
  NoiseItem,
  DashboardMetrics,
} from '@/types'

interface DashboardFilters {
  limit?: number
  assignedTo?: string | null
  days?: number
}

export function useUrgentCases(filters: DashboardFilters = {}) {
  return useQuery({
    queryKey: ['dashboard', 'urgent', filters],
    queryFn: async () => {
      const response = await apiClient.get<{ items: UrgentCaseItem[]; total: number }>(
        '/dashboard/urgent',
        { params: { limit: 20, ...filters } }
      )
      return response.data
    },
  })
}

export function useAttentionCases(filters: DashboardFilters = {}) {
  return useQuery({
    queryKey: ['dashboard', 'attention', filters],
    queryFn: async () => {
      const response = await apiClient.get<{ items: AttentionCaseItem[]; total: number }>(
        '/dashboard/attention',
        { params: { limit: 20, ...filters } }
      )
      return response.data
    },
  })
}

export function useGoodNews(filters: DashboardFilters = {}) {
  return useQuery({
    queryKey: ['dashboard', 'good-news', filters],
    queryFn: async () => {
      const response = await apiClient.get<{ items: GoodNewsItem[]; total: number }>(
        '/dashboard/good-news',
        { params: { limit: 20, days: 7, ...filters } }
      )
      return response.data
    },
  })
}

export function useNoise(filters: DashboardFilters = {}) {
  return useQuery({
    queryKey: ['dashboard', 'noise', filters],
    queryFn: async () => {
      const response = await apiClient.get<{ items: NoiseItem[]; total: number }>(
        '/dashboard/noise',
        { params: { limit: 20, days: 7, ...filters } }
      )
      return response.data
    },
  })
}

export function useDashboardMetrics(days: number = 30) {
  return useQuery({
    queryKey: ['dashboard', 'metrics', days],
    queryFn: async () => {
      const response = await apiClient.get<DashboardMetrics>('/dashboard/metrics', {
        params: { days },
      })
      return response.data
    },
  })
}

export function useDashboardSummary() {
  return useQuery({
    queryKey: ['dashboard', 'summary'],
    queryFn: async () => {
      const response = await apiClient.get<{
        urgent_count: number
        attention_count: number
        good_news_count: number
        noise_count: number
      }>('/dashboard/summary')
      return response.data
    },
  })
}
