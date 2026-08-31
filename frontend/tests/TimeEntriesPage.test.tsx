import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

const COMPANY = { id: 'c1', name: 'Constructora Nexora', code: null, legalName: null, functionalCurrencyCode: 'HNL' }
const WORKER = {
  id: 'w1',
  companyId: 'c1',
  fullName: 'Juan Pérez',
  roleTitle: 'Albañil',
  standardHourlyRate: '125.50',
  active: true,
}

function makeSubmittedEntry() {
  return {
    id: 't1',
    companyId: 'c1',
    workerId: 'w1',
    scope: 'GENERAL',
    projectId: null,
    workDate: '2026-01-10',
    hoursWorked: '8.00',
    hourlyRate: '125.50',
    status: 'SUBMITTED',
    approvedHours: null,
    laborCost: null,
    approvedById: null,
    approvedAt: null,
  }
}

function stubFetch() {
  const entries = [makeSubmittedEntry()]

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
      if (url.includes('/workforce/workers')) {
        return Promise.resolve({ ok: true, status: 200, json: async () => [WORKER] } as Response)
      }
      if (url.includes('/projects?')) {
        return Promise.resolve({ ok: true, status: 200, json: async () => [] } as Response)
      }
      if (url.match(/\/workforce\/time-entries\/.+\/approve/)) {
        const body = init?.body ? JSON.parse(String(init.body)) : {}
        const approvedHours = body.approvedHours ?? entries[0].hoursWorked
        entries[0] = {
          ...entries[0],
          status: 'APPROVED',
          approvedHours,
          laborCost: (Number(entries[0].hourlyRate) * Number(approvedHours)).toFixed(2),
          approvedById: 'u1',
          approvedAt: '2026-01-11T00:00:00Z',
        }
        return Promise.resolve({ ok: true, status: 200, json: async () => entries[0] } as Response)
      }
      if (url.includes('/workforce/time-entries')) {
        // A real backend response is a fresh object graph on every call (a
        // new JSON payload deserialized); return a copy here too, not the
        // live mutable array, so the test exercises the same "did the data
        // actually change" reactivity path the real API does.
        return Promise.resolve({ ok: true, status: 200, json: async () => entries.map((entry) => ({ ...entry })) } as Response)
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => ({}) } as Response)
    }),
  )
}

describe('TimeEntriesPage', () => {
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

    render(renderApp('/recursos/tiempo'))

    expect(await screen.findByText(/configura una compañía primero/i)).toBeInTheDocument()
  })

  it('reloads Workers and TimeEntries from their real APIs, approves a time entry, and displays the server-computed labor cost', async () => {
    stubFetch()
    const user = userEvent.setup()

    render(renderApp('/recursos/tiempo'))

    const row = (await screen.findByText('Juan Pérez')).closest('tr')
    expect(row).not.toBeNull()
    expect(within(row as HTMLElement).getByText('Enviado')).toBeInTheDocument()

    await user.click(within(row as HTMLElement).getByRole('button', { name: /aprobar/i }))

    const approvedRow = (await screen.findByText('Juan Pérez')).closest('tr') as HTMLElement
    await within(approvedRow).findByText('Aprobado')
    // Money is rendered through the global formatter: symbol + thousands + 2 decimals.
    expect(within(approvedRow).getByText(/^L\s?1,004\.00$/)).toBeInTheDocument()
  })
})
