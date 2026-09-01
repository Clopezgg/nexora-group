import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

function stubFetch(handlers: Record<string, unknown>) {
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
          }),
        } as Response)
      }
      for (const [fragment, body] of Object.entries(handlers)) {
        if (url.includes(fragment)) {
          return Promise.resolve({ ok: true, status: 200, json: async () => body } as Response)
        }
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => ({}) } as Response)
    }),
  )
}

describe('TreasuryPage', () => {
  it('shows an honest empty state (no fabricated balances) when there is no company yet', async () => {
    stubFetch({ '/master-data/companies': [] })

    render(renderApp('/finanzas/tesoreria'))

    expect(await screen.findByText(/aún no hay ninguna compañía configurada/i)).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /crear compañía y cuentas de inicio/i }),
    ).toBeInTheDocument()
  })

  it('renders real treasury account balances from the API, never a hardcoded figure', async () => {
    stubFetch({
      '/master-data/companies': [
        {
          id: 'c1',
          name: 'Constructora Nexora',
          code: null,
          legalName: null,
          functionalCurrencyCode: 'HNL',
          country: null,
          fiscalId: null,
        },
      ],
      '/master-data/accounts': [
        {
          id: 'a1',
          code: '1100',
          name: 'Bancos',
          accountType: 'ASSET',
          parentId: null,
          isPostable: true,
        },
      ],
      '/treasury/accounts': [
        {
          id: 't1',
          companyId: 'c1',
          name: 'Banco Principal',
          kind: 'BANK',
          institution: null,
          accountReference: null,
          currencyCode: 'HNL',
          glAccountId: 'a1',
          status: 'ACTIVE',
          balance: '4321.50',
        },
        {
          id: 't2',
          companyId: 'c1',
          name: 'Caja Central',
          kind: 'CASH',
          institution: null,
          accountReference: null,
          currencyCode: 'HNL',
          glAccountId: 'a1',
          status: 'ACTIVE',
          balance: '500.00',
        },
      ],
    })

    render(renderApp('/finanzas/tesoreria'))

    expect(await screen.findByText('Banco Principal')).toBeInTheDocument()
    expect(await screen.findByText(/4,321\.50/)).toBeInTheDocument()
    expect(await screen.findByText(/4,821\.50/)).toBeInTheDocument()
  })

  it.each([
    {
      route: '/finanzas/cuentas-por-pagar',
      endpoint: '/ap/supplier-invoices?companyId=c1',
      invoice: {
        id: 'ap1',
        supplierId: 's1',
        invoiceNumber: 'AP-DB-1',
        scope: 'GENERAL',
        currencyCode: 'HNL',
        amount: 125,
        taxAmount: 0,
        amountPaid: 0,
        dueDate: '2026-09-01',
        status: 'DRAFT',
      },
      visibleText: 'Proveedor persistido',
    },
    {
      route: '/finanzas/cuentas-por-cobrar',
      endpoint: '/ar/customer-invoices?companyId=c1',
      invoice: {
        id: 'ar1',
        customerId: 'cu1',
        invoiceNumber: 'AR-DB-1',
        scope: 'GENERAL',
        currencyCode: 'HNL',
        amount: 225,
        amountCollected: 0,
        dueDate: '2026-09-01',
        status: 'DRAFT',
      },
      visibleText: 'Cliente persistido',
    },
  ])(
    'reloads AP and AR invoices from their APIs: $endpoint',
    async ({ route, endpoint, invoice, visibleText }) => {
      stubFetch({
        '/master-data/companies': [
          {
            id: 'c1',
            name: 'Constructora Nexora',
            code: null,
            legalName: null,
            functionalCurrencyCode: 'HNL',
            country: null,
            fiscalId: null,
          },
        ],
        '/master-data/accounts': [],
        '/treasury/accounts': [],
        '/procurement/suppliers': [
          {
            id: 's1',
            companyId: 'c1',
            legalName: 'Proveedor persistido',
            tradeName: null,
            taxId: null,
            email: null,
            phone: null,
            status: 'ACTIVE',
            classification: null,
          },
        ],
        '/crm/customers': [
          {
            id: 'cu1',
            companyId: 'c1',
            legalName: 'Cliente persistido',
            tradeName: null,
            taxId: null,
            contactName: null,
            email: null,
            phone: null,
            address: null,
            status: 'ACTIVE',
          },
        ],
        [endpoint]: [invoice],
      })

      render(renderApp(route))

      // El nombre puede aparecer también en el filtro; basta con que la fila
      // de la tabla lo muestre.
      const matches = await screen.findAllByText(visibleText)
      expect(matches.some((el) => el.closest('tr'))).toBe(true)
      expect(fetch).toHaveBeenCalledWith(expect.stringContaining(endpoint), expect.anything())
    },
  )

  it('submits a DRAFT supplier invoice for real approval through the Approval Inbox (DEFERRED-FINAL-016)', async () => {
    const draftInvoice = {
      id: 'ap1',
      supplierId: 's1',
      invoiceNumber: 'AP-SUB-1',
      scope: 'GENERAL',
      currencyCode: 'HNL',
      amount: 125,
      taxAmount: 0,
      amountPaid: 0,
      dueDate: '2026-09-01',
      status: 'DRAFT',
    }
    let submitted = false
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
          return Promise.resolve({
            ok: true,
            status: 200,
            json: async () => [{ id: 'c1', name: 'Constructora Nexora', code: null, legalName: null, functionalCurrencyCode: 'HNL' }],
          } as Response)
        }
        if (url.includes('/procurement/suppliers')) {
          return Promise.resolve({
            ok: true,
            status: 200,
            json: async () => [{ id: 's1', companyId: 'c1', legalName: 'Proveedor persistido', tradeName: null, taxId: null, email: null, phone: null, status: 'ACTIVE', classification: null }],
          } as Response)
        }
        if (url.includes('/master-data/users')) {
          return Promise.resolve({
            ok: true,
            status: 200,
            json: async () => [
              { id: 'u1', email: 'admin@nexora.group', fullName: 'Admin', roles: ['Administrator'] },
              { id: 'u2', email: 'aprobador@nexora.group', fullName: 'Aprobador', roles: ['Finance Manager'] },
            ],
          } as Response)
        }
        if (url.includes('/submit-for-approval')) {
          submitted = true
          return Promise.resolve({
            ok: true,
            status: 200,
            json: async () => ({ ...draftInvoice, status: 'REVIEW' }),
          } as Response)
        }
        if (url.includes('/ap/supplier-invoices')) {
          return Promise.resolve({
            ok: true,
            status: 200,
            json: async () => [submitted ? { ...draftInvoice, status: 'REVIEW' } : draftInvoice],
          } as Response)
        }
        return Promise.resolve({ ok: true, status: 200, json: async () => [] } as Response)
      }),
    )

    render(renderApp('/finanzas/cuentas-por-pagar'))

    await userEvent.click(await screen.findByRole('button', { name: /enviar a aprobación/i }))
    await userEvent.selectOptions(
      await screen.findByLabelText(/usuario aprobador/i),
      'u2',
    )
    await userEvent.click(screen.getByRole('button', { name: /^enviar$/i }))

    expect(await screen.findByText('REVIEW')).toBeInTheDocument()
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/ap/supplier-invoices/ap1/submit-for-approval'),
      expect.objectContaining({ method: 'POST' }),
    )
  })

  it('creates a Treasury account from an available postable ASSET account', async () => {
    let createdPayload: Record<string, unknown> | null = null
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
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
            }),
          } as Response)
        }
        if (url.includes('/master-data/companies')) {
          return Promise.resolve({
            ok: true,
            status: 200,
            json: async () => [
              {
                id: 'c1',
                name: 'NEXORA GROUP',
                code: null,
                legalName: null,
                functionalCurrencyCode: 'HNL',
                country: null,
                fiscalId: null,
              },
            ],
          } as Response)
        }
        if (url.includes('/master-data/accounts')) {
          return Promise.resolve({
            ok: true,
            status: 200,
            json: async () => [
              { id: 'a-bank', code: '1102', name: 'Bancos — HNL', accountType: 'ASSET', parentId: 'a-assets', isPostable: true },
              { id: 'a-assets', code: '1000', name: 'ACTIVOS', accountType: 'ASSET', parentId: null, isPostable: false },
              { id: 'a-expense', code: '6101', name: 'Gastos administrativos generales', accountType: 'EXPENSE', parentId: null, isPostable: true },
            ],
          } as Response)
        }
        if (url.includes('/treasury/accounts')) {
          if (init?.method === 'POST') {
            createdPayload = JSON.parse(String(init.body)) as Record<string, unknown>
            return Promise.resolve({
              ok: true,
              status: 201,
              json: async () => ({
                id: 't1', companyId: 'c1', name: 'Banco principal HNL', kind: 'BANK', institution: 'Banco de Occidente', accountReference: null, currencyCode: 'HNL', glAccountId: 'a-bank', status: 'ACTIVE', balance: '0.00',
              }),
            } as Response)
          }
          return Promise.resolve({ ok: true, status: 200, json: async () => [] } as Response)
        }
        if (url.includes('/treasury/remittances')) {
          return Promise.resolve({ ok: true, status: 200, json: async () => [] } as Response)
        }
        return Promise.resolve({ ok: true, status: 200, json: async () => [] } as Response)
      }),
    )

    render(renderApp('/finanzas/tesoreria'))
    await userEvent.click(await screen.findByRole('button', { name: /nueva cuenta de tesorería/i }))

    expect(screen.getByRole('option', { name: '1102 · Bancos — HNL' })).toBeInTheDocument()
    expect(screen.queryByRole('option', { name: /1000 · ACTIVOS/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('option', { name: /6101 · Gastos administrativos/i })).not.toBeInTheDocument()

    await userEvent.type(screen.getByLabelText(/nombre de la cuenta/i), 'Banco principal HNL')
    await userEvent.type(screen.getByLabelText(/^institución$/i), 'Banco de Occidente')
    await userEvent.click(screen.getByRole('button', { name: /crear cuenta de tesorería/i }))

    await waitFor(() =>
      expect(createdPayload).toMatchObject({
        companyId: 'c1',
        name: 'Banco principal HNL',
        kind: 'BANK',
        currencyCode: 'HNL',
        glAccountId: 'a-bank',
        institution: 'Banco de Occidente',
      }),
    )
  })

})
