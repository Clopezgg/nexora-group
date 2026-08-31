import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

describe('VoucherVerificationPage (público)', () => {
  it('muestra un comprobante válido con datos mínimos y sin auth', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((input: RequestInfo | URL) => {
        const url = String(input)
        if (url.includes('/verificar/comprobante/')) {
          return Promise.resolve({
            ok: true,
            status: 200,
            headers: new Headers(),
            json: async () => ({
              verified: true,
              documentNumber: 'REM-2026-000022',
              company: 'NEXORA GROUP',
              beneficiary: 'Constructora Nexora',
              issuedOn: '2026-08-31',
              amount: '18662.00',
              currency: 'HNL',
              status: 'posted',
              verificationCode: 'AB12CD34EF56',
            }),
          } as Response)
        }
        return Promise.resolve({ ok: true, status: 200, headers: new Headers(), json: async () => ({}) } as Response)
      }),
    )

    render(renderApp('/verificar/comprobante/tok-123'))

    expect(await screen.findByText(/Comprobante válido/i)).toBeInTheDocument()
    expect(screen.getByText('REM-2026-000022')).toBeInTheDocument()
    expect(screen.getByText(/L\s*18,662\.00/)).toBeInTheDocument()
    expect(screen.getByText('AB12CD34EF56')).toBeInTheDocument()
    // No hay login: la página pública se renderiza directamente.
    expect(screen.queryByRole('heading', { name: /bienvenido a nexora/i })).not.toBeInTheDocument()
  })

  it('muestra "no verificado" cuando el token no existe', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        headers: new Headers(),
        json: async () => ({ detail: 'No encontramos un comprobante con ese código de verificación.' }),
      } as Response),
    )

    render(renderApp('/verificar/comprobante/malo'))
    expect(await screen.findByText(/Comprobante no verificado/i)).toBeInTheDocument()
  })
})
