import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

function stubFetch(companies: unknown[], equipment: unknown[]) {
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
        return Promise.resolve({ ok: true, status: 200, json: async () => companies } as Response)
      }
      if (url.includes('/equipment?')) {
        return Promise.resolve({ ok: true, status: 200, json: async () => equipment } as Response)
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => ({}) } as Response)
    }),
  )
}

describe('EquipmentPage', () => {
  it('shows an honest empty state when there are no companies yet', async () => {
    stubFetch([], [])

    render(renderApp('/recursos/equipos'))

    expect(await screen.findByText(/configura una compañía primero/i)).toBeInTheDocument()
  })

  it('lists real equipment for the active company, never fabricated rows', async () => {
    stubFetch(
      [{ id: 'c1', name: 'Constructora Nexora', code: null, legalName: null, functionalCurrencyCode: 'HNL' }],
      [
        {
          id: 'e1',
          companyId: 'c1',
          assetId: null,
          projectId: null,
          equipmentType: 'EXCAVATOR',
          name: 'Retroexcavadora 01',
          serialNumber: null,
          plateNumber: 'ABC-123',
          operator: null,
          hourMeter: '0.00',
          odometer: '0.00',
          status: 'AVAILABLE',
        },
      ],
    )

    render(renderApp('/recursos/equipos'))

    expect(await screen.findByText('Retroexcavadora 01')).toBeInTheDocument()
    expect(screen.getByText('ABC-123')).toBeInTheDocument()
  })
})
