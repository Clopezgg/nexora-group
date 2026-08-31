import { render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { readSelectedCompanyId, writeSelectedCompanyId } from '../src/hooks/useActiveCompany'
import { renderApp } from './testUtils'

function stubAuthenticatedFetch(roles: string[], dashboard?: Record<string, unknown>) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockImplementation((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/auth/me')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({ id: 'u1', email: 'user@nexora.group', fullName: 'Usuaria Demo', roles }),
        } as Response)
      }
      if (url.includes('/master-data/companies')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => [
            {
              id: 'c1',
              name: 'NEXORA GROUP',
              code: null,
              legalName: null,
              functionalCurrencyCode: 'HNL',
              country: null,
              fiscalId: null,
            },
          ],
        } as Response)
      }
      if (url.includes('/dashboard/summary') && dashboard) {
        return Promise.resolve({ ok: true, status: 200, json: async () => dashboard } as Response)
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => ({}) } as Response)
    }),
  )
}

describe('HomePage', () => {
  it('keeps working when browser storage is unavailable or blocked', () => {
    const blockedStorage = {
      getItem: vi.fn(() => {
        throw new Error('storage blocked')
      }),
      removeItem: vi.fn(() => {
        throw new Error('storage blocked')
      }),
      setItem: vi.fn(() => {
        throw new Error('storage blocked')
      }),
    }

    expect(readSelectedCompanyId(undefined)).toBeNull()
    expect(readSelectedCompanyId(blockedStorage)).toBeNull()
    expect(() => writeSelectedCompanyId(undefined, 'c1')).not.toThrow()
    expect(() => writeSelectedCompanyId(blockedStorage, 'c1')).not.toThrow()
    expect(() => writeSelectedCompanyId(blockedStorage, null)).not.toThrow()
  })

  it('shows the finance home with real treasury cards for Administrator', async () => {
    stubAuthenticatedFetch(['Administrator'], {
      treasuryBalance: 12000,
      periodIncome: 5000,
      periodExpense: 2000,
      activeProjects: 3,
      pendingApprovals: 2,
      overduePayables: 1,
      overduePayablesAmount: 4500,
      receivablesOutstanding: 9000,
      currency: 'HNL',
    })

    render(renderApp('/inicio'))

    expect(await screen.findByRole('heading', { name: /inicio — finanzas/i })).toBeInTheDocument()
    expect(await screen.findByText('Tesorería · disponible')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
    // "Mi trabajo hoy" band, clicable, con el conteo real de aprobaciones.
    const workToday = screen.getByRole('region', { name: /mi trabajo hoy/i })
    expect(workToday).toBeInTheDocument()
    expect(within(workToday).getByRole('link', { name: /aprobaciones/i })).toHaveAttribute(
      'href',
      '/inicio/aprobaciones',
    )
  })

  it('shows the project home with real module shortcuts for Project Manager', async () => {
    stubAuthenticatedFetch(['Project Manager'])

    render(renderApp('/inicio'))

    expect(await screen.findByRole('heading', { name: /inicio — proyectos/i })).toBeInTheDocument()
    expect(screen.queryByText('Saldo Tesorería')).not.toBeInTheDocument()
    expect(screen.getByText('Presupuesto vs. actual')).toBeInTheDocument()
  })
})
