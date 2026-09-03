import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, expect, it, vi } from 'vitest'
import { BuildInfoCard } from '../src/features/settings/BuildInfoCard'

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{ui}</QueryClientProvider>
}

describe('BuildInfoCard (ORDEN MAESTRA §21)', () => {
  it('shows the real backend build metadata from GET /api/version, abbreviated SHA', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((input: RequestInfo | URL) => {
        const url = String(input)
        if (url.includes('/version')) {
          return Promise.resolve({
            ok: true,
            status: 200,
            json: async () => ({
              gitSha: 'fc0b2d9f166a70d8784f80c682049c80f8a66e8b',
              buildTime: '2026-09-03T02:12:58Z',
              environment: 'production',
            }),
          } as Response)
        }
        return Promise.resolve({ ok: true, status: 200, json: async () => ({}) } as Response)
      }),
    )

    render(wrap(<BuildInfoCard />))

    expect(await screen.findByText('fc0b2d9')).toBeInTheDocument()
    expect(screen.getByText('production')).toBeInTheDocument()
    expect(screen.queryByText('fc0b2d9f166a70d8784f80c682049c80f8a66e8b')).not.toBeInTheDocument()
  })

  it('never crashes the page when /api/version returns an unexpected shape', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(() => Promise.resolve({ ok: true, status: 200, json: async () => ({}) } as Response)),
    )

    const { container } = render(wrap(<BuildInfoCard />))

    // No debe lanzar ni quedar en un estado roto -- simplemente no muestra nada útil.
    await waitFor(() => expect(container.textContent).toBe(''))
  })
})
