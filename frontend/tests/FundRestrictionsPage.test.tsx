import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

const COMPANY = { id: 'c1', name: 'NEXORA', code: null, legalName: null, functionalCurrencyCode: 'HNL' }
const ACCOUNTS = [
  { id: 't-atl', companyId: 'c1', name: 'Banco Atlántida HNL', kind: 'BANK', institution: 'Banco Atlántida', accountReference: null, currencyCode: 'HNL', glAccountId: 'a1', status: 'ACTIVE', balance: '1000.00' },
]

describe('FundRestrictionsPage (§21 — bug de carga de restricciones)', () => {
  it('carga las restricciones de la cuenta seleccionada usando treasuryAccountId, no companyId', async () => {
    const calls: string[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((input: RequestInfo | URL) => {
        const url = String(input)
        calls.push(url)
        const ok = (body: unknown) => Promise.resolve({ ok: true, status: 200, json: async () => body } as Response)
        if (url.includes('/auth/me')) return ok({ id: 'u1', email: 'a@nexora.group', fullName: 'Admin', roles: ['Administrator'] })
        if (url.includes('/master-data/companies')) return ok([COMPANY])
        if (url.includes('/treasury/accounts')) return ok(ACCOUNTS)
        if (url.includes('/projects')) return ok([])
        if (url.includes('/treasury/fund-restrictions')) {
          // El backend exige treasuryAccountId; con companyId respondería 422.
          if (url.includes('companyId')) return Promise.resolve({ ok: false, status: 422, json: async () => ({ error: { code: 'NXR-422' } }) } as Response)
          return ok([])
        }
        if (url.includes('/treasury/accounts/t-atl/availability')) return ok({ balance: '1000.00', reservedAmount: '0.00', availableAmount: '1000.00' })
        return ok([])
      }),
    )

    render(renderApp('/finanzas/restricciones-fondos'))

    await waitFor(() =>
      expect(calls.some((u) => u.includes('/treasury/fund-restrictions') && u.includes('treasuryAccountId=t-atl'))).toBe(true),
    )
    expect(calls.some((u) => u.includes('/treasury/fund-restrictions') && u.includes('companyId'))).toBe(false)
    expect(await screen.findByText(/No hay restricciones/i)).toBeInTheDocument()
    expect(screen.queryByText(/No se pudieron cargar las restricciones/i)).not.toBeInTheDocument()
  })
})
