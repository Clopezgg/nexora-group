import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import {
  Badge,
  Button,
  Card,
  CompanySelector,
  EmptyState,
  ErrorState,
  Input,
  LoadingState,
  Modal,
  Select,
  Table,
  type TableColumn,
} from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { masterDataService } from '../../services/masterDataService'
import type { Account } from '../../types/masterData'
import { useAuth } from '../auth/auth-context'

const ACCOUNT_TYPE_LABELS: Record<string, string> = {
  ASSET: 'Activo',
  LIABILITY: 'Pasivo',
  EQUITY: 'Patrimonio',
  REVENUE: 'Ingreso',
  EXPENSE: 'Gasto',
}

const CREATE_ACCOUNT_ROLES = new Set(['Administrator', 'Finance Manager'])

const EMPTY_FORM = {
  code: '',
  name: '',
  accountType: 'ASSET',
  parentId: '',
}

export function AccountCatalogPage() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const {
    companies,
    activeCompanyId,
    setActiveCompanyId,
    isLoading: loadingCompanies,
    isError: companiesError,
    refetch: refetchCompanies,
  } = useActiveCompany()
  const [modalOpen, setModalOpen] = useState(false)
  const [form, setForm] = useState(EMPTY_FORM)

  const accountsQuery = useQuery({
    queryKey: ['master-data', 'accounts', activeCompanyId],
    queryFn: () => masterDataService.listAccounts(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  const createMutation = useMutation({
    mutationFn: () =>
      masterDataService.createAccount({
        companyId: activeCompanyId as string,
        code: form.code.trim(),
        name: form.name.trim(),
        accountType: form.accountType,
        ...(form.parentId ? { parentId: form.parentId } : {}),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['master-data', 'accounts', activeCompanyId],
      })
      setModalOpen(false)
      setForm(EMPTY_FORM)
    },
  })

  if (loadingCompanies) return <LoadingState label="Cargando compañías…" />
  if (companiesError) return <ErrorState onRetry={() => refetchCompanies()} />
  if (companies.length === 0 || !activeCompanyId) {
    return (
      <EmptyState
        icon="book"
        title="Configura una compañía primero"
        description="Cada compañía tendrá su propio catálogo contable aislado."
      />
    )
  }

  const accounts = accountsQuery.data ?? []
  const accountById = new Map(accounts.map((account) => [account.id, account]))
  const canCreateAccount = Boolean(user?.roles.some((role) => CREATE_ACCOUNT_ROLES.has(role)))

  const columns: TableColumn<Account>[] = [
    { key: 'code', header: 'Código', render: (account) => account.code },
    { key: 'name', header: 'Nombre', render: (account) => account.name },
    {
      key: 'accountType',
      header: 'Tipo',
      render: (account) => (
        <Badge tone="info">{ACCOUNT_TYPE_LABELS[account.accountType] ?? account.accountType}</Badge>
      ),
    },
    {
      key: 'parentId',
      header: 'Cuenta padre',
      render: (account) => {
        const parent = account.parentId ? accountById.get(account.parentId) : null
        return parent ? `${parent.code} · ${parent.name}` : '—'
      },
    },
    {
      key: 'isPostable',
      header: 'Estado',
      render: (account) => (
        <Badge tone={account.isPostable ? 'success' : 'neutral'}>
          {account.isPostable ? 'Registrable' : 'No registrable'}
        </Badge>
      ),
    },
  ]

  const handleCompanyChange = (companyId: string | null) => {
    setActiveCompanyId(companyId)
    setModalOpen(false)
    setForm(EMPTY_FORM)
  }

  const closeCreateModal = () => {
    setModalOpen(false)
    setForm(EMPTY_FORM)
    createMutation.reset()
  }

  return (
    <div>
      <header className="nx-page__header">
        <div>
          <h1 className="nx-dashboard__title">Catálogo de cuentas</h1>
          <p className="nx-field__hint">Estructura contable de la compañía seleccionada.</p>
        </div>
        {canCreateAccount ? <Button onClick={() => setModalOpen(true)}>Nueva cuenta</Button> : null}
      </header>

      <Card>
        <CompanySelector
          options={companies.map((company) => ({ id: company.id, label: company.name }))}
          value={activeCompanyId}
          onChange={handleCompanyChange}
        />
      </Card>

      <Card
        title={`Cuentas · ${companies.find((company) => company.id === activeCompanyId)?.name ?? ''}`}
      >
        {accountsQuery.isLoading ? (
          <LoadingState label="Cargando catálogo de cuentas…" />
        ) : accountsQuery.isError ? (
          <ErrorState onRetry={() => accountsQuery.refetch()} />
        ) : (
          <Table
            columns={columns}
            rows={accounts}
            getRowKey={(account) => account.id}
            emptyMessage="Aún no hay cuentas en el catálogo de esta compañía."
          />
        )}
      </Card>

      <Modal open={modalOpen} title="Nueva cuenta contable" onClose={closeCreateModal}>
        <form
          onSubmit={(event) => {
            event.preventDefault()
            createMutation.mutate()
          }}
        >
          <Input
            name="code"
            label="Código"
            value={form.code}
            maxLength={32}
            autoComplete="off"
            onChange={(event) => setForm((current) => ({ ...current, code: event.target.value }))}
            required
          />
          <Input
            name="name"
            label="Nombre"
            value={form.name}
            maxLength={255}
            autoComplete="off"
            onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
            required
          />
          <Select
            name="accountType"
            label="Tipo de cuenta"
            value={form.accountType}
            onChange={(event) =>
              setForm((current) => ({ ...current, accountType: event.target.value }))
            }
            required
          >
            {Object.entries(ACCOUNT_TYPE_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </Select>
          <Select
            name="parentId"
            label="Cuenta padre"
            value={form.parentId}
            onChange={(event) =>
              setForm((current) => ({ ...current, parentId: event.target.value }))
            }
          >
            <option value="">Sin cuenta padre</option>
            {accounts.map((account) => (
              <option key={account.id} value={account.id}>
                {account.code} · {account.name}
              </option>
            ))}
          </Select>

          {createMutation.isError ? (
            <p className="nx-field__error" role="alert">
              {(createMutation.error as Error).message}
            </p>
          ) : null}

          <Button
            type="submit"
            loading={createMutation.isPending}
            disabled={!form.code.trim() || !form.name.trim()}
          >
            Crear cuenta
          </Button>
        </form>
      </Modal>
    </div>
  )
}
