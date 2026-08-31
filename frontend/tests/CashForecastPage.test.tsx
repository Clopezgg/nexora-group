import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

function stubFetch(hasAlert: boolean) {
  const weeks = Array.from({ length: 13 }, (_, i) => ({
    weekIndex: i,
    weekStart: `2026-09-0${(i % 9) + 1}`,
    weekEnd: `2026-09-0${(i % 9) + 1}`,
    inflows: 0,
    outflows: i === 2 && hasAlert ? 5000 : 0,
    net: i === 2 && hasAlert ? -5000 : 0,
    projectedBalance: hasAlert && i >= 2 ? -4000 : 1000,
  }))
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
      if (url.includes('/financial-control/cash-forecast')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            asOf: '2026-08-31',
            currencyCode: 'HNL',
            openingBalance: 1000,
            weeks,
            minProjectedBalance: hasAlert ? -4000 : 1000,
            firstNegativeWeekIndex: hasAlert ? 2 : null,
            hasLiquidityAlert: hasAlert,
          }),
        } as Response)
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => ({}) } as Response)
    }),
  )
}

describe('CashForecastPage', () => {
  it('renders 13 weeks and a liquidity alert when the balance goes negative', async () => {
    stubFetch(true)
    render(renderApp('/finanzas/flujo-13-semanas'))

    expect(await screen.findByRole('heading', { name: 'Forecast de caja · 13 semanas' })).toBeInTheDocument()
    expect(await screen.findByText(/Alerta de liquidez · descubierto en la semana 3/)).toBeInTheDocument()
    expect(screen.getAllByText(/S\d+ ·/).length).toBe(13)
  })

  it('shows no alert when the projected balance stays positive', async () => {
    stubFetch(false)
    render(renderApp('/finanzas/flujo-13-semanas'))
    expect(await screen.findByText('Sin descubierto proyectado en el horizonte')).toBeInTheDocument()
  })
})
