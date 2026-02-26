import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'

export interface Client {
  id: string
  tenant_id: string
  full_name: string
  cpf_cnpj?: string
  email?: string
  phone?: string
  status: string
  health_score?: number
  active_cases_count?: number
  total_cases_count?: number
  last_interaction?: string
  last_interaction_type?: string
  alerts?: any[]
  created_at: string
  updated_at: string
}

export function useClients() {
  return useQuery({
    queryKey: ['clients'],
    queryFn: async () => {
      const response = await apiClient.get<Client[]>('/clients')
      return response.data
    },
  })
}

export function useClient(id: string) {
  return useQuery({
    queryKey: ['clients', id],
    queryFn: async () => {
      const response = await apiClient.get<Client>(`/clients/${id}`)
      return response.data
    },
    enabled: !!id,
  })
}

export function useCreateClient() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (data: Partial<Client>) => {
      const response = await apiClient.post<Client>('/clients', data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clients'] })
    },
  })
}

export function useUpdateClient() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<Client> }) => {
      const response = await apiClient.put<Client>(`/clients/${id}`, data)
      return response.data
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['clients'] })
      queryClient.invalidateQueries({ queryKey: ['clients', variables.id] })
    },
  })
}
