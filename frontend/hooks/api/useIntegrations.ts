import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiClient } from '@/lib/api-client'
import type { InstagramStatus } from '@/types'

export function useInstagramIntegration() {
  return useQuery({
    queryKey: ['integrations', 'instagram'],
    queryFn: async () => {
      const res = await apiClient.get<InstagramStatus>('/integrations/instagram')
      return res.data
    },
    staleTime: 60 * 1000,
  })
}

export function useDisconnectInstagram() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async () => {
      await apiClient.delete('/integrations/instagram')
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['integrations', 'instagram'] })
    },
  })
}
