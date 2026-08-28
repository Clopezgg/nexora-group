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

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  // Un body FormData (subida de archivos, ver documentService.uploadEvidence)
  // nunca debe forzar Content-Type: application/json -- el navegador debe
  // fijar el `multipart/form-data; boundary=...` correcto por sí mismo.
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
    let message = `Error ${response.status}`
    try {
      const body = await response.json()
      // `detail` es el formato de FastAPI/HTTPException; `error.message` es
      // el estándar NXR-* (orden maestra §108) que usan los endpoints de
      // dominio (Track A en adelante). Se soportan ambos.
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

  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}
