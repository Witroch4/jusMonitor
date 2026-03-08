import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import type {
  Fatura,
  FaturaListResponse,
  Lancamento,
  LancamentoListResponse,
  FinanceiroDashboard,
} from '@/types'

export function useFinanceiroDashboard() {
  return useQuery({
    queryKey: ['financeiro', 'dashboard'],
    queryFn: async () => {
      const response = await apiClient.get<FinanceiroDashboard>('/financeiro/dashboard')
      return response.data
    },
  })
}

interface FaturaFilters {
  status?: string
  contrato_id?: string
  data_inicio?: string
  data_fim?: string
  skip?: number
  limit?: number
}

export function useFaturas(filters?: FaturaFilters) {
  return useQuery({
    queryKey: ['faturas', filters],
    queryFn: async () => {
      const response = await apiClient.get<FaturaListResponse>('/financeiro/faturas', { params: filters })
      return response.data
    },
  })
}

export function useRegistrarPagamento() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ faturaId, data }: { faturaId: string; data: { forma_pagamento: string; valor_pago?: number; data_pagamento?: string } }) => {
      const response = await apiClient.put<Fatura>(`/financeiro/faturas/${faturaId}`, {
        ...data,
        status: 'paga',
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['faturas'] })
      queryClient.invalidateQueries({ queryKey: ['financeiro', 'dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['contratos'] })
    },
  })
}

interface LancamentoFilters {
  tipo?: string
  categoria?: string
  contrato_id?: string
  data_inicio?: string
  data_fim?: string
  skip?: number
  limit?: number
}

export function useLancamentos(filters?: LancamentoFilters) {
  return useQuery({
    queryKey: ['lancamentos', filters],
    queryFn: async () => {
      const response = await apiClient.get<LancamentoListResponse>('/financeiro/lancamentos', { params: filters })
      return response.data
    },
  })
}

export function useCreateLancamento() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (data: Partial<Lancamento>) => {
      const response = await apiClient.post<Lancamento>('/financeiro/lancamentos', data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lancamentos'] })
      queryClient.invalidateQueries({ queryKey: ['financeiro', 'dashboard'] })
    },
  })
}
