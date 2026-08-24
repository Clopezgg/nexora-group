import { apiFetch } from './httpClient'
import type { ActiveUIContext } from '../types/context'

export const contextService = {
  get: () => apiFetch<ActiveUIContext>('/context'),
  set: (activeProjectId: string | null) =>
    apiFetch<ActiveUIContext>('/context', {
      method: 'PUT',
      body: JSON.stringify({ activeProjectId }),
    }),
}
