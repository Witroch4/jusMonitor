import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'

export interface Process {
  id: string
  tenant_id: string
  client_id: string
  cnj_number: string
  court?: string
  case_type?: string
  status?: string
  last_movement_date?: string
  next_deadline?: string
  monitoring_enabled: boolean
  created_at: string
  updated_at: string
}

export function useProcesses(filters?: { client_id?: string }) {
  return useQuery({
    queryKey: ['processes', filters],
    queryFn: async () => {
      const response = await apiClient.get<Process[]>('/processes', { params: filters })
      return response.data
    },
  })
}

export function useProcess(id: string) {
  return useQuery({
    queryKey: ['processes', id],
    queryFn: async () => {
      const response = await apiClient.get<Process>(`/processes/${id}`)
      return response.data
    },
    enabled: !!id,
  })
}

export function useCreateProcess() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (data: Partial<Process>) => {
      const response = await apiClient.post<Process>('/processes', data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['processes'] })
    },
  })
}
