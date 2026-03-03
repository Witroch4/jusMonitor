import { useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import type {
  CasoOAB,
  CasoOABDetail,
  CasoOABListResponse,
  SyncStatusResponse,
  SyncTriggerResponse,
} from '@/types/casos-oab'

// --- Queries ---

export function useCasosOAB() {
  return useQuery({
    queryKey: ['casos-oab'],
    queryFn: async (): Promise<CasoOABListResponse> => {
      const { data } = await apiClient.get<CasoOABListResponse>('/casos-oab')
      return data
    },
    staleTime: 30_000,
  })
}

export function useCasoDetalhe(id: string | null) {
  return useQuery({
    queryKey: ['casos-oab', id],
    queryFn: async (): Promise<CasoOABDetail> => {
      const { data } = await apiClient.get<CasoOABDetail>(`/casos-oab/${id}`)
      return data
    },
    enabled: !!id,
    staleTime: 30_000,
  })
}

export function useSyncStatus() {
  const queryClient = useQueryClient()
  const prevStatusRef = useRef<string | undefined>(undefined)

  const query = useQuery({
    queryKey: ['casos-oab-sync-status'],
    queryFn: async (): Promise<SyncStatusResponse> => {
      const { data } = await apiClient.get<SyncStatusResponse>('/casos-oab/sync-status')
      return data
    },
    staleTime: 0,
    // Poll every 3s while sync is running
    refetchInterval: (q) => {
      const status = q.state.data?.status
      return status === 'running' ? 3000 : false
    },
  })

  // When status transitions running → idle/error, refresh the cases list
  useEffect(() => {
    const currentStatus = query.data?.status
    if (prevStatusRef.current === 'running' && currentStatus !== 'running') {
      queryClient.invalidateQueries({ queryKey: ['casos-oab'] })
    }
    prevStatusRef.current = currentStatus
  }, [query.data?.status, queryClient])

  return query
}

// --- Mutations ---

export function useSyncCasos() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (): Promise<SyncTriggerResponse> => {
      const { data } = await apiClient.post<SyncTriggerResponse>('/casos-oab/sync')
      return data
    },
    onSuccess: () => {
      // Start polling: invalidate status so refetchInterval kicks in immediately
      queryClient.invalidateQueries({ queryKey: ['casos-oab-sync-status'] })
    },
  })
}

export function useAdicionarCaso() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (numero: string): Promise<CasoOAB> => {
      const { data } = await apiClient.post<CasoOAB>('/casos-oab', { numero })
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['casos-oab'] })
    },
  })
}

export function useRemoverCaso() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (id: string): Promise<void> => {
      await apiClient.delete(`/casos-oab/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['casos-oab'] })
    },
  })
}

export function useMarcarCasoVisto() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (id: string): Promise<CasoOAB> => {
      const { data } = await apiClient.post<CasoOAB>(`/casos-oab/${id}/visto`)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['casos-oab'] })
    },
  })
}
