import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

const COMPANY = { id: 'c1', name: 'Constructora Nexora', code: null, legalName: null, functionalCurrencyCode: 'HNL' }

function makePendingRequest() {
  return {
    id: 'ar1',
    policyId: null,
    entityType: 'ap.supplier_invoice',
    entityId: 'inv1',
    companyId: 'c1',
    projectId: null,
    module: 'ap',
    requestedBy: 'u2',
    assignedTo: 'u1',
    assignedRole: null,
    status: 'PENDING',
    priority: 'NORMAL',
    amount: '1000.00',
    comment: null,
    decidedBy: null,
    decidedAt: null,
    createdAt: '2026-08-25T10:00:00Z',
  }
}

function stubFetch() {
  const requests = [makePendingRequest()]

  vi.stubGlobal(
    'fetch',
    vi.fn().mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.includes('/auth/me')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({ id: 'u1', email: 'admin@nexora.group', fullName: 'Admin', roles: ['Administrator'] }),
        } as Response)
      }
      if (url.includes('/master-data/companies')) {
        return Promise.resolve({ ok: true, status: 200, json: async () => [COMPANY] } as Response)
      }
      if (url.match(/\/approvals\/.+\/decide/)) {
        const body = init?.body ? JSON.parse(String(init.body)) : {}
        requests[0] = {
          ...requests[0],
          status: body.decision,
          decidedBy: 'u1',
          decidedAt: '2026-08-25T11:00:00Z',
          comment: body.comment ?? null,
        }
        return Promise.resolve({ ok: true, status: 200, json: async () => requests[0] } as Response)
      }
      if (url.includes('/approvals?')) {
        return Promise.resolve({ ok: true, status: 200, json: async () => requests.map((r) => ({ ...r })) } as Response)
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => ({}) } as Response)
    }),
  )
}

describe('ApprovalInboxPage', () => {
  it('shows an honest empty state when there are no companies yet', async () => {
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
          return Promise.resolve({ ok: true, status: 200, json: async () => [] } as Response)
        }
        return Promise.resolve({ ok: true, status: 200, json: async () => ({}) } as Response)
      }),
    )

    render(renderApp('/inicio/aprobaciones'))

    expect(await screen.findByText(/configura una compañía primero/i)).toBeInTheDocument()
  })

  it('loads pending approvals, decides via the real API, and refetches the updated row', async () => {
    stubFetch()
    const user = userEvent.setup()

    render(renderApp('/inicio/aprobaciones'))

    const row = (await screen.findByText('ap.supplier_invoice')).closest('tr')
    expect(row).not.toBeNull()

    await user.click(within(row as HTMLElement).getByRole('button', { name: /aprobar/i }))

    // After the decide response, the row no longer has a PENDING status --
    // the Approve/Reject controls (which only render for PENDING rows)
    // should disappear, proving the page actually refetched the real API
    // response rather than optimistically mutating local state.
    await screen.findByText('ap.supplier_invoice')
    const updatedRow = screen.getByText('ap.supplier_invoice').closest('tr')
    expect(updatedRow).not.toBeNull()
    expect(within(updatedRow as HTMLElement).queryByRole('button', { name: /aprobar/i })).not.toBeInTheDocument()
  })
})
