import { createContext, useContext } from 'react'
import type { CurrentUser, LoginPayload } from '../../types/auth'

export interface AuthContextValue {
  user: CurrentUser | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (payload: LoginPayload) => Promise<CurrentUser>
  loginError: string | null
  isLoggingIn: boolean
  logout: () => void
}

export const AuthContext = createContext<AuthContextValue | null>(null)

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
