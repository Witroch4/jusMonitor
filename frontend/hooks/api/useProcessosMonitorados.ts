import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'

export interface ProcessoMonitoradoDB {
  id: string
  numero: string
  apelido?: string | null
  dadosDatajud?: Record<string, unknown> | null
  ultimaConsulta?: string | null
  movimentacoesConhecidas: number
  novasMovimentacoes: number
  peticaoId?: string | null
  criadoPor?: string | null
  criadoEm: string
  atualizadoEm: string
}

interface ProcessoMonitoradoListResponse {
  items: ProcessoMonitoradoDB[]
  total: number
}

export function useProcessosMonitoradosAPI() {
  return useQuery({
    queryKey: ['processos-monitorados'],
    queryFn: async (): Promise<ProcessoMonitoradoListResponse> => {
      const { data } = await apiClient.get<ProcessoMonitoradoListResponse>('/processos-monitorados')
      return data
    },
    staleTime: 30_000,
  })
}

export function useAdicionarProcessoMonitorado() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (params: { numero: string; apelido?: string }): Promise<ProcessoMonitoradoDB> => {
      const { data } = await apiClient.post<ProcessoMonitoradoDB>('/processos-monitorados', params)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['processos-monitorados'] })
    },
  })
}

export function useRemoverProcessoMonitorado() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (id: string): Promise<void> => {
      await apiClient.delete(`/processos-monitorados/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['processos-monitorados'] })
    },
  })
}

export function useConsultarProcessoMonitorado() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (id: string): Promise<ProcessoMonitoradoDB> => {
      const { data } = await apiClient.post<ProcessoMonitoradoDB>(`/processos-monitorados/${id}/consultar`)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['processos-monitorados'] })
    },
  })
}

export function useMarcarVistoProcessoMonitorado() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (id: string): Promise<ProcessoMonitoradoDB> => {
      const { data } = await apiClient.post<ProcessoMonitoradoDB>(`/processos-monitorados/${id}/visto`)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['processos-monitorados'] })
    },
  })
}
