import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

function stubFetch() {
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
      if (url.includes('/financial-control/daily-status')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            companyId: 'c1',
            asOf: '2026-08-31',
            currencyCode: 'HNL',
            fiscalPeriodLabel: null,
            fiscalPeriodStatus: null,
            kpis: [
              {
                key: 'cash_position',
                label: 'Posición de caja y bancos',
                value: 'L 5,000.00',
                numeric: 5000,
                severity: 'ok',
                hint: 'Saldo real consolidado.',
                route: '/finanzas/tesoreria',
              },
              {
                key: 'ap_overdue',
                label: 'Cuentas por pagar vencidas',
                value: 'L 1,200.00',
                numeric: 1200,
                severity: 'critical',
                hint: 'Saldo vencido.',
                route: '/finanzas/cuentas-por-pagar',
              },
            ],
          }),
        } as Response)
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => ({}) } as Response)
    }),
  )
}

describe('FinancialControlCenterPage', () => {
  it('renders the daily financial status with actionable, drillable KPIs', async () => {
    stubFetch()
    render(renderApp('/finanzas/control'))

    expect(await screen.findByText('Centro de Control Financiero')).toBeInTheDocument()
    expect(await screen.findByText('L 5,000.00')).toBeInTheDocument()
    expect(screen.getByText('Cuentas por pagar vencidas')).toBeInTheDocument()
    expect(screen.getByText(/Estado financiero del día · 2026-08-31/)).toBeInTheDocument()

    const drill = screen.getAllByRole('link', { name: /ver detalle/i })
    expect(drill.length).toBeGreaterThan(0)
    expect(drill[0]).toHaveAttribute('href', '/finanzas/tesoreria')
  })
})
