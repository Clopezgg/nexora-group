import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

function stubFetch(exceptionZero: boolean) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockImplementation((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/auth/me')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            id: 'u1',
            email: 'admin@nexora.group',
            fullName: 'Admin',
            roles: ['Administrator'],
            permissions: ['treasury.account:read'],
          }),
        } as Response)
      }
      if (url.includes('/master-data/companies')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => [{ id: 'c1', name: 'Constructora Nexora', functionalCurrencyCode: 'HNL' }],
        } as Response)
      }
      if (url.includes('/financial-control/exceptions')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () =>
            exceptionZero
              ? { exceptionZero: true, total: 0, criticalCount: 0, exceptions: [] }
              : {
                  exceptionZero: false,
                  total: 2,
                  criticalCount: 1,
                  exceptions: [
                    {
                      code: 'DUPLICATE_SUPPLIER_INVOICE',
                      severity: 'critical',
                      title: 'Facturas de proveedor duplicadas',
                      detail: '1 combinación duplicada',
                      count: 1,
                      suggestedAction: 'Anular la factura duplicada',
                      route: '/finanzas/cuentas-por-pagar',
                    },
                    {
                      code: 'AP_OVERDUE',
                      severity: 'warning',
                      title: 'Facturas de proveedor vencidas',
                      detail: '3 facturas vencidas',
                      count: 3,
                      suggestedAction: 'Programar pago',
                      route: '/finanzas/cuentas-por-pagar',
                    },
                  ],
                },
        } as Response)
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => ({}) } as Response)
    }),
  )
}

describe('ExceptionCenterPage', () => {
  it('shows Exception Zero when there is nothing open', async () => {
    stubFetch(true)
    render(renderApp('/finanzas/excepciones'))
    expect(await screen.findByRole('heading', { name: 'Exception Center' })).toBeInTheDocument()
    expect(await screen.findByText('Exception Zero')).toBeInTheDocument()
  })

  it('lists open exceptions with severity, action and a resolve link', async () => {
    stubFetch(false)
    render(renderApp('/finanzas/excepciones'))
    expect(await screen.findByText('Facturas de proveedor duplicadas')).toBeInTheDocument()
    expect(screen.getByText('Crítica')).toBeInTheDocument()
    expect(screen.getByText('Anular la factura duplicada')).toBeInTheDocument()
    expect(screen.getByText(/2 excepción\(es\) · 1 crítica/)).toBeInTheDocument()
    const resolve = screen.getAllByRole('link', { name: /resolver/i })
    expect(resolve[0]).toHaveAttribute('href', '/finanzas/cuentas-por-pagar')
  })
})
