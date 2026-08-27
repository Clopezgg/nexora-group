import { QueryClient } from '@tanstack/react-query'

function isTransientError(error: Error): boolean {
  const status = (error as { status?: number }).status
  if (status === undefined) return true
  return status >= 500 || status === 0
}

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error) => {
        if (failureCount >= 2) return false
        return isTransientError(error)
      },
      // Keep recently loaded ERP data warm across short navigation bursts.
      // Mutations still invalidate their affected queries immediately, so this
      // avoids redundant GETs without hiding newly written financial data.
      staleTime: 60_000,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: false,
    },
  },
})
