import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import type {
  Peticao,
  PeticaoListItem,
  PeticaoFilters,
  PeticaoEvento,
  PeticaoDocumento,
  TipoDocumento,
  NovaPeticaoFormData,
} from '@/types/peticoes'

interface PeticaoListResponse {
  items: PeticaoListItem[]
  total: number
}

export function usePeticoes(filters?: PeticaoFilters) {
  return useQuery({
    queryKey: ['peticoes', filters],
    queryFn: async (): Promise<PeticaoListResponse> => {
      const params: Record<string, string> = {}
      if (filters?.search) params.search = filters.search
      if (filters?.status && filters.status !== 'all') params.status = filters.status
      if (filters?.tribunalId && filters.tribunalId !== 'all') params.tribunal_id = filters.tribunalId
      const { data } = await apiClient.get<PeticaoListResponse>('/peticoes', { params })
      return data
    },
  })
}

export function usePeticao(id: string) {
  return useQuery({
    queryKey: ['peticoes', id],
    queryFn: async (): Promise<Peticao> => {
      const { data } = await apiClient.get<Peticao>(`/peticoes/${id}`)
      return data
    },
    enabled: !!id,
  })
}

export function usePeticaoEventos(peticaoId: string) {
  return useQuery({
    queryKey: ['peticoes', peticaoId, 'eventos'],
    queryFn: async (): Promise<PeticaoEvento[]> => {
      const { data } = await apiClient.get<PeticaoEvento[]>(`/peticoes/${peticaoId}/eventos`)
      return data
    },
    enabled: !!peticaoId,
  })
}

export function useConsultarProcesso() {
  return useMutation({
    mutationFn: async (params: {
      numeroProcesso: string
      tribunalId: string
      certificadoId: string
    }) => {
      const { data } = await apiClient.post('/peticoes/consultar-processo', {
        numeroProcesso: params.numeroProcesso,
        tribunalId: params.tribunalId,
        certificadoId: params.certificadoId,
      })
      return data
    },
  })
}

export function useCreatePeticao() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (formData: NovaPeticaoFormData): Promise<Peticao> => {
      const { data } = await apiClient.post<Peticao>('/peticoes', {
        processoNumero: formData.processoNumero,
        tribunalId: formData.tribunalId,
        tipoPeticao: formData.tipoPeticao,
        assunto: formData.assunto,
        descricao: formData.descricao || undefined,
        certificadoId: formData.certificadoId || undefined,
        dadosBasicos: formData.dadosBasicos || undefined,
      })
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['peticoes'] })
    },
  })
}

export function useUpdatePeticao() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      id,
      ...body
    }: {
      id: string
      assunto?: string
      descricao?: string
      certificadoId?: string
      tribunalId?: string
      processoNumero?: string
      tipoPeticao?: string
    }): Promise<Peticao> => {
      const { data } = await apiClient.patch<Peticao>(`/peticoes/${id}`, body)
      return data
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['peticoes'] })
      queryClient.invalidateQueries({ queryKey: ['peticoes', variables.id] })
    },
  })
}

export function useDeletePeticao() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (id: string): Promise<void> => {
      await apiClient.delete(`/peticoes/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['peticoes'] })
    },
  })
}

export function useUploadDocumento() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (params: {
      peticaoId: string
      arquivo: File
      tipoDocumento: TipoDocumento
      ordem: number
      sigiloso?: boolean
    }): Promise<PeticaoDocumento> => {
      const form = new FormData()
      form.append('arquivo', params.arquivo)
      form.append('tipo_documento', params.tipoDocumento)
      form.append('ordem', String(params.ordem))
      form.append('sigiloso', String(params.sigiloso ?? false))
      const { data } = await apiClient.post<PeticaoDocumento>(
        `/peticoes/${params.peticaoId}/documentos`,
        form,
        { headers: { 'Content-Type': 'multipart/form-data' } },
      )
      return data
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['peticoes', variables.peticaoId] })
    },
  })
}

export function useDeleteDocumento() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (params: {
      peticaoId: string
      docId: string
    }): Promise<void> => {
      await apiClient.delete(`/peticoes/${params.peticaoId}/documentos/${params.docId}`)
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['peticoes', variables.peticaoId] })
    },
  })
}

export function useProtocolar() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (peticaoId: string): Promise<{ message: string; peticaoId: string }> => {
      const { data } = await apiClient.post(`/peticoes/${peticaoId}/protocolar`)
      return data
    },
    onSuccess: (_, peticaoId) => {
      queryClient.invalidateQueries({ queryKey: ['peticoes'] })
      queryClient.invalidateQueries({ queryKey: ['peticoes', peticaoId] })
      queryClient.invalidateQueries({ queryKey: ['peticoes', peticaoId, 'eventos'] })
    },
  })
}

export function usePeticoesProtocoladas() {
  return useQuery({
    queryKey: ['peticoes', 'protocoladas'],
    queryFn: async (): Promise<PeticaoListItem[]> => {
      const { data } = await apiClient.get<PeticaoListResponse>('/peticoes', {
        params: { status: 'PROTOCOLADA' },
      })
      return data.items.filter((p) => p.numeroProtocolo)
    },
    staleTime: 5 * 60_000,
  })
}

export function useValidarPeticao() {
  return useMutation({
    mutationFn: async (peticaoId: string): Promise<{ pronta: boolean; errors: string[] }> => {
      const { data } = await apiClient.get(`/peticoes/${peticaoId}/validar`)
      return data
    },
  })
}

export function useAnaliseIA() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (peticaoId: string): Promise<void> => {
      await apiClient.post(`/peticoes/${peticaoId}/analise-ia`)
    },
    onSuccess: (_, peticaoId) => {
      queryClient.invalidateQueries({ queryKey: ['peticoes', peticaoId] })
    },
  })
}
