export class ApiError extends Error {
  status: number
  correlationId: string | null
  /** Standard API error code (`error.code`), e.g. "NXR-CONTRACT-GUARD-001",
   *  so a caller can branch on a specific domain condition. */
  code: string | null
  constructor(
    message: string,
    status: number,
    correlationId: string | null = null,
    code: string | null = null,
  ) {
    super(message)
    this.status = status
    this.correlationId = correlationId
    this.code = code
  }
}

/** Human-facing message by HTTP status, so a page never shows a bare
 *  "Error 500" and a dropped session is not mistaken for a real failure. */
export function friendlyApiMessage(error: unknown): string {
  if (!(error instanceof ApiError)) return 'No se pudo contactar el servidor. Revisa tu conexión.'
  switch (error.status) {
    case 401:
      return 'Tu sesión expiró. Inicia sesión nuevamente.'
    case 403:
      return 'No tienes permiso para ver esta información.'
    case 404:
      return 'El recurso solicitado no existe.'
    case 409:
      return error.message || 'La operación entra en conflicto con el estado actual.'
    case 422:
      return error.message || 'Los datos enviados no son válidos.'
    default:
      return error.status >= 500
        ? `Error interno del servidor${error.correlationId ? ` (ref. ${error.correlationId})` : ''}.`
        : error.message || `Error ${error.status}`
  }
}

function resolveApiBaseUrl(): string {
  const configured = import.meta.env.VITE_API_BASE_URL?.trim()

  if (import.meta.env.PROD) {
    if (!configured) {
      throw new Error('VITE_API_BASE_URL is required for the Nexora production build')
    }
    // Production must be first-party: either a same-origin absolute path
    // (served by the Static Web Apps linked backend as `/api`, which keeps
    // the session cookie first-party and works in Safari/WebKit ITP), or an
    // absolute HTTPS origin. A cleartext or relative-without-leading-slash
    // value is rejected.
    const isSameOriginPath = configured.startsWith('/') && !configured.startsWith('//')
    if (!isSameOriginPath) {
      let parsed: URL
      try {
        parsed = new URL(configured)
      } catch {
        throw new Error(
          'VITE_API_BASE_URL must be a same-origin path (e.g. "/api") or an absolute HTTPS URL in production',
        )
      }
      if (parsed.protocol !== 'https:') {
        throw new Error('VITE_API_BASE_URL must use HTTPS in production')
      }
    }
  }

  return (configured || '/api').replace(/\/+$/, '')
}

const API_BASE_URL = resolveApiBaseUrl()
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

async function throwApiError(response: Response, path: string): Promise<never> {
  let message = `Error ${response.status}`
  let correlationId: string | null =
    response.headers.get('x-correlation-id') ?? response.headers.get('x-request-id')
  let code: string | null = null
  try {
    const body = await response.json()
    message = body.detail ?? body.error?.message ?? message
    correlationId = body.error?.correlationId ?? correlationId
    code = body.error?.code ?? null
  } catch {
    // response without JSON body
  }
  if (response.status === 428 && typeof window !== 'undefined') {
    clearEditCapability()
    window.dispatchEvent(new CustomEvent('nexora:edit-access-required'))
  }
  // A 401 on any endpoint other than the session probe itself means the
  // session is gone (expired, revoked, or — historically — a cross-site
  // cookie the browser refused to send). Signal the app so it shows the
  // login screen instead of a scattered "Ocurrió un error" on every page.
  if (
    response.status === 401 &&
    typeof window !== 'undefined' &&
    !path.startsWith('/auth/')
  ) {
    window.dispatchEvent(new CustomEvent('nexora:session-expired'))
  }
  throw new ApiError(message, response.status, correlationId, code)
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
    return throwApiError(response, path)
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

function safeDownloadFilename(filename: string | null): string | null {
  if (!filename) return null
  const normalized = filename.replace(/\\/g, '/').split('/').pop() ?? ''
  const withoutControls = Array.from(normalized)
    .filter((character) => character.charCodeAt(0) > 31 && character.charCodeAt(0) !== 127)
    .join('')
  const safe = withoutControls.trim().replace(/^\.+/, '')
  return safe.slice(0, 255) || null
}

function downloadFilename(response: Response): string | null {
  const disposition = response.headers.get('content-disposition')
  if (!disposition) return null

  const encoded = disposition.match(/filename\*=UTF-8''([^;]+)/i)?.[1]
  if (encoded) {
    try {
      return safeDownloadFilename(decodeURIComponent(encoded))
    } catch {
      return safeDownloadFilename(encoded)
    }
  }

  const quoted = disposition.match(/filename="([^"]+)"/i)?.[1]
  return safeDownloadFilename(quoted ?? null)
}

export async function apiFetchBlob(path: string): Promise<ApiDownload> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: 'include',
    headers: { Accept: 'application/octet-stream,*/*' },
  })

  if (!response.ok) {
    return throwApiError(response, path)
  }

  return {
    blob: await response.blob(),
    filename: downloadFilename(response),
  }
}
