import { apiFetch, clearEditCapability, hasEditCapability, storeEditCapability } from './httpClient'

interface VerifyResponse {
  capability: string
  expiresAt: number
}

export const editAccessService = {
  async unlock(token: string) {
    const response = await apiFetch<VerifyResponse>('/edit-access/verify', {
      method: 'POST',
      body: JSON.stringify({ token }),
    })
    storeEditCapability(response.capability, response.expiresAt)
    return response
  },
  lock() {
    clearEditCapability()
  },
  isUnlocked() {
    return hasEditCapability()
  },
}
