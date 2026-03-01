import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import type { CertificadoDigital } from '@/types/peticoes'

interface CertificadoListResponse {
  items: CertificadoDigital[]
  total: number
}

interface TesteResponse {
  sucesso: boolean
  mensagem: string
}

export function useCertificados() {
  return useQuery({
    queryKey: ['certificados'],
    queryFn: async (): Promise<CertificadoDigital[]> => {
      const { data } = await apiClient.get<CertificadoListResponse>('/certificados')
      return data.items
    },
  })
}

export function useTestarCertificado() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (id: string): Promise<TesteResponse> => {
      const { data } = await apiClient.post<TesteResponse>(`/certificados/${id}/testar`)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['certificados'] })
    },
  })
}

export function useUploadCertificado() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (params: {
      arquivo: File
      nome: string
      senhaPfx: string
    }): Promise<CertificadoDigital> => {
      const formData = new FormData()
      formData.append('arquivo', params.arquivo)
      formData.append('nome', params.nome)
      formData.append('senha_pfx', params.senhaPfx)

      const { data } = await apiClient.post<CertificadoDigital>('/certificados', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['certificados'] })
    },
  })
}

export function useRemoverCertificado() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (id: string): Promise<void> => {
      await apiClient.delete(`/certificados/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['certificados'] })
    },
  })
}
