import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

const COMPANY = { id: 'c1', name: 'NEXORA', code: null, legalName: null, functionalCurrencyCode: 'HNL' }
const SUPPLIER = {
  id: 's1', companyId: 'c1', legalName: 'Lester Rivas', tradeName: null, taxId: '0801-1990-12345',
  contactName: 'Lester Rivas', email: null, phone: '9999-0000', address: null,
  addressLine1: null, addressLine2: null, city: null, stateDepartment: null, country: null,
  status: 'ACTIVE', partyRole: 'CONTRACTOR', classification: null, paymentTerms: null,
}

describe('SuppliersPage — Proveedores y Contratistas (§10/§14/§16)', () => {
  it('titula "Proveedores y Contratistas", muestra el tipo y permite editar', async () => {
    const patched: unknown[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input)
        const method = init?.method ?? 'GET'
        const ok = (body: unknown) => Promise.resolve({ ok: true, status: 200, json: async () => body } as Response)
        if (url.includes('/auth/me')) return ok({ id: 'u1', email: 'a@nexora.group', fullName: 'Admin', roles: ['Administrator'] })
        if (url.includes('/master-data/companies')) return ok([COMPANY])
        if (url.includes('/procurement/suppliers') && method === 'PATCH') {
          patched.push(JSON.parse(String(init?.body)))
          return ok({ ...SUPPLIER, email: 'pagos@rivas.hn' })
        }
        if (url.includes('/procurement/suppliers')) return ok([SUPPLIER])
        return ok([])
      }),
    )

    render(renderApp('/abastecimiento/proveedores'))

    expect(await screen.findByRole('heading', { name: 'Proveedores y Contratistas' })).toBeInTheDocument()
    expect(await screen.findByText('Contratista')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /\+ Nuevo proveedor \/ contratista/i })).toBeInTheDocument()

    await userEvent.click(await screen.findByRole('button', { name: /Ver \/ editar/i }))
    const email = await screen.findByLabelText(/^Correo/i)
    await userEvent.type(email, 'pagos@rivas.hn')
    await userEvent.click(screen.getByRole('button', { name: /Guardar cambios/i }))

    await waitFor(() => expect(patched.length).toBe(1))
    expect((patched[0] as { email: string }).email).toBe('pagos@rivas.hn')
  })
})
