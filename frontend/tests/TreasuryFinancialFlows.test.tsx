import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

const company = {
  id: 'c1',
  name: 'NEXORA GROUP',
  code: null,
  legalName: null,
  functionalCurrencyCode: 'HNL',
  country: null,
  fiscalId: null,
}
const treasuryAccounts = [
  {
    id: 't-atl', companyId: 'c1', name: 'Banco Atlántida HNL', kind: 'BANK', institution: 'Banco Atlántida', accountReference: null, currencyCode: 'HNL', glAccountId: 'a-bank-1', status: 'ACTIVE', balance: '1000.00',
  },
  {
    id: 't-bac', companyId: 'c1', name: 'Banco BAC HNL', kind: 'BANK', institution: 'BAC', accountReference: null, currencyCode: 'HNL', glAccountId: 'a-bank-2', status: 'ACTIVE', balance: '500.00',
  },
]

function authResponse() {
  return { id: 'u1', email: 'admin@nexora.group', fullName: 'Admin', roles: ['Administrator'] }
}

function baseResponse(url: string) {
  if (url.includes('/auth/me')) return authResponse()
  if (url.includes('/master-data/companies')) return [company]
  if (url.includes('/treasury/accounts')) return treasuryAccounts
  if (url.includes('/projects?company_id=c1')) {
    return [{ id: 'p1', companyId: 'c1', name: 'Cerco Perimetral', code: 'CERCO', currencyCode: 'HNL', status: 'PLANNING' }]
  }
  return undefined
}

describe('Treasury financial flow corrections', () => {
  it('classifies remittances and never asks for a project', async () => {
    vi.stubGlobal('fetch', vi.fn().mockImplementation((input: RequestInfo | URL) => {
      const url = String(input)
      const base = baseResponse(url)
      if (base !== undefined) return Promise.resolve({ ok: true, status: 200, json: async () => base } as Response)
      if (url.includes('/master-data/accounts')) {
        return Promise.resolve({ ok: true, status: 200, json: async () => [
          { id: 'a-bank-1', code: '1102', name: 'Banco Atlántida — HNL', accountType: 'ASSET', parentId: null, isPostable: true },
          { id: 'a-bank-2', code: '1104', name: 'Banco BAC — HNL', accountType: 'ASSET', parentId: null, isPostable: true },
          { id: 'eq', code: '3101', name: 'Capital y aportaciones', accountType: 'EQUITY', parentId: null, isPostable: true },
          { id: 'liab', code: '2201', name: 'Préstamos recibidos', accountType: 'LIABILITY', parentId: null, isPostable: true },
          { id: 'rev', code: '4201', name: 'Otros ingresos', accountType: 'REVENUE', parentId: null, isPostable: true },
          { id: 'exp', code: '6101', name: 'Gastos administrativos', accountType: 'EXPENSE', parentId: null, isPostable: true },
        ] } as Response)
      }
      if (url.includes('/treasury/remittances')) return Promise.resolve({ ok: true, status: 200, json: async () => [] } as Response)
      return Promise.resolve({ ok: true, status: 200, json: async () => [] } as Response)
    }))

    render(renderApp('/finanzas/tesoreria'))
    await userEvent.click(await screen.findByRole('button', { name: /registrar remesa/i }))

    expect(screen.getByLabelText(/origen \/ naturaleza de la entrada/i)).toBeInTheDocument()
    expect(screen.queryByLabelText(/^proyecto$/i)).not.toBeInTheDocument()
    expect(screen.getByRole('option', { name: /3101 · Capital y aportaciones/i })).toBeInTheDocument()
    expect(screen.queryByRole('option', { name: /Gastos administrativos/i })).not.toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Karen Vannessa Lopez Gonzalez' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Maria del Rosario Lopez Gonzalez' })).toBeInTheDocument()
  expect(screen.getByRole('option', { name: 'Davie Morales Rodriguez' })).toBeInTheDocument()
  expect(screen.getByRole('option', { name: 'Mavel Griselda Tejada' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Remesa' })).toBeInTheDocument()
    await userEvent.selectOptions(screen.getByLabelText(/^Remitente$/i), '__OTHER__')
    expect(screen.getByLabelText(/nombre completo del remitente/i)).toBeInTheDocument()

    await userEvent.selectOptions(screen.getByLabelText(/origen \/ naturaleza/i), 'FINANCING')
    expect(screen.getByRole('option', { name: /2201 · Préstamos recibidos/i })).toBeInTheDocument()
    expect(screen.queryByRole('option', { name: /3101 · Capital/i })).not.toBeInTheDocument()
  })

  it('requires a project only when an immediate expense is project-attributable', async () => {
    let posted: Record<string, unknown> | null = null
    vi.stubGlobal('fetch', vi.fn().mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      const base = baseResponse(url)
      if (base !== undefined) return Promise.resolve({ ok: true, status: 200, json: async () => base } as Response)
      if (url.includes('/master-data/accounts')) {
        return Promise.resolve({ ok: true, status: 200, json: async () => [
          { id: 'a-bank-1', code: '1102', name: 'Banco Atlántida — HNL', accountType: 'ASSET', parentId: null, isPostable: true },
          { id: 'a-bank-2', code: '1104', name: 'Banco BAC — HNL', accountType: 'ASSET', parentId: null, isPostable: true },
          { id: 'exp', code: '5101', name: 'Costos directos de construcción', accountType: 'EXPENSE', parentId: null, isPostable: true },
        ] } as Response)
      }
      if (url.includes('/treasury/remittances')) return Promise.resolve({ ok: true, status: 200, json: async () => [] } as Response)
      if (url.includes('/treasury/general-expenses') && init?.method === 'POST') {
        posted = JSON.parse(String(init.body))
        return Promise.resolve({ ok: true, status: 201, json: async () => ({ id: 'g1', accountingDocumentId: 'doc1' }) } as Response)
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => [] } as Response)
    }))

    render(renderApp('/finanzas/tesoreria'))
    await userEvent.click(await screen.findByRole('button', { name: /registrar salida \/ gasto/i }))
    expect(screen.queryByLabelText(/^proyecto$/i)).not.toBeInTheDocument()
    await userEvent.selectOptions(screen.getByLabelText(/alcance del gasto/i), 'PROJECT')
    await userEvent.selectOptions(await screen.findByLabelText(/^proyecto$/i), 'p1')
    await userEvent.type(screen.getByLabelText(/descripción/i), 'Gasolina de la obra')
    await userEvent.type(screen.getByLabelText(/monto/i), '750')
    await userEvent.click(screen.getByRole('button', { name: /^registrar salida$/i }))

    await waitFor(() => expect(posted).toMatchObject({ scope: 'PROJECT', projectId: 'p1', treasuryAccountId: 't-atl' }))
  })

  it('lets the user choose the actual bank when paying a supplier invoice', async () => {
    let paymentPayload: Record<string, unknown> | null = null
    const invoice = { id: 'ap1', supplierId: 's1', invoiceNumber: 'FAC-P-1', scope: 'PROJECT', projectId: 'p1', currencyCode: 'HNL', amount: 1000, taxAmount: 0, amountPaid: 0, dueDate: '2026-09-01', status: 'APPROVED' }
    vi.stubGlobal('fetch', vi.fn().mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      const base = baseResponse(url)
      if (base !== undefined) return Promise.resolve({ ok: true, status: 200, json: async () => base } as Response)
      if (url.includes('/master-data/accounts')) return Promise.resolve({ ok: true, status: 200, json: async () => [] } as Response)
      if (url.includes('/procurement/suppliers')) return Promise.resolve({ ok: true, status: 200, json: async () => [{ id: 's1', companyId: 'c1', legalName: 'Proveedor', status: 'ACTIVE' }] } as Response)
      if (url.includes('/ap/supplier-invoices/ap1/payments')) {
        paymentPayload = JSON.parse(String(init?.body))
        return Promise.resolve({ ok: true, status: 200, json: async () => ({}) } as Response)
      }
      if (url.includes('/ap/supplier-invoices/ap1')) return Promise.resolve({ ok: true, status: 200, json: async () => ({ ...invoice, status: 'PAID', amountPaid: 1000 }) } as Response)
      if (url.includes('/ap/supplier-invoices')) return Promise.resolve({ ok: true, status: 200, json: async () => [invoice] } as Response)
      return Promise.resolve({ ok: true, status: 200, json: async () => [] } as Response)
    }))

    render(renderApp('/finanzas/cuentas-por-pagar'))
    await userEvent.click(await screen.findByRole('button', { name: /pagar saldo/i }))
    await userEvent.selectOptions(screen.getByLabelText(/cuenta pagadora/i), 't-bac')
    await userEvent.click(screen.getByRole('button', { name: /confirmar pago/i }))
    await waitFor(() => expect(paymentPayload).toMatchObject({ treasuryAccountId: 't-bac', amount: '1000' }))
  })

  it('lets the user choose the actual bank when collecting a customer invoice', async () => {
    let collectionPayload: Record<string, unknown> | null = null
    const invoice = { id: 'ar1', customerId: 'cu1', invoiceNumber: 'FAC-C-1', scope: 'PROJECT', projectId: 'p1', currencyCode: 'HNL', amount: 800, amountCollected: 0, dueDate: '2026-09-01', status: 'APPROVED' }
    vi.stubGlobal('fetch', vi.fn().mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      const base = baseResponse(url)
      if (base !== undefined) return Promise.resolve({ ok: true, status: 200, json: async () => base } as Response)
      if (url.includes('/master-data/accounts')) return Promise.resolve({ ok: true, status: 200, json: async () => [] } as Response)
      if (url.includes('/crm/customers')) return Promise.resolve({ ok: true, status: 200, json: async () => [{ id: 'cu1', companyId: 'c1', legalName: 'Cliente', status: 'ACTIVE' }] } as Response)
      if (url.includes('/ar/customer-invoices/ar1/receipts')) {
        collectionPayload = JSON.parse(String(init?.body))
        return Promise.resolve({ ok: true, status: 200, json: async () => ({}) } as Response)
      }
      if (url.includes('/ar/customer-invoices/ar1')) return Promise.resolve({ ok: true, status: 200, json: async () => ({ ...invoice, status: 'COLLECTED', amountCollected: 800 }) } as Response)
      if (url.includes('/ar/customer-invoices')) return Promise.resolve({ ok: true, status: 200, json: async () => [invoice] } as Response)
      return Promise.resolve({ ok: true, status: 200, json: async () => [] } as Response)
    }))

    render(renderApp('/finanzas/cuentas-por-cobrar'))
    await userEvent.click(await screen.findByRole('button', { name: /cobrar saldo/i }))
    await userEvent.selectOptions(screen.getByLabelText(/cuenta receptora/i), 't-bac')
    await userEvent.click(screen.getByRole('button', { name: /confirmar cobro/i }))
    await waitFor(() => expect(collectionPayload).toMatchObject({ treasuryAccountId: 't-bac', amount: '800' }))
  })
})