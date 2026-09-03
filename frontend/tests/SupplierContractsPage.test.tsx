import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

const COMPANY = { id: 'c1', name: 'Constructora Nexora', code: null, legalName: null, functionalCurrencyCode: 'HNL' }
const SUPPLIER = {
  id: 's1',
  companyId: 'c1',
  legalName: 'Proveedor Estructuras S.A.',
  tradeName: null,
  taxId: null,
  email: null,
  phone: null,
  status: 'ACTIVE',
  classification: null,
}
const CONTRACT = {
  id: 'sc1',
  companyId: 'c1',
  supplierId: 's1',
  projectId: null,
  contractNumber: 'SC-001',
  scopeDescription: null,
  value: '150000.00',
  currencyCode: 'HNL',
  startDate: '2026-01-01',
  endDate: null,
  advancePercentage: '10.00',
  retentionPercentage: '5.00',
  paymentTerms: null,
  status: 'DRAFT',
  contractCategory: 'LABOR',
}

function stubFetch(overrides: { contracts?: unknown[]; onCreate?: () => void }) {
  let contracts = overrides.contracts ?? [CONTRACT]
  vi.stubGlobal(
    'fetch',
    vi.fn().mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      const method = init?.method ?? 'GET'
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
      if (url.includes('/procurement/suppliers/contracts') && method === 'POST') {
        overrides.onCreate?.()
        contracts = [...contracts, CONTRACT]
        return Promise.resolve({ ok: true, status: 201, json: async () => CONTRACT } as Response)
      }
      if (url.includes('/procurement/suppliers/contracts')) {
        return Promise.resolve({ ok: true, status: 200, json: async () => contracts } as Response)
      }
      if (url.includes('/procurement/suppliers')) {
        return Promise.resolve({ ok: true, status: 200, json: async () => [SUPPLIER] } as Response)
      }
      if (url.includes('/projects')) {
        return Promise.resolve({ ok: true, status: 200, json: async () => [] } as Response)
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => [] } as Response)
    }),
  )
}

describe('SupplierContractsPage', () => {
  it('shows an honest empty state when there are no contracts yet', async () => {
    stubFetch({ contracts: [] })

    render(renderApp('/abastecimiento/contratos'))

    expect(await screen.findByText(/aún no hay contratos/i)).toBeInTheDocument()
  })

  it('lists real supplier contracts from the API', async () => {
    stubFetch({})

    render(renderApp('/abastecimiento/contratos'))

    expect(await screen.findByText('SC-001')).toBeInTheDocument()
    expect(screen.getByText('L 150,000.00')).toBeInTheDocument()
    // §13: la categoría del contrato es visible en la lista, en español.
    const contractRow = screen.getByText('SC-001').closest('tr') as HTMLElement
    expect(within(contractRow).getByText('Mano de obra')).toBeInTheDocument()
    // Estado nunca crudo: DRAFT -> Borrador (ORDEN MAESTRA §7).
    expect(within(contractRow).getByText('Borrador')).toBeInTheDocument()
    expect(within(contractRow).queryByText('DRAFT')).not.toBeInTheDocument()
  })

  it('creates a new supplier contract through the real API', async () => {
    const onCreate = vi.fn()
    stubFetch({ contracts: [], onCreate })

    render(renderApp('/abastecimiento/contratos'))
    await userEvent.click(await screen.findByRole('button', { name: /nuevo contrato/i }))
    await userEvent.selectOptions(screen.getByLabelText(/proveedor/i), 's1')
    await userEvent.type(screen.getByLabelText(/número de contrato/i), 'SC-777')
    await userEvent.selectOptions(screen.getByLabelText(/categoría del costo/i), 'SUBCONTRACT')
    await userEvent.type(screen.getByLabelText(/^valor/i), '99999.00')
    await userEvent.type(screen.getByLabelText(/fecha de inicio/i), '2026-03-01')
    await userEvent.click(screen.getByRole('button', { name: /guardar/i }))

    expect(onCreate).toHaveBeenCalled()
  })
})
