import type { ReactNode } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { authService } from '../../services/authService'
import { ApiError } from '../../services/httpClient'
import type { CurrentUser } from '../../types/auth'
import { AuthContext, type AuthContextValue } from './auth-context'

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()

  const meQuery = useQuery<CurrentUser | null>({
    queryKey: ['auth', 'me'],
    queryFn: async () => {
      try {
        return await authService.me()
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          return null
        }
        throw error
      }
    },
    retry: false,
  })

  const loginMutation = useMutation({
    mutationFn: authService.login,
    onSuccess: (user) => {
      queryClient.setQueryData(['auth', 'me'], user)
    },
  })

  const logoutMutation = useMutation({
    mutationFn: authService.logout,
    onSuccess: () => {
      queryClient.setQueryData(['auth', 'me'], null)
    },
  })

  const value: AuthContextValue = {
    user: meQuery.data ?? null,
    isLoading: meQuery.isLoading,
    isAuthenticated: Boolean(meQuery.data),
    login: (payload) => loginMutation.mutateAsync(payload),
    loginError:
      loginMutation.error instanceof ApiError ? loginMutation.error.message : null,
    isLoggingIn: loginMutation.isPending,
    logout: () => logoutMutation.mutate(),
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
