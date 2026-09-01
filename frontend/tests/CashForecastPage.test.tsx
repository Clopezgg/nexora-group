import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
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
  const actualWeeks = Array.from({ length: 13 }, (_, i) => ({
    weekIndex: i,
    weekStart: `2026-06-0${(i % 9) + 1}`,
    weekEnd: `2026-06-0${(i % 9) + 1}`,
    inflows: i === 12 ? 10000 : 0,
    outflows: 0,
    net: i === 12 ? 10000 : 0,
    closingBalance: i === 12 ? 10000 : 0,
    byCategory: {},
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
      if (url.includes('/financial-control/cash-flow-actual')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            asOf: '2026-08-31',
            currencyCode: 'HNL',
            openingBalance: 0,
            closingBalance: 10000,
            totalInflows: 10000,
            totalOutflows: 0,
            inflowByCategory: { 'Aportes de capital': 10000 },
            outflowByCategory: {},
            weeks: actualWeeks,
          }),
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
  it('defaults to the realized 13-week cash flow', async () => {
    stubFetch(false)
    render(renderApp('/finanzas/flujo-13-semanas'))

    expect(await screen.findByRole('heading', { name: 'Flujo de caja · 13 semanas' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Realizado' })).toHaveAttribute('aria-selected', 'true')
    expect(await screen.findByText(/Entradas L\s?10,000/)).toBeInTheDocument()
    expect(screen.getAllByText(/S\d+ ·/).length).toBe(13)
  })

  it('shows the projected forecast with a liquidity alert when switched to Proyectado', async () => {
    stubFetch(true)
    render(renderApp('/finanzas/flujo-13-semanas'))

    await userEvent.click(await screen.findByRole('tab', { name: 'Proyectado' }))
    expect(await screen.findByText(/Alerta de liquidez · descubierto en la semana 3/)).toBeInTheDocument()
  })

  it('shows no alert when the projected balance stays positive', async () => {
    stubFetch(false)
    render(renderApp('/finanzas/flujo-13-semanas'))
    await userEvent.click(await screen.findByRole('tab', { name: 'Proyectado' }))
    expect(await screen.findByText('Sin descubierto proyectado en el horizonte')).toBeInTheDocument()
  })
})
