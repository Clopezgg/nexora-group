import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

type StubAccount = {
  id: string
  code: string
  name: string
  accountType: string
  parentId: string | null
  isPostable: boolean
  cashFlowActivity: string | null
}

const COMPANY = {
  id: 'c1',
  name: 'NEXORA GROUP',
  code: 'NX',
  legalName: 'Nexora Group S.A.',
  functionalCurrencyCode: 'HNL',
  country: 'HN',
  fiscalId: null,
}

function stubCatalogFetch({
  role = 'Administrator',
  accounts = [],
  companiesStatus = 200,
}: {
  role?: string
  accounts?: StubAccount[]
  companiesStatus?: number
}) {
  const storedAccounts = [...accounts]

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
            email: 'user@nexora.group',
            fullName: 'Usuario',
            roles: [role],
          }),
        } as Response)
      }
      if (url.includes('/master-data/companies')) {
        return Promise.resolve({
          ok: companiesStatus === 200,
          status: companiesStatus,
          json: async () =>
            companiesStatus === 200
              ? [COMPANY]
              : { error: { message: 'No se pudieron cargar las compañías' } },
        } as Response)
      }
      if (url.includes('/master-data/accounts') && init?.method === 'POST') {
        const payload = JSON.parse(String(init.body)) as Record<string, unknown>
        const validPayload =
          payload.companyId === COMPANY.id &&
          payload.code === '1101' &&
          payload.name === 'Cuentas por cobrar' &&
          payload.accountType === 'ASSET' &&
          payload.parentId === 'a-parent'

        if (!validPayload) {
          return Promise.resolve({
            ok: false,
            status: 422,
            json: async () => ({ error: { message: 'Payload inesperado' } }),
          } as Response)
        }

        const created: StubAccount = {
          id: 'a-created',
          code: String(payload.code),
          name: String(payload.name),
          accountType: String(payload.accountType),
          parentId: String(payload.parentId),
          isPostable: true,
          cashFlowActivity: null,
        }
        storedAccounts.push(created)
        return Promise.resolve({ ok: true, status: 201, json: async () => created } as Response)
      }
      if (url.includes('/master-data/accounts')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => storedAccounts,
        } as Response)
      }
      if (url.includes('/reports/trial-balance')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({ rows: [], totalDebit: '0.00', totalCredit: '0.00' }),
        } as Response)
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => ({}) } as Response)
    }),
  )
}

const PARENT_ACCOUNT: StubAccount = {
  id: 'a-parent',
  code: '1100',
  name: 'Activo corriente',
  accountType: 'ASSET',
  parentId: null,
  isPostable: true,
  cashFlowActivity: null,
}

describe('AccountCatalogPage', () => {
  it('lists the active company accounts with translated type, parent and posting status', async () => {
    stubCatalogFetch({
      accounts: [
        PARENT_ACCOUNT,
        {
          id: 'a-child',
          code: '1101',
          name: 'Cuentas por cobrar',
          accountType: 'ASSET',
          parentId: 'a-parent',
          isPostable: true,
          cashFlowActivity: null,
        },
      ],
    })

    render(renderApp('/finanzas/contabilidad'))

    expect(await screen.findByRole('heading', { name: /catálogo de cuentas/i })).toBeInTheDocument()
    const childRow = await screen.findByRole('row', { name: /1101 cuentas por cobrar/i })
    expect(within(childRow).getByText('Activo')).toBeInTheDocument()
    expect(within(childRow).getByText('1100 · Activo corriente')).toBeInTheDocument()
    expect(within(childRow).getByText('Registrable')).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /balance de comprobación/i })).toBeInTheDocument()
  })

  it('creates an account for the active company with an optional parent and refreshes the table', async () => {
    stubCatalogFetch({ accounts: [PARENT_ACCOUNT] })
    const user = userEvent.setup()

    render(renderApp('/finanzas/contabilidad'))

    await user.click(await screen.findByRole('button', { name: /nueva cuenta/i }))
    const dialog = screen.getByRole('dialog', { name: /nueva cuenta contable/i })
    await user.type(within(dialog).getByLabelText(/^código$/i), '1101')
    await user.type(within(dialog).getByLabelText(/^nombre$/i), 'Cuentas por cobrar')
    await user.selectOptions(within(dialog).getByLabelText(/tipo de cuenta/i), 'ASSET')
    await user.selectOptions(within(dialog).getByLabelText(/cuenta padre/i), 'a-parent')
    await user.click(within(dialog).getByRole('button', { name: /crear cuenta/i }))

    expect(await screen.findByRole('row', { name: /1101 cuentas por cobrar/i })).toBeInTheDocument()
    expect(screen.queryByRole('dialog', { name: /nueva cuenta contable/i })).not.toBeInTheDocument()
  })

  it('keeps the catalog read-only for roles without accounting.account:create', async () => {
    stubCatalogFetch({ role: 'Viewer', accounts: [PARENT_ACCOUNT] })

    render(renderApp('/finanzas/contabilidad'))

    expect(await screen.findByText('Activo corriente')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /nueva cuenta/i })).not.toBeInTheDocument()
  })

  it('shows a retryable error instead of claiming there are no companies when loading fails', async () => {
    stubCatalogFetch({ companiesStatus: 500 })

    render(renderApp('/finanzas/contabilidad'))

    expect(await screen.findByRole('alert')).toHaveTextContent(/ocurrió un error/i)
    expect(screen.getByRole('button', { name: /reintentar/i })).toBeInTheDocument()
    expect(screen.queryByText(/configura una compañía primero/i)).not.toBeInTheDocument()
  })

  it('does not add the accounting catalog to the separate Control reports route', async () => {
    stubCatalogFetch({ accounts: [PARENT_ACCOUNT] })

    render(renderApp('/control/reportes'))

    expect(await screen.findByRole('tab', { name: /balance de comprobación/i })).toBeInTheDocument()
    expect(screen.queryByRole('tab', { name: /catálogo de cuentas/i })).not.toBeInTheDocument()
  })
})
