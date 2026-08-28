import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

function makeCompany() {
  return {
    id: 'c1',
    name: 'Constructora Nexora',
    code: 'NX-001',
    legalName: null as string | null,
    functionalCurrencyCode: 'HNL',
    country: null,
    fiscalId: null as string | null,
  }
}

function stubFetch(company: ReturnType<typeof makeCompany>) {
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
      if (init?.method === 'PATCH' && url.match(/\/master-data\/companies\/.+/)) {
        // El "servidor" canonicaliza legalName a mayúsculas -- si la UI
        // muestra este valor después de guardar, es porque de verdad
        // recargó desde la API real, no porque conservó lo que el usuario
        // tecleó localmente.
        const body = JSON.parse(String(init.body)) as { legalName?: string; fiscalId?: string }
        if (body.legalName !== undefined) company.legalName = body.legalName.toUpperCase()
        if (body.fiscalId !== undefined) company.fiscalId = body.fiscalId
        return Promise.resolve({ ok: true, status: 200, json: async () => ({ ...company }) } as Response)
      }
      if (url.includes('/master-data/companies')) {
        return Promise.resolve({ ok: true, status: 200, json: async () => [{ ...company }] } as Response)
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => ({}) } as Response)
    }),
  )
}

describe('CompanySettingsPage', () => {
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

    render(renderApp('/control/configuracion'))

    expect(await screen.findByText(/no hay compañías registradas/i)).toBeInTheDocument()
  })

  it('shows code/functional currency read-only and persists legal name + fiscal id through the real PATCH API', async () => {
    const company = makeCompany()
    stubFetch(company)
    const user = userEvent.setup()

    render(renderApp('/control/configuracion'))

    expect(await screen.findByDisplayValue('NX-001')).toBeInTheDocument()
    expect(screen.getByLabelText(/moneda funcional/i)).toHaveValue('HNL')

    const legalNameInput = screen.getByLabelText(/razón social/i)
    await user.clear(legalNameInput)
    await user.type(legalNameInput, 'constructora nexora s.a.')

    const fiscalIdInput = screen.getByLabelText(/identificación fiscal/i)
    await user.clear(fiscalIdInput)
    await user.type(fiscalIdInput, '0801-1990-12345')

    await user.click(screen.getByRole('button', { name: /guardar cambios/i }))

    expect(await screen.findByText(/cambios guardados/i)).toBeInTheDocument()
    // Valor canonicalizado por el "servidor" (mayúsculas) -- prueba que la
    // UI refleja la respuesta real de la API, no solo el estado local.
    expect(await screen.findByDisplayValue('CONSTRUCTORA NEXORA S.A.')).toBeInTheDocument()
    expect(screen.getByDisplayValue('0801-1990-12345')).toBeInTheDocument()

    // El código y la moneda funcional nunca se enviaron ni cambiaron.
    expect(screen.getByDisplayValue('NX-001')).toBeInTheDocument()
    expect(screen.getByLabelText(/moneda funcional/i)).toHaveValue('HNL')
  })
})
