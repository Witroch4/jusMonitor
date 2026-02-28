import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type { PeticaoFilters, AnaliseIA } from '@/types/peticoes'
import { fetchPeticoes, fetchPeticao, fetchPeticaoEventos, createPeticao, runAnaliseIA } from '@/lib/mock/peticoes-data'

export function usePeticoes(filters?: PeticaoFilters) {
  return useQuery({
    queryKey: ['peticoes', filters],
    queryFn: () => fetchPeticoes(filters),
  })
}

export function usePeticao(id: string) {
  return useQuery({
    queryKey: ['peticoes', id],
    queryFn: () => fetchPeticao(id),
    enabled: !!id,
  })
}

export function usePeticaoEventos(peticaoId: string) {
  return useQuery({
    queryKey: ['peticoes', peticaoId, 'eventos'],
    queryFn: () => fetchPeticaoEventos(peticaoId),
    enabled: !!peticaoId,
  })
}

export function useCreatePeticao() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: createPeticao,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['peticoes'] })
    },
  })
}

export function useAnaliseIA() {
  return useMutation<AnaliseIA, Error>({
    mutationFn: runAnaliseIA,
  })
}
