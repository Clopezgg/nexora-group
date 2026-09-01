import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

function stubFetch(hasAlert: boolean) {
  const forecastWeeks = Array.from({ length: 13 }, (_, i) => ({
    weekIndex: i,
    weekStart: '2026-09-01',
    weekEnd: '2026-09-07',
    inflows: 0,
    outflows: i === 2 && hasAlert ? 5000 : 0,
    net: i === 2 && hasAlert ? -5000 : 0,
    projectedBalance: hasAlert && i >= 2 ? -4000 : 1000,
  }))
  const periods = [
    { index: 0, periodStart: '2026-06-01', periodEnd: '2026-06-30', label: 'Junio 2026', inflows: 0, outflows: 0, net: 0, closingBalance: 0, movementCount: 0, byCategory: {} },
    { index: 1, periodStart: '2026-07-01', periodEnd: '2026-07-31', label: 'Julio 2026', inflows: 5000, outflows: 0, net: 5000, closingBalance: 5000, movementCount: 1, byCategory: { 'Aportes de capital': 5000 } },
    { index: 2, periodStart: '2026-08-01', periodEnd: '2026-08-31', label: 'Agosto 2026', inflows: 8000, outflows: 2000, net: 6000, closingBalance: 11000, movementCount: 2, byCategory: {} },
  ]
  vi.stubGlobal(
    'fetch',
    vi.fn().mockImplementation((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/auth/me')) {
        return Promise.resolve({
          ok: true, status: 200,
          json: async () => ({ id: 'u1', email: 'admin@nexora.group', fullName: 'Admin', roles: ['Administrator'], permissions: ['treasury.account:read'] }),
        } as Response)
      }
      if (url.includes('/master-data/companies')) {
        return Promise.resolve({
          ok: true, status: 200,
          json: async () => [{ id: 'c1', name: 'Constructora Nexora', functionalCurrencyCode: 'HNL' }],
        } as Response)
      }
      if (url.includes('/cash-flow-actual/movements')) {
        return Promise.resolve({
          ok: true, status: 200,
          json: async () => [
            { documentId: 'd1', documentNumber: 'REM-2026-0007', effectiveDate: '2026-07-10', direction: 'INFLOW', category: 'Aportes de capital', amount: 5000, concept: 'Aporte socio', counterparty: null },
          ],
        } as Response)
      }
      if (url.includes('/cash-flow-actual/series')) {
        return Promise.resolve({
          ok: true, status: 200,
          json: async () => ({
            dateFrom: '2026-06-01', dateTo: '2026-08-31', granularity: 'month', currencyCode: 'HNL',
            openingBalance: 0, closingBalance: 11000, totalInflows: 13000, totalOutflows: 2000,
            inflowByCategory: { 'Aportes de capital': 13000 }, outflowByCategory: { 'Gastos pagados': 2000 },
            periods,
          }),
        } as Response)
      }
      if (url.includes('/cash-flow-actual')) {
        return Promise.resolve({
          ok: true, status: 200,
          json: async () => ({
            asOf: '2026-08-31', currencyCode: 'HNL', openingBalance: 0, closingBalance: 10000,
            totalInflows: 10000, totalOutflows: 0, inflowByCategory: {}, outflowByCategory: {},
            weeks: [],
          }),
        } as Response)
      }
      if (url.includes('/financial-control/cash-forecast')) {
        return Promise.resolve({
          ok: true, status: 200,
          json: async () => ({
            asOf: '2026-08-31', currencyCode: 'HNL', openingBalance: 1000, weeks: forecastWeeks,
            minProjectedBalance: hasAlert ? -4000 : 1000, firstNegativeWeekIndex: hasAlert ? 2 : null,
            hasLiquidityAlert: hasAlert,
          }),
        } as Response)
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => ({}) } as Response)
    }),
  )
}

describe('CashForecastPage', () => {
  it('shows the realized cash flow with a real-date range and movement drill-down', async () => {
    stubFetch(false)
    const user = userEvent.setup()
    render(renderApp('/finanzas/flujo-13-semanas'))

    expect(await screen.findByRole('heading', { name: 'Flujo de caja' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Realizado' })).toHaveAttribute('aria-selected', 'true')
    // Selector de rango real, no S1..S13.
    expect(screen.getByRole('button', { name: '3M' })).toBeInTheDocument()
    expect(screen.getByLabelText('Agrupación')).toBeInTheDocument()
    // Etiquetas de calendario reales.
    expect(await screen.findByText('Julio 2026')).toBeInTheDocument()
    expect(screen.getByText('Agosto 2026')).toBeInTheDocument()
    expect(screen.getByText(/Entradas L\s?13,000/)).toBeInTheDocument()
    // Nunca "S1".."S13" como etiqueta principal (§5/§10).
    expect(screen.queryByText(/^S1[0-3]$/)).not.toBeInTheDocument()
    expect(screen.queryByText(/^S[1-9]$/)).not.toBeInTheDocument()

    // Drill-down: click en el contador de movimientos abre el detalle.
    const julioRow = screen.getByText('Julio 2026').closest('tr') as HTMLElement
    await user.click(within(julioRow).getByRole('button', { name: '1' }))
    expect(await screen.findByText('REM-2026-0007')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /Movimientos · Julio 2026/ })).toBeInTheDocument()
  })

  it('shows the projected forecast with a liquidity alert when switched to Proyectado', async () => {
    stubFetch(true)
    render(renderApp('/finanzas/flujo-13-semanas'))
    await userEvent.click(await screen.findByRole('tab', { name: 'Proyectado' }))
    const alert = await screen.findByText(/Alerta de liquidez/)
    expect(alert).toBeInTheDocument()
    // Fecha de calendario real en la alerta, nunca "S3".
    expect(alert.textContent).not.toMatch(/\bS\d+\b/)
    expect(alert.textContent).toMatch(/sep/)
  })

  it('shows no liquidity alert when the projected balance stays positive', async () => {
    stubFetch(false)
    render(renderApp('/finanzas/flujo-13-semanas'))
    await userEvent.click(await screen.findByRole('tab', { name: 'Proyectado' }))
    // El resumen proyectado se muestra sin alerta de liquidez.
    expect(await screen.findByText(/Saldo inicial/)).toBeInTheDocument()
    expect(screen.queryByText(/Alerta de liquidez/)).not.toBeInTheDocument()
  })
})
