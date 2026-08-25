import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

function page(offset: number, limit: number) {
  return {
    rows: Array.from({ length: limit }, (_, i) => ({
      lineId: `l-${offset + i}`,
      documentId: `d-${offset + i}`,
      documentNumber: `JRN-${offset + i}`,
      postedAt: '2026-08-25T12:00:00Z',
      documentStatus: 'POSTED',
      accountId: 'a1',
      accountCode: '1000',
      accountName: 'Caja',
      accountType: 'ASSET',
      scope: 'GENERAL',
      projectId: null,
      description: null,
      debitAmount: '10.00',
      creditAmount: '0.00',
    })),
    total: 30,
    offset,
    limit,
    totalDebit: '300.00',
    totalCredit: '300.00',
  }
}

function stubFetch() {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockImplementation((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/auth/me')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({ id: 'u1', email: 'admin@nexora.group', fullName: 'Admin', roles: ['Administrator'] }),
        } as Response)
      }
      if (url.includes('/master-data/companies')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => [{ id: 'c1', name: 'Constructora Nexora', code: null, legalName: null, functionalCurrencyCode: 'HNL' }],
        } as Response)
      }
      if (url.includes('/reports/general-ledger')) {
        const parsed = new URL(url, 'http://localhost')
        const offset = Number(parsed.searchParams.get('offset') ?? '0')
        const limit = Number(parsed.searchParams.get('limit') ?? '25')
        return Promise.resolve({ ok: true, status: 200, json: async () => page(offset, limit) } as Response)
      }
      if (url.includes('/reports/trial-balance')) {
        return Promise.resolve({ ok: true, status: 200, json: async () => ({ rows: [], totalDebit: '0', totalCredit: '0' }) } as Response)
      }
      if (url.includes('/context')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({ activeProjectId: null, activeProjectName: null }),
        } as Response)
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => ({}) } as Response)
    }),
  )
}

describe('GeneralLedgerPage', () => {
  it('requests the next general-ledger page with a real offset', async () => {
    stubFetch()

    render(renderApp('/control/reportes'))
    await userEvent.click(await screen.findByRole('tab', { name: /libro mayor/i }))
    await screen.findByText('JRN-0')
    await userEvent.click(await screen.findByRole('button', { name: /siguiente/i }))

    expect(await screen.findByText('JRN-25')).toBeInTheDocument()
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('offset=25&limit=25'),
      expect.anything(),
    )
  })

  it('disables Previous at the first page', async () => {
    stubFetch()

    render(renderApp('/control/reportes'))
    await userEvent.click(await screen.findByRole('tab', { name: /libro mayor/i }))
    await screen.findByText('JRN-0')

    expect(screen.getByRole('button', { name: /anterior/i })).toBeDisabled()
  })
})
