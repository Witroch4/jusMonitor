import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import type { Contrato, ContratoListResponse, FaturaListResponse } from '@/types'

interface ContratoFilters {
  search?: string
  status?: string
  tipo?: string
  client_id?: string
  skip?: number
  limit?: number
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}

export function useContratos(filters?: ContratoFilters) {
  return useQuery({
    queryKey: ['contratos', filters],
    queryFn: async () => {
      const response = await apiClient.get<ContratoListResponse>('/contratos', { params: filters })
      return response.data
    },
  })
}

export function useContrato(id: string) {
  return useQuery({
    queryKey: ['contratos', id],
    queryFn: async () => {
      const response = await apiClient.get<Contrato>(`/contratos/${id}`)
      return response.data
    },
    enabled: !!id,
  })
}

export function useContratoFaturas(contratoId: string) {
  return useQuery({
    queryKey: ['contratos', contratoId, 'faturas'],
    queryFn: async () => {
      const response = await apiClient.get<FaturaListResponse>(`/contratos/${contratoId}/faturas`)
      return response.data
    },
    enabled: !!contratoId,
  })
}

export function useCreateContrato() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (data: Partial<Contrato>) => {
      const response = await apiClient.post<Contrato>('/contratos', data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contratos'] })
    },
  })
}

export function useUpdateContrato() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<Contrato> }) => {
      const response = await apiClient.put<Contrato>(`/contratos/${id}`, data)
      return response.data
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['contratos'] })
      queryClient.invalidateQueries({ queryKey: ['contratos', variables.id] })
    },
  })
}

export function useDeleteContrato() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/contratos/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contratos'] })
    },
  })
}

export function useGerarFaturas() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ contratoId, mes, ano }: { contratoId: string; mes?: number; ano?: number }) => {
      const response = await apiClient.post(`/contratos/${contratoId}/gerar-faturas`, null, {
        params: { mes, ano },
      })
      return response.data
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['contratos', variables.contratoId, 'faturas'] })
      queryClient.invalidateQueries({ queryKey: ['faturas'] })
    },
  })
}
