import { apiFetch } from './httpClient'
import type { CurrentUser, LoginPayload } from '../types/auth'

export const authService = {
  login: (payload: LoginPayload) =>
    apiFetch<CurrentUser>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  logout: () => apiFetch<void>('/auth/logout', { method: 'POST' }),
  me: () => apiFetch<CurrentUser>('/auth/me'),
}
