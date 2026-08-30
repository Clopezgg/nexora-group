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
            permissions:
              role === 'Viewer'
                ? ['accounting.journal_entry:read', 'accounting.account:read']
                : [],
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
          payload.parentId === 'a-parent' &&
          payload.isPostable === true

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
          isPostable: Boolean(payload.isPostable),
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
  isPostable: false,
  cashFlowActivity: null,
}

describe('AccountCatalogPage', () => {
  it('renders parent/child accounts as an ordered visual hierarchy with posting status', async () => {
    const child: StubAccount = {
      id: 'a-child',
      code: '1101',
      name: 'Cuentas por cobrar',
      accountType: 'ASSET',
      parentId: 'a-parent',
      isPostable: true,
      cashFlowActivity: null,
    }
    // Deliberately return the child first: the UI must build the hierarchy
    // from parentId rather than trusting API array order.
    stubCatalogFetch({ accounts: [child, PARENT_ACCOUNT] })

    render(renderApp('/finanzas/contabilidad'))

    expect(await screen.findByRole('heading', { name: /catálogo de cuentas/i })).toBeInTheDocument()
    const parentRow = await screen.findByRole('row', { name: /1100 activo corriente/i })
    const childRow = await screen.findByRole('row', { name: /1101 cuentas por cobrar/i })
    const parentName = within(parentRow).getByText('Activo corriente')
    const childName = within(childRow).getByText('Cuentas por cobrar')

    expect(parentName).toHaveAttribute('data-account-depth', '0')
    expect(childName).toHaveAttribute('data-account-depth', '1')
    expect(parentRow.compareDocumentPosition(childRow) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(within(parentRow).getByText('Agrupadora')).toBeInTheDocument()
    expect(within(childRow).getByText('Activo')).toBeInTheDocument()
    expect(within(childRow).getByText('1100 · Activo corriente')).toBeInTheDocument()
    expect(within(childRow).getByText('Registrable')).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /balance de comprobación/i })).toBeInTheDocument()
  })

  it('creates a registrable account under an eligible grouping parent', async () => {
    stubCatalogFetch({ accounts: [PARENT_ACCOUNT] })
    const user = userEvent.setup()

    render(renderApp('/finanzas/contabilidad'))

    await user.click(await screen.findByRole('button', { name: /nueva cuenta/i }))
    const dialog = screen.getByRole('dialog', { name: /nueva cuenta contable/i })
    expect(within(dialog).getByLabelText(/uso de la cuenta/i)).toHaveValue('postable')
    await user.type(within(dialog).getByLabelText(/^código$/i), '1101')
    await user.type(within(dialog).getByLabelText(/^nombre$/i), 'Cuentas por cobrar')
    await user.selectOptions(within(dialog).getByLabelText(/tipo de cuenta/i), 'ASSET')
    await user.selectOptions(within(dialog).getByLabelText(/cuenta padre/i), 'a-parent')
    await user.click(within(dialog).getByRole('button', { name: /crear cuenta/i }))

    expect(await screen.findByRole('row', { name: /1101 cuentas por cobrar/i })).toBeInTheDocument()
    expect(screen.queryByRole('dialog', { name: /nueva cuenta contable/i })).not.toBeInTheDocument()
  })

  it('offers only non-postable parents of the same account type', async () => {
    stubCatalogFetch({
      accounts: [
        PARENT_ACCOUNT,
        {
          id: 'asset-postable',
          code: '1199',
          name: 'Activo operativo',
          accountType: 'ASSET',
          parentId: null,
          isPostable: true,
          cashFlowActivity: null,
        },
        {
          id: 'liability-group',
          code: '2000',
          name: 'PASIVOS',
          accountType: 'LIABILITY',
          parentId: null,
          isPostable: false,
          cashFlowActivity: null,
        },
      ],
    })
    const user = userEvent.setup()

    render(renderApp('/finanzas/contabilidad'))
    await user.click(await screen.findByRole('button', { name: /nueva cuenta/i }))
    const parentSelect = within(screen.getByRole('dialog')).getByLabelText(/cuenta padre/i)

    expect(within(parentSelect).getByRole('option', { name: /1100 · activo corriente/i })).toBeInTheDocument()
    expect(within(parentSelect).queryByRole('option', { name: /1199 · activo operativo/i })).not.toBeInTheDocument()
    expect(within(parentSelect).queryByRole('option', { name: /2000 · pasivos/i })).not.toBeInTheDocument()
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
