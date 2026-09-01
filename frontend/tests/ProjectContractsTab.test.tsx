import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

const COMPANY = { id: 'c1', name: 'Constructora Nexora', code: null, legalName: null, functionalCurrencyCode: 'HNL' }
const PROJECT = {
  id: 'p1',
  companyId: 'c1',
  name: 'Casa Residencial',
  code: 'CASA-1',
  status: 'ACTIVE',
  currencyCode: 'HNL',
  customerId: null,
  managerUserId: null,
  costCenterId: null,
  plannedStart: null,
  plannedEnd: null,
  description: null,
  addressLine1: null,
  addressLine2: null,
  city: null,
  stateDepartment: null,
  country: null,
  locationReference: null,
  manager: null,
}
const SUPPLIER = { id: 's1', companyId: 'c1', legalName: 'Lester Rivas', status: 'ACTIVE', classification: null }

function stubFetch(onCreate?: () => void) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      const method = init?.method ?? 'GET'
      const ok = (status: number, body: unknown) =>
        Promise.resolve({ ok: status < 300, status, json: async () => body } as Response)
      if (url.includes('/auth/me'))
        return ok(200, { id: 'u1', email: 'a@nexora.group', fullName: 'Admin', roles: ['Administrator'] })
      if (url.includes('/master-data/companies')) return ok(200, [COMPANY])
      if (url.includes('/procurement/suppliers/contracts') && method === 'POST') {
        onCreate?.()
        return ok(201, { ...PROJECT })
      }
      if (url.includes('/procurement/suppliers/contracts')) return ok(200, [])
      if (url.includes('/procurement/suppliers')) return ok(200, [SUPPLIER])
      if (url.match(/\/projects\/p1\/financial-summary/)) return ok(200, null)
      if (url.match(/\/projects\/p1$/)) return ok(200, PROJECT)
      if (url.includes('/projects')) return ok(200, [PROJECT])
      if (url.includes('/contract-payments')) return ok(404, { error: { code: 'NXR-404' } })
      return ok(200, [])
    }),
  )
}

describe('Project Cockpit — Contratos', () => {
  it('lets you add an execution contract without leaving the project (§4/§11)', async () => {
    const onCreate = vi.fn()
    stubFetch(onCreate)

    render(renderApp('/proyectos/p1'))

    await userEvent.click(await screen.findByRole('tab', { name: /contratos/i }))
    await userEvent.click(await screen.findByRole('button', { name: /\+ agregar contrato/i }))

    // El proyecto se hereda: no hay selector de proyecto en el formulario.
    expect(screen.getByText('Nuevo contrato de ejecución')).toBeInTheDocument()
    expect(screen.queryByLabelText(/proyecto \(opcional\)/i)).not.toBeInTheDocument()

    await userEvent.selectOptions(screen.getByLabelText(/contratista/i), 's1')
    await userEvent.type(screen.getByLabelText(/número de contrato/i), 'CON-EXC-1')
    await userEvent.type(screen.getByLabelText(/valor contractual/i), '250000')
    await userEvent.type(screen.getByLabelText(/fecha de inicio/i), '2026-04-01')
    await userEvent.click(screen.getByRole('button', { name: /guardar contrato/i }))

    expect(onCreate).toHaveBeenCalled()
  })
})
