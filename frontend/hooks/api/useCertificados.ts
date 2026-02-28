import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchCertificados,
  testarCertificado,
  uploadCertificado,
  removerCertificado,
} from '@/lib/mock/certificados-data'

export function useCertificados() {
  return useQuery({
    queryKey: ['certificados'],
    queryFn: fetchCertificados,
  })
}

export function useTestarCertificado() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => testarCertificado(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['certificados'] })
    },
  })
}

export function useUploadCertificado() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: { nomeAmigavel: string }) => uploadCertificado(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['certificados'] })
    },
  })
}

export function useRemoverCertificado() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => removerCertificado(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['certificados'] })
    },
  })
}
