import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

function stubFetch(context: { activeProjectId: string | null; activeProjectName: string | null }, summary: unknown) {
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
      if (url.includes('/context')) {
        return Promise.resolve({ ok: true, status: 200, json: async () => context } as Response)
      }
      if (url.includes('/reports/budget-vs-actual')) {
        return Promise.resolve({ ok: true, status: 200, json: async () => summary } as Response)
      }
      if (url.includes('/master-data/companies')) {
        return Promise.resolve({ ok: true, status: 200, json: async () => [] } as Response)
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => ({}) } as Response)
    }),
  )
}

describe('BudgetVsActualPage', () => {
  it('prompts to select an active project when none is set', async () => {
    stubFetch({ activeProjectId: null, activeProjectName: null }, {})

    const user = userEvent.setup()
    render(renderApp('/control/reportes'))

    await user.click(await screen.findByRole('tab', { name: 'Presupuesto vs. Real' }))

    expect(await screen.findByText('Selecciona un proyecto activo')).toBeInTheDocument()
  })

  it('loads and displays budget-vs-actual numbers straight from budget_service.compute_summary', async () => {
    stubFetch(
      { activeProjectId: 'p1', activeProjectName: 'Torre Nexora II' },
      {
        authorized: '1000.00',
        committed: '125.50',
        accrued: '0',
        paid: '0',
        available: '874.50',
      },
    )

    const user = userEvent.setup()
    render(renderApp('/control/reportes'))

    await user.click(await screen.findByRole('tab', { name: 'Presupuesto vs. Real' }))

    expect(await screen.findByText('1000.00')).toBeInTheDocument()
    expect(screen.getByText('125.50')).toBeInTheDocument()
    expect(screen.getByText('874.50')).toBeInTheDocument()
  })
})
