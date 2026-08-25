import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Button,
  Card,
  EmptyState,
  ErrorState,
  LoadingState,
  Modal,
  MoneyInput,
  Select,
  StatCard,
  Table,
  type TableColumn,
} from '../../design-system'
import { masterDataService } from '../../services/masterDataService'
import { treasuryService } from '../../services/treasuryService'
import type { TreasuryAccount } from '../../types/treasury'
import './TreasuryPage.css'

const currencyFormatter = new Intl.NumberFormat('es-HN', {
  style: 'currency',
  currency: 'HNL',
  maximumFractionDigits: 2,
})

type ModalKind = 'remittance' | 'expense' | 'transfer' | null

export function TreasuryPage() {
  const queryClient = useQueryClient()
  const [companyId, setCompanyId] = useState<string | null>(null)
  const [openModal, setOpenModal] = useState<ModalKind>(null)

  const companiesQuery = useQuery({
    queryKey: ['master-data', 'companies'],
    queryFn: masterDataService.listCompanies,
  })
  const companies = companiesQuery.data ?? []
  const activeCompanyId = companyId ?? companies[0]?.id ?? null

  const accountsQuery = useQuery({
    queryKey: ['master-data', 'accounts', activeCompanyId],
    queryFn: () => masterDataService.listAccounts(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })
  const treasuryAccountsQuery = useQuery({
    queryKey: ['treasury', 'accounts', activeCompanyId],
    queryFn: () => treasuryService.listAccounts(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  const quickStart = useMutation({
    mutationFn: async () => {
      const company = await masterDataService.createCompany({
        name: 'Constructora Nexora',
        functionalCurrencyCode: 'HNL',
      })
      const bank = await masterDataService.createAccount({
        companyId: company.id,
        code: '1100',
        name: 'Bancos',
        accountType: 'ASSET',
      })
      await masterDataService.createAccount({
        companyId: company.id,
        code: '3100',
        name: 'Aportes de socios',
        accountType: 'EQUITY',
      })
      await masterDataService.createAccount({
        companyId: company.id,
        code: '5100',
        name: 'Gastos administrativos',
        accountType: 'EXPENSE',
      })
      await treasuryService.createAccount({
        companyId: company.id,
        name: 'Banco Principal',
        kind: 'BANK',
        currencyCode: 'HNL',
        glAccountId: bank.id,
      })
      return company
    },
    onSuccess: (company) => {
      setCompanyId(company.id)
      queryClient.invalidateQueries({ queryKey: ['master-data', 'companies'] })
    },
  })

  if (companiesQuery.isLoading) return <LoadingState label="Cargando compañías…" />
  if (companiesQuery.isError) {
    return (
      <ErrorState title="No se pudo cargar Tesorería" onRetry={() => companiesQuery.refetch()} />
    )
  }

  if (companies.length === 0) {
    return (
      <div className="nx-treasury">
        <EmptyState
          icon="🏦"
          title="Aún no hay ninguna compañía configurada"
          description="Crea la primera compañía y su catálogo mínimo de cuentas para empezar a operar Tesorería (NXR-REQ-0002)."
        />
        <Button loading={quickStart.isPending} onClick={() => quickStart.mutate()}>
          Crear compañía y cuentas de inicio
        </Button>
      </div>
    )
  }

  const glAccounts = accountsQuery.data ?? []
  const treasuryAccounts = treasuryAccountsQuery.data ?? []

  const columns: TableColumn<TreasuryAccount>[] = [
    { key: 'name', header: 'Cuenta', render: (row) => row.name },
    { key: 'kind', header: 'Tipo', render: (row) => row.kind },
    { key: 'currency', header: 'Moneda', render: (row) => row.currencyCode },
    {
      key: 'balance',
      header: 'Saldo',
      render: (row) => currencyFormatter.format(row.balance),
    },
  ]

  const totalBalance = treasuryAccounts.reduce((sum, account) => sum + account.balance, 0)

  return (
    <div className="nx-treasury">
      <header className="nx-treasury__header">
        <h1 className="nx-dashboard__title">Tesorería</h1>
        <Select
          aria-label="Compañía activa"
          value={activeCompanyId ?? ''}
          onChange={(event) => setCompanyId(event.target.value)}
        >
          {companies.map((company) => (
            <option key={company.id} value={company.id}>
              {company.name}
            </option>
          ))}
        </Select>
      </header>

      <div className="nx-treasury__grid">
        <StatCard label="Saldo total de Tesorería" value={currencyFormatter.format(totalBalance)} />
        <StatCard label="Cuentas de tesorería" value={treasuryAccounts.length} />
      </div>

      <Card title="Acciones">
        <div className="nx-treasury__actions">
          <Button variant="secondary" onClick={() => setOpenModal('remittance')}>
            Registrar remesa
          </Button>
          <Button variant="secondary" onClick={() => setOpenModal('expense')}>
            Registrar gasto general
          </Button>
          <Button
            variant="secondary"
            onClick={() => setOpenModal('transfer')}
            disabled={treasuryAccounts.length < 2}
          >
            Transferencia entre cuentas
          </Button>
        </div>
      </Card>

      {treasuryAccountsQuery.isLoading ? (
        <LoadingState label="Cargando cuentas de tesorería…" />
      ) : (
        <Table
          columns={columns}
          rows={treasuryAccounts}
          getRowKey={(row) => row.id}
          emptyMessage="Aún no hay cuentas de tesorería para esta compañía."
        />
      )}

      {openModal === 'remittance' && activeCompanyId ? (
        <RemittanceModal
          companyId={activeCompanyId}
          treasuryAccounts={treasuryAccounts}
          counterAccounts={glAccounts}
          onClose={() => setOpenModal(null)}
        />
      ) : null}
      {openModal === 'expense' && activeCompanyId ? (
        <GeneralExpenseModal
          companyId={activeCompanyId}
          treasuryAccounts={treasuryAccounts}
          expenseAccounts={glAccounts.filter((a) => a.accountType === 'EXPENSE')}
          onClose={() => setOpenModal(null)}
        />
      ) : null}
      {openModal === 'transfer' && activeCompanyId ? (
        <TransferModal
          companyId={activeCompanyId}
          treasuryAccounts={treasuryAccounts}
          onClose={() => setOpenModal(null)}
        />
      ) : null}
    </div>
  )
}

function RemittanceModal({
  companyId,
  treasuryAccounts,
  counterAccounts,
  onClose,
}: {
  companyId: string
  treasuryAccounts: TreasuryAccount[]
  counterAccounts: { id: string; name: string }[]
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const [treasuryAccountId, setTreasuryAccountId] = useState(treasuryAccounts[0]?.id ?? '')
  const [counterAccountId, setCounterAccountId] = useState(counterAccounts[0]?.id ?? '')
  const [sender, setSender] = useState('')
  const [amount, setAmount] = useState<number | null>(null)

  const mutation = useMutation({
    mutationFn: () =>
      treasuryService.createRemittance({
        companyId,
        treasuryAccountId,
        counterAccountId,
        sender,
        currencyCode: 'HNL',
        originalAmount: String(amount ?? 0),
        remittanceDate: new Date().toISOString().slice(0, 10),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['treasury', 'accounts'] })
      onClose()
    },
  })

  return (
    <Modal open title="Registrar remesa" onClose={onClose}>
      <form
        className="nx-treasury__form"
        onSubmit={(event) => {
          event.preventDefault()
          mutation.mutate()
        }}
      >
        <Select
          label="Cuenta de tesorería"
          value={treasuryAccountId}
          onChange={(e) => setTreasuryAccountId(e.target.value)}
        >
          {treasuryAccounts.map((account) => (
            <option key={account.id} value={account.id}>
              {account.name}
            </option>
          ))}
        </Select>
        <Select
          label="Cuenta contrapartida"
          value={counterAccountId}
          onChange={(e) => setCounterAccountId(e.target.value)}
        >
          {counterAccounts.map((account) => (
            <option key={account.id} value={account.id}>
              {account.name}
            </option>
          ))}
        </Select>
        <label className="nx-field">
          <span className="nx-field__label">Remitente</span>
          <input
            className="nx-input"
            value={sender}
            onChange={(event) => setSender(event.target.value)}
            required
          />
        </label>
        <MoneyInput label="Monto" value={amount} onChange={setAmount} />
        {mutation.isError ? (
          <p className="nx-field__error">{(mutation.error as Error).message}</p>
        ) : null}
        <Button
          type="submit"
          loading={mutation.isPending}
          disabled={!treasuryAccountId || !counterAccountId || !amount}
        >
          Registrar
        </Button>
      </form>
    </Modal>
  )
}

function GeneralExpenseModal({
  companyId,
  treasuryAccounts,
  expenseAccounts,
  onClose,
}: {
  companyId: string
  treasuryAccounts: TreasuryAccount[]
  expenseAccounts: { id: string; name: string }[]
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const [treasuryAccountId, setTreasuryAccountId] = useState(treasuryAccounts[0]?.id ?? '')
  const [expenseAccountId, setExpenseAccountId] = useState(expenseAccounts[0]?.id ?? '')
  const [category, setCategory] = useState('papeleria')
  const [description, setDescription] = useState('')
  const [amount, setAmount] = useState<number | null>(null)

  const mutation = useMutation({
    mutationFn: () =>
      treasuryService.createGeneralExpense({
        companyId,
        treasuryAccountId,
        expenseAccountId,
        category,
        amount: String(amount ?? 0),
        currencyCode: 'HNL',
        expenseDate: new Date().toISOString().slice(0, 10),
        description,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['treasury', 'accounts'] })
      onClose()
    },
  })

  if (expenseAccounts.length === 0) {
    return (
      <Modal open title="Registrar gasto general" onClose={onClose}>
        <EmptyState title="No hay cuentas de gasto (EXPENSE) configuradas todavía." />
      </Modal>
    )
  }

  return (
    <Modal open title="Registrar gasto general" onClose={onClose}>
      <form
        className="nx-treasury__form"
        onSubmit={(event) => {
          event.preventDefault()
          mutation.mutate()
        }}
      >
        <Select
          label="Cuenta de tesorería"
          value={treasuryAccountId}
          onChange={(e) => setTreasuryAccountId(e.target.value)}
        >
          {treasuryAccounts.map((account) => (
            <option key={account.id} value={account.id}>
              {account.name}
            </option>
          ))}
        </Select>
        <Select
          label="Cuenta de gasto"
          value={expenseAccountId}
          onChange={(e) => setExpenseAccountId(e.target.value)}
        >
          {expenseAccounts.map((account) => (
            <option key={account.id} value={account.id}>
              {account.name}
            </option>
          ))}
        </Select>
        <label className="nx-field">
          <span className="nx-field__label">Categoría</span>
          <input
            className="nx-input"
            value={category}
            onChange={(event) => setCategory(event.target.value)}
            required
          />
        </label>
        <label className="nx-field">
          <span className="nx-field__label">Descripción</span>
          <input
            className="nx-input"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            required
          />
        </label>
        <MoneyInput label="Monto" value={amount} onChange={setAmount} />
        {mutation.isError ? (
          <p className="nx-field__error">{(mutation.error as Error).message}</p>
        ) : null}
        <Button type="submit" loading={mutation.isPending} disabled={!amount}>
          Registrar
        </Button>
      </form>
    </Modal>
  )
}

function TransferModal({
  companyId,
  treasuryAccounts,
  onClose,
}: {
  companyId: string
  treasuryAccounts: TreasuryAccount[]
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const [sourceId, setSourceId] = useState(treasuryAccounts[0]?.id ?? '')
  const [destinationId, setDestinationId] = useState(
    treasuryAccounts[1]?.id ?? treasuryAccounts[0]?.id ?? '',
  )
  const [amount, setAmount] = useState<number | null>(null)

  const source = treasuryAccounts.find((a) => a.id === sourceId)

  const mutation = useMutation({
    mutationFn: () =>
      treasuryService.createTransfer({
        companyId,
        sourceTreasuryAccountId: sourceId,
        destinationTreasuryAccountId: destinationId,
        amount: String(amount ?? 0),
        currencyCode: source?.currencyCode ?? 'HNL',
        transferDate: new Date().toISOString().slice(0, 10),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['treasury', 'accounts'] })
      onClose()
    },
  })

  return (
    <Modal open title="Transferencia entre cuentas de tesorería" onClose={onClose}>
      <form
        className="nx-treasury__form"
        onSubmit={(event) => {
          event.preventDefault()
          mutation.mutate()
        }}
      >
        <Select label="Origen" value={sourceId} onChange={(e) => setSourceId(e.target.value)}>
          {treasuryAccounts.map((account) => (
            <option key={account.id} value={account.id}>
              {account.name}
            </option>
          ))}
        </Select>
        <Select
          label="Destino"
          value={destinationId}
          onChange={(e) => setDestinationId(e.target.value)}
        >
          {treasuryAccounts.map((account) => (
            <option key={account.id} value={account.id}>
              {account.name}
            </option>
          ))}
        </Select>
        <MoneyInput label="Monto" value={amount} onChange={setAmount} />
        {mutation.isError ? (
          <p className="nx-field__error">{(mutation.error as Error).message}</p>
        ) : null}
        <Button
          type="submit"
          loading={mutation.isPending}
          disabled={!amount || sourceId === destinationId}
        >
          Transferir
        </Button>
      </form>
    </Modal>
  )
}
