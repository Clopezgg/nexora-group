import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

function stubFetch(canHardClose: boolean) {
  const hardCloseCalls: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn().mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
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
            permissions: ['accounting.closing:read', 'accounting.closing:execute'],
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
      if (url.includes('/fiscal/periods')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => [
            { id: 'p1', fiscalYearId: 'y1', periodNumber: 8, startDate: '2026-08-01', endDate: '2026-08-31', status: 'OPEN' },
          ],
        } as Response)
      }
      if (url.includes('/accounting/closing/checklist')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            periodId: 'p1',
            periodLabel: 'P08',
            periodStatus: 'OPEN',
            canHardClose,
            checks: [
              { key: 'subledger_gl', label: 'Subledgers cuadran contra el GL', passed: canHardClose, blocking: true, detail: canHardClose ? 'Cuadran' : 'Descuadre en AP' },
              { key: 'bank_reconciliation', label: 'Sin líneas bancarias por conciliar', passed: false, blocking: false, detail: '2 líneas UNMATCHED' },
            ],
          }),
        } as Response)
      }
      if (url.includes('/hard-close')) {
        hardCloseCalls.push(String(init?.body))
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            periodId: 'p1',
            periodLabel: 'P08',
            companyId: 'c1',
            closedAt: '2026-08-31T12:00:00Z',
            forced: false,
            forceReason: null,
            checks: [],
          }),
        } as Response)
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => ({}) } as Response)
    }),
  )
  return hardCloseCalls
}

describe('ClosingCenterPage', () => {
  it('runs the pre-close checklist and blocks hard close when a blocking check fails', async () => {
    stubFetch(false)
    const user = userEvent.setup()
    render(renderApp('/finanzas/cierre'))

    await user.selectOptions(await screen.findByLabelText('Período fiscal a cerrar'), 'p1')

    expect(await screen.findByText(/Cierre duro bloqueado/)).toBeInTheDocument()
    expect(screen.getByText('BLOQUEA EL CIERRE')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Ejecutar cierre duro' })).toBeDisabled()
  })

  it('allows hard close when every blocking check passes', async () => {
    const calls = stubFetch(true)
    const user = userEvent.setup()
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    render(renderApp('/finanzas/cierre'))

    await user.selectOptions(await screen.findByLabelText('Período fiscal a cerrar'), 'p1')
    expect(await screen.findByText('Listo para cierre duro')).toBeInTheDocument()

    const button = screen.getByRole('button', { name: 'Ejecutar cierre duro' })
    expect(button).toBeEnabled()
    await user.click(button)

    expect(await screen.findByText(/Período cerrado\. Manifiesto generado/)).toBeInTheDocument()
    expect(calls.length).toBe(1)
    expect(JSON.parse(calls[0])).toEqual({ force: false })
  })
})
