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

/** Remove empty-name parties/lawyers from polos before sending to backend */
function sanitizeDadosBasicos(db: NovaPeticaoFormData['dadosBasicos']) {
  if (!db) return undefined
  const polos = db.polos
    .map((polo) => ({
      ...polo,
      partes: polo.partes.filter((p) => p.nome?.trim()),
      advogados: (polo.advogados ?? []).filter((a) => a.nome?.trim()),
    }))
    .filter((polo) => polo.partes.length > 0 || polo.advogados.length > 0)

  const hasAnyData =
    polos.length > 0 ||
    (db.assuntos?.length ?? 0) > 0 ||
    db.classeProcessual ||
    db.valorCausa ||
    db.codigoLocalidade

  if (!hasAnyData) return undefined

  return { ...db, polos }
}

export function useCreatePeticao() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (formData: NovaPeticaoFormData): Promise<Peticao> => {
      const payload: Record<string, unknown> = {
        processoNumero: formData.processoNumero || '',
        tribunalId: formData.tribunalId,
        assunto: formData.assunto || '',
      }
      // Only send tipoPeticao if the user actually picked one
      if (formData.tipoPeticao) payload.tipoPeticao = formData.tipoPeticao
      if (formData.descricao) payload.descricao = formData.descricao
      if (formData.certificadoId) payload.certificadoId = formData.certificadoId
      if (formData.tipoPeticaoPje) payload.tipoPeticaoPje = formData.tipoPeticaoPje
      if (formData.descricaoPje) payload.descricaoPje = formData.descricaoPje
      const db = sanitizeDadosBasicos(formData.dadosBasicos)
      if (db) payload.dadosBasicos = db

      const { data } = await apiClient.post<Peticao>('/peticoes', payload)
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
      tipoPeticaoPje?: string
      descricaoPje?: string
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

/** Retorna lista de tipos de documento do PJe para o tribunal informado (capturada via RPA) */
export function useTiposDocumentoPje(tribunalId: string | undefined) {
  return useQuery({
    queryKey: ['tipos-documento-pje', tribunalId],
    queryFn: async (): Promise<string[]> => {
      const { data } = await apiClient.get<{ tipos: string[] }>('/peticoes/tipos-documento', {
        params: { tribunal_id: tribunalId },
      })
      return data.tipos
    },
    enabled: !!tribunalId,
    staleTime: 1000 * 60 * 60, // 1h — lista não muda frequentemente
  })
}

export interface TipoDocumentoTPU {
  cod_item: number
  nome: string
  descricao: string
}

/** Retorna tipos de documento da Tabela Processual Unificada (CNJ oficial) */
export function useTiposDocumentoTPU(tribunalId: string | undefined) {
  return useQuery({
    queryKey: ['tipos-documento-tpu', tribunalId],
    queryFn: async (): Promise<TipoDocumentoTPU[]> => {
      const { data } = await apiClient.get<{ tipos: TipoDocumentoTPU[] }>(
        '/peticoes/tipos-documento-tpu',
        { params: { tribunal_id: tribunalId } },
      )
      return data.tipos
    },
    enabled: !!tribunalId,
    staleTime: 1000 * 60 * 60 * 24, // 24h — TPU muda raramente
    retry: 1,
  })
}
