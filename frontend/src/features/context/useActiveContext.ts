import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { contextService } from '../../services/contextService'
import type { ActiveUIContext } from '../../types/context'

const CONTEXT_QUERY_KEY = ['ui-context'] as const

export function useActiveContext() {
  const queryClient = useQueryClient()

  const query = useQuery<ActiveUIContext>({
    queryKey: CONTEXT_QUERY_KEY,
    queryFn: contextService.get,
  })

  const mutation = useMutation({
    mutationFn: (activeProjectId: string | null) => contextService.set(activeProjectId),
    onSuccess: (data) => {
      queryClient.setQueryData(CONTEXT_QUERY_KEY, data)
    },
  })

  return {
    context: query.data ?? { activeProjectId: null, activeProjectName: null },
    isLoading: query.isLoading,
    setActiveProject: (activeProjectId: string | null) => mutation.mutate(activeProjectId),
  }
}
