import { apiFetch } from './httpClient'

export interface UserPreferences {
  themeId: string | null
  density: string | null
}

export const preferencesService = {
  get: () => apiFetch<UserPreferences>('/me/preferences'),
  update: (body: { themeId: string | null; density: string | null }) =>
    apiFetch<UserPreferences>('/me/preferences', {
      method: 'PUT',
      body: JSON.stringify(body),
    }),
}
