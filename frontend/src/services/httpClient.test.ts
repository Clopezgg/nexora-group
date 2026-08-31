import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, apiFetch, friendlyApiMessage } from './httpClient'

describe('httpClient', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('dispatches nexora:session-expired on a 401 from a data endpoint', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ error: { message: 'no session' } }), {
          status: 401,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    )
    const listener = vi.fn()
    window.addEventListener('nexora:session-expired', listener)

    await expect(apiFetch('/master-data/companies')).rejects.toBeInstanceOf(ApiError)
    expect(listener).toHaveBeenCalledTimes(1)

    window.removeEventListener('nexora:session-expired', listener)
  })

  it('does NOT dispatch nexora:session-expired for the auth probe itself', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response('{}', { status: 401, headers: { 'Content-Type': 'application/json' } })),
    )
    const listener = vi.fn()
    window.addEventListener('nexora:session-expired', listener)

    await expect(apiFetch('/auth/me')).rejects.toBeInstanceOf(ApiError)
    expect(listener).not.toHaveBeenCalled()

    window.removeEventListener('nexora:session-expired', listener)
  })

  it('surfaces the backend correlation id and a friendly message on 5xx', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ error: { message: 'boom', correlationId: 'abc-123' } }), {
          status: 500,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    )
    try {
      await apiFetch('/dashboard/summary')
      throw new Error('expected apiFetch to reject')
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError)
      expect((error as ApiError).correlationId).toBe('abc-123')
      expect(friendlyApiMessage(error)).toContain('abc-123')
    }
  })

  it('maps statuses to distinct human messages', () => {
    expect(friendlyApiMessage(new ApiError('x', 401))).toMatch(/sesión expiró/i)
    expect(friendlyApiMessage(new ApiError('x', 403))).toMatch(/permiso/i)
    expect(friendlyApiMessage(new ApiError('x', 404))).toMatch(/no existe/i)
    expect(friendlyApiMessage(new TypeError('network'))).toMatch(/conexión/i)
  })

  it('accepts a same-origin "/api" base URL in a production build (first-party auth)', async () => {
    vi.resetModules()
    vi.stubEnv('PROD', true)
    vi.stubEnv('VITE_API_BASE_URL', '/api')
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response('[]', { status: 200, headers: { 'Content-Type': 'application/json' } })),
    )
    const mod = await import('./httpClient')
    await mod.apiFetch('/master-data/companies')
    expect(vi.mocked(fetch).mock.calls[0]?.[0]).toBe('/api/master-data/companies')
    vi.unstubAllEnvs()
    vi.resetModules()
  })

  it('rejects a cleartext absolute base URL in a production build', async () => {
    vi.resetModules()
    vi.stubEnv('PROD', true)
    vi.stubEnv('VITE_API_BASE_URL', 'http://insecure.example/api')
    await expect(import('./httpClient')).rejects.toThrow(/HTTPS/i)
    vi.unstubAllEnvs()
    vi.resetModules()
  })
})
