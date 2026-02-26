import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'

export interface Lead {
  id: string
  tenant_id: string
  full_name: string
  phone?: string
  email?: string
  source: string
  stage: string
  score: number
  status: string
  created_at: string
  updated_at: string
}

export function useLeads(filters?: { stage?: string; status?: string }) {
  return useQuery({
    queryKey: ['leads', filters],
    queryFn: async () => {
      const response = await apiClient.get<Lead[]>('/leads', { params: filters })
      return response.data
    },
  })
}

export function useLead(id: string) {
  return useQuery({
    queryKey: ['leads', id],
    queryFn: async () => {
      const response = await apiClient.get<Lead>(`/leads/${id}`)
      return response.data
    },
    enabled: !!id,
  })
}

export function useCreateLead() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (data: Partial<Lead>) => {
      const response = await apiClient.post<Lead>('/leads', data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] })
    },
  })
}

export function useUpdateLeadStage() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ id, stage }: { id: string; stage: string }) => {
      const response = await apiClient.patch<Lead>(`/leads/${id}/stage`, { stage })
      return response.data
    },
    onMutate: async ({ id, stage }) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['leads'] })

      // Snapshot previous value
      const previousLeads = queryClient.getQueryData<Lead[]>(['leads'])

      // Optimistically update
      if (previousLeads) {
        queryClient.setQueryData<Lead[]>(
          ['leads'],
          previousLeads.map((lead) =>
            lead.id === id ? { ...lead, stage } : lead
          )
        )
      }

      return { previousLeads }
    },
    onError: (err, variables, context) => {
      // Rollback on error
      if (context?.previousLeads) {
        queryClient.setQueryData(['leads'], context.previousLeads)
      }
    },
    onSettled: () => {
      // Refetch after mutation
      queryClient.invalidateQueries({ queryKey: ['leads'] })
    },
  })
}
