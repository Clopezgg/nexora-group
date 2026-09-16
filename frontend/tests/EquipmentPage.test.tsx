import { fireEvent, render, screen } from '@testing-library/react'
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

  it('creates a maintenance plan and links it only to a preventive order', async () => {
    const plans: unknown[] = []
    stubFetch(
      [{ id: 'c1', name: 'Constructora Nexora', code: null, legalName: null, functionalCurrencyCode: 'HNL' }],
      [{ id: 'e1', companyId: 'c1', assetId: null, projectId: null, equipmentType: 'EXCAVATOR', name: 'Retroexcavadora 01', serialNumber: null, plateNumber: null, operator: null, hourMeter: '0.00', odometer: '0.00', status: 'AVAILABLE' }],
    )
    const originalFetch = globalThis.fetch
    vi.stubGlobal('fetch', vi.fn().mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.includes('/maintenance-plans') && init?.method === 'POST') {
        const body = JSON.parse(String(init.body)); const plan = { id: 'plan-1', equipmentId: 'e1', active: true, description: null, ...body }; plans.push(plan)
        return { ok: true, status: 201, json: async () => plan } as Response
      }
      if (url.includes('/maintenance-plans')) return { ok: true, status: 200, json: async () => plans } as Response
      if (url.includes('/maintenance-orders')) return { ok: true, status: 200, json: async () => [] } as Response
      return originalFetch(input, init)
    }))

    render(renderApp('/recursos/mantenimiento'))
    fireEvent.change(await screen.findByText('Retroexcavadora 01').then((option) => option.parentElement as HTMLSelectElement), { target: { value: 'e1' } })
    fireEvent.click(screen.getByRole('button', { name: 'Nuevo plan' }))
    fireEvent.change(screen.getByLabelText('Nombre'), { target: { value: 'Servicio 250 horas' } })
    fireEvent.change(screen.getByLabelText('Valor del disparador'), { target: { value: '250' } })
    fireEvent.click(screen.getByRole('button', { name: 'Guardar plan' }))
    expect(await screen.findByText('Servicio 250 horas')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Nueva orden' }))
    fireEvent.change(screen.getByLabelText('Tipo'), { target: { value: 'PREVENTIVE' } })
    expect(screen.getByRole('option', { name: 'Servicio 250 horas' })).toBeInTheDocument()
  })
})
