import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

function stubFetch() {
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
            permissions: ['project.budget:read'],
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
      if (url.includes('/financial-cockpit')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            projectId: 'p1',
            projectName: 'Torre Cockpit',
            currencyCode: 'HNL',
            budgetAtCompletion: 600,
            committed: 0,
            actualCost: 200,
            percentComplete: 50,
            earnedValue: 300,
            costPerformanceIndex: 1.5,
            estimateToComplete: 200,
            estimateAtCompletion: 400,
            varianceAtCompletion: 200,
            contractRevenue: 1000,
            projectedMargin: 600,
            projectedMarginPct: 60,
          }),
        } as Response)
      }
      if (url.includes('/projects?')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => [{ id: 'p1', name: 'Torre Cockpit', code: 'CKP-001', companyId: 'c1' }],
        } as Response)
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => ({}) } as Response)
    }),
  )
}

describe('ProjectCockpitPage', () => {
  it('shows EAC/ETC/CPI/margin from the backend', async () => {
    stubFetch()
    const user = userEvent.setup()
    render(renderApp('/proyectos/cockpit'))

    await user.selectOptions(await screen.findByLabelText('Proyecto'), 'p1')

    expect(await screen.findByText('Estimado al completar (EAC)')).toBeInTheDocument()
    expect(screen.getByText('CPI 1.50')).toBeInTheDocument()
    expect(screen.getByText('Dentro de presupuesto')).toBeInTheDocument()
    expect(screen.getByText(/60\.00%/)).toBeInTheDocument()
  })
})
