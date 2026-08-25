export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api'

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: 'include',
    ...options,
    headers: {
      'Content-Type': 'application/json',
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
    throw new ApiError(message, response.status)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}
