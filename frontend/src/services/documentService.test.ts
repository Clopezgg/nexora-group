import { afterEach, describe, expect, it, vi } from 'vitest'
import { documentService } from './documentService'

describe('documentService evidence download', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('fetches the authenticated private endpoint and returns bytes with a safe filename', async () => {
    const payload = new Blob(['private bytes'], { type: 'application/pdf' })
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(payload, {
        status: 200,
        headers: {
          'Content-Type': 'application/pdf',
          'Content-Disposition': "attachment; filename*=UTF-8''..%2Fplano%20final.pdf",
        },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const result = await documentService.downloadEvidence('evidence-1')

    expect(fetchMock).toHaveBeenCalledWith('/api/evidence/evidence-1/download', {
      credentials: 'include',
      headers: { Accept: 'application/octet-stream,*/*' },
    })
    expect(await result.blob.text()).toBe('private bytes')
    expect(result.filename).toBe('plano final.pdf')
  })

  it('propagates the standard API error for unavailable storage', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ error: { message: 'Storage no configurado' } }), {
          status: 503,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    )

    await expect(documentService.downloadEvidence('evidence-2')).rejects.toMatchObject({
      status: 503,
      message: 'Storage no configurado',
    })
  })
})
