export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api'
const EDIT_CAPABILITY_KEY = 'nexora.edit-access.capability'
const EDIT_EXPIRY_KEY = 'nexora.edit-access.expires-at'

function getEditCapability(): string | null {
  if (typeof window === 'undefined') return null
  try {
    const capability = window.sessionStorage.getItem(EDIT_CAPABILITY_KEY)
    const expiresAt = Number(window.sessionStorage.getItem(EDIT_EXPIRY_KEY) ?? '0')
    if (!capability || !expiresAt || Date.now() >= expiresAt * 1000) {
      window.sessionStorage.removeItem(EDIT_CAPABILITY_KEY)
      window.sessionStorage.removeItem(EDIT_EXPIRY_KEY)
      return null
    }
    return capability
  } catch {
    return null
  }
}

export function storeEditCapability(capability: string, expiresAt: number) {
  if (typeof window === 'undefined') return
  try {
    window.sessionStorage.setItem(EDIT_CAPABILITY_KEY, capability)
    window.sessionStorage.setItem(EDIT_EXPIRY_KEY, String(expiresAt))
  } catch {
    // Session storage can be disabled by browser policy; the backend remains authoritative.
  }
  window.dispatchEvent(new CustomEvent('nexora:edit-access-changed'))
}

export function clearEditCapability() {
  if (typeof window === 'undefined') return
  try {
    window.sessionStorage.removeItem(EDIT_CAPABILITY_KEY)
    window.sessionStorage.removeItem(EDIT_EXPIRY_KEY)
  } catch {
    // no-op
  }
  window.dispatchEvent(new CustomEvent('nexora:edit-access-changed'))
}

export function hasEditCapability(): boolean {
  return Boolean(getEditCapability())
}

async function throwApiError(response: Response): Promise<never> {
  let message = `Error ${response.status}`
  try {
    const body = await response.json()
    message = body.detail ?? body.error?.message ?? message
  } catch {
    // response without JSON body
  }
  if (response.status === 428 && typeof window !== 'undefined') {
    clearEditCapability()
    window.dispatchEvent(new CustomEvent('nexora:edit-access-required'))
  }
  throw new ApiError(message, response.status)
}

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  // A FormData body (evidence uploads) must not force application/json; the
  // browser owns the multipart boundary.
  const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData
  const method = (options.method ?? 'GET').toUpperCase()
  const editCapability = ['PUT', 'PATCH', 'DELETE'].includes(method) ? getEditCapability() : null
  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: 'include',
    ...options,
    headers: {
      ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
      ...(editCapability ? { 'X-Nexora-Edit-Access': editCapability } : {}),
      ...options.headers,
    },
  })

  if (!response.ok) {
    return throwApiError(response)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}

export interface ApiDownload {
  blob: Blob
  filename: string | null
}

function downloadFilename(response: Response): string | null {
  const disposition = response.headers.get('content-disposition')
  if (!disposition) return null

  const encoded = disposition.match(/filename\*=UTF-8''([^;]+)/i)?.[1]
  if (encoded) {
    try {
      return decodeURIComponent(encoded)
    } catch {
      return encoded
    }
  }

  const quoted = disposition.match(/filename="([^"]+)"/i)?.[1]
  return quoted ?? null
}

export async function apiFetchBlob(path: string): Promise<ApiDownload> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: 'include',
    headers: { Accept: 'application/octet-stream,*/*' },
  })

  if (!response.ok) {
    return throwApiError(response)
  }

  return {
    blob: await response.blob(),
    filename: downloadFilename(response),
  }
}
