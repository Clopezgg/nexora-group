import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  Input,
  LoadingState,
  Modal,
  MoneyInput,
  Select,
  StatCard,
  Table,
  type TableColumn,
} from '../../design-system'
import { masterDataService } from '../../services/masterDataService'
import {
  treasuryService,
  type CreateGeneralExpensePayload,
  type CreateRemittancePayload,
  type CreateTransferPayload,
} from '../../services/treasuryService'
import type { Account } from '../../types/masterData'
import type { Remittance, TreasuryAccount } from '../../types/treasury'
import { formatMoney } from '../../utils/currency'
import { useAuth } from '../auth/auth-context'
import './TreasuryPage.css'

type ModalKind = 'account' | 'remittance' | 'expense' | 'transfer' | null
const REMITTANCE_PAGE_SIZE = 25
const CREATE_TREASURY_ACCOUNT_ROLES = new Set(['Administrator', 'Finance Manager'])
const TREASURY_KIND_LABELS: Record<TreasuryAccount['kind'], string> = {
  BANK: 'Banco',
  CASH: 'Caja',
  OTHER: 'Otra',
}

export function TreasuryPage() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [companyId, setCompanyId] = useState<string | null>(null)
  const [openModal, setOpenModal] = useState<ModalKind>(null)
  const [remittanceOffset, setRemittanceOffset] = useState(0)

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
  const remittancesQuery = useQuery({
    queryKey: ['treasury', 'remittances', activeCompanyId, remittanceOffset],
    queryFn: () =>
      treasuryService.listRemittances(
        activeCompanyId as string,
        remittanceOffset,
        REMITTANCE_PAGE_SIZE,
      ),
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
      setRemittanceOffset(0)
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
        <header className="nx-treasury__header">
          <h1 className="nx-dashboard__title">Tesorería</h1>
        </header>
        <EmptyState
          icon="bank"
          title="Aún no hay ninguna compañía configurada"
          description="Crea la primera compañía y su catálogo mínimo de cuentas para empezar a operar Tesorería."
        />
        <Button loading={quickStart.isPending} onClick={() => quickStart.mutate()}>
          Crear compañía y cuentas de inicio
        </Button>
      </div>
    )
  }

  const glAccounts = accountsQuery.data ?? []
  const treasuryAccounts = treasuryAccountsQuery.data ?? []
  const remittances = remittancesQuery.data ?? []
  const assignedGlAccountIds = new Set(treasuryAccounts.map((account) => account.glAccountId))
  const availableTreasuryGlAccounts = glAccounts.filter(
    (account) =>
      account.isPostable &&
      account.accountType === 'ASSET' &&
      !assignedGlAccountIds.has(account.id),
  )
  const canCreateTreasuryAccount = Boolean(
    user?.roles.some((role) => CREATE_TREASURY_ACCOUNT_ROLES.has(role)),
  )

  const columns: TableColumn<TreasuryAccount>[] = [
    { key: 'name', header: 'Cuenta', render: (row) => row.name },
    { key: 'kind', header: 'Tipo', render: (row) => TREASURY_KIND_LABELS[row.kind] ?? row.kind },
    { key: 'currency', header: 'Moneda', render: (row) => row.currencyCode },
    {
      key: 'balance',
      header: 'Saldo',
      render: (row) => formatMoney(row.balance, row.currencyCode),
    },
  ]

  const accountNameById = new Map(treasuryAccounts.map((account) => [account.id, account.name]))
  const remittanceColumns: TableColumn<Remittance>[] = [
    { key: 'date', header: 'Fecha', render: (row) => row.remittanceDate },
    {
      key: 'document',
      header: 'Documento',
      render: (row) => row.reference ?? row.accountingDocumentId.slice(0, 8).toUpperCase(),
    },
    { key: 'sender', header: 'Remitente', render: (row) => row.sender },
    {
      key: 'account',
      header: 'Cuenta',
      render: (row) => accountNameById.get(row.treasuryAccountId) ?? 'Cuenta de tesorería',
    },
    {
      key: 'amount',
      header: 'Importe',
      render: (row) => formatMoney(row.originalAmount, row.currencyCode),
    },
    {
      key: 'method',
      header: 'Método / canal',
      render: (row) => row.channel ?? row.provider ?? '—',
    },
    {
      key: 'status',
      header: 'Estado',
      render: () => <Badge tone="success">Contabilizada</Badge>,
    },
  ]

  const balancesByCurrency = treasuryAccounts.reduce<Map<string, number>>((totals, account) => {
    totals.set(account.currencyCode, (totals.get(account.currencyCode) ?? 0) + account.balance)
    return totals
  }, new Map())
  const hnlBalance = balancesByCurrency.get('HNL') ?? 0
  const secondaryBalances = [...balancesByCurrency.entries()].filter(([currency]) => currency !== 'HNL')
  const remittanceCounterAccounts = glAccounts.filter(
    (account) => account.isPostable && !assignedGlAccountIds.has(account.id),
  )
  const remittancePage = Math.floor(remittanceOffset / REMITTANCE_PAGE_SIZE) + 1

  return (
    <div className="nx-treasury">
      <header className="nx-treasury__header">
        <h1 className="nx-dashboard__title">Tesorería</h1>
        <Select
          aria-label="Compañía activa"
          value={activeCompanyId ?? ''}
          onChange={(event) => {
            setCompanyId(event.target.value)
            setRemittanceOffset(0)
          }}
        >
          {companies.map((company) => (
            <option key={company.id} value={company.id}>
              {company.name}
            </option>
          ))}
        </Select>
      </header>

      <div className="nx-treasury__grid">
        <StatCard label="Saldo total HNL" value={formatMoney(hnlBalance)} />
        <StatCard label="Cuentas de tesorería" value={treasuryAccounts.length} />
        {secondaryBalances.map(([currency, balance]) => (
          <StatCard key={currency} label={`Saldo ${currency}`} value={formatMoney(balance, currency)} />
        ))}
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

      <Card title="Cuentas de Tesorería">
        {canCreateTreasuryAccount ? (
          <div className="nx-treasury__actions">
            <Button onClick={() => setOpenModal('account')}>Nueva cuenta de Tesorería</Button>
          </div>
        ) : null}
        {treasuryAccountsQuery.isLoading ? (
          <LoadingState label="Cargando cuentas de tesorería…" />
        ) : treasuryAccountsQuery.isError ? (
          <ErrorState
            title="No se pudieron cargar las cuentas de Tesorería"
            onRetry={() => treasuryAccountsQuery.refetch()}
          />
        ) : (
          <Table
            columns={columns}
            rows={treasuryAccounts}
            getRowKey={(row) => row.id}
            emptyMessage="No hay cuentas de tesorería para esta compañía."
          />
        )}
      </Card>

      <Card title="Remesas">
        {remittancesQuery.isLoading ? (
          <LoadingState label="Cargando remesas…" />
        ) : remittancesQuery.isError ? (
          <ErrorState
            title="No se pudieron cargar las remesas"
            onRetry={() => remittancesQuery.refetch()}
          />
        ) : (
          <>
            <Table
              columns={remittanceColumns}
              rows={remittances}
              getRowKey={(row) => row.id}
              emptyMessage="No hay remesas registradas para esta compañía."
            />
            <div className="nx-treasury__actions" aria-label="Paginación de remesas">
              <Button
                variant="secondary"
                disabled={remittanceOffset === 0}
                onClick={() =>
                  setRemittanceOffset((current) => Math.max(0, current - REMITTANCE_PAGE_SIZE))
                }
              >
                Anterior
              </Button>
              <span>Página {remittancePage}</span>
              <Button
                variant="secondary"
                disabled={remittances.length < REMITTANCE_PAGE_SIZE}
                onClick={() =>
                  setRemittanceOffset((current) => current + REMITTANCE_PAGE_SIZE)
                }
              >
                Siguiente
              </Button>
            </div>
          </>
        )}
      </Card>

      {openModal === 'account' && activeCompanyId ? (
        <TreasuryAccountModal
          companyId={activeCompanyId}
          glAccounts={availableTreasuryGlAccounts}
          onClose={() => setOpenModal(null)}
        />
      ) : null}
      {openModal === 'remittance' && activeCompanyId ? (
        <RemittanceModal
          companyId={activeCompanyId}
          treasuryAccounts={treasuryAccounts}
          counterAccounts={remittanceCounterAccounts}
          onClose={() => setOpenModal(null)}
        />
      ) : null}
      {openModal === 'expense' && activeCompanyId ? (
        <GeneralExpenseModal
          companyId={activeCompanyId}
          treasuryAccounts={treasuryAccounts}
          expenseAccounts={glAccounts.filter((a) => a.isPostable && a.accountType === 'EXPENSE')}
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


function TreasuryAccountModal({
  companyId,
  glAccounts,
  onClose,
}: {
  companyId: string
  glAccounts: Account[]
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const [name, setName] = useState('')
  const [kind, setKind] = useState<TreasuryAccount['kind']>('BANK')
  const [currencyCode, setCurrencyCode] = useState('HNL')
  const [glAccountId, setGlAccountId] = useState(glAccounts[0]?.id ?? '')
  const [institution, setInstitution] = useState('')
  const [accountReference, setAccountReference] = useState('')

  const mutation = useMutation({
    mutationFn: () =>
      treasuryService.createAccount({
        companyId,
        name: name.trim(),
        kind,
        currencyCode,
        glAccountId,
        institution: institution.trim() || null,
        accountReference: accountReference.trim() || null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['treasury', 'accounts', companyId] })
      onClose()
    },
  })

  if (glAccounts.length === 0) {
    return (
      <Modal open title="Nueva cuenta de Tesorería" onClose={onClose}>
        <EmptyState
          icon="bank"
          title="No hay cuentas contables disponibles"
          description="Crea primero una cuenta contable registrable de tipo Activo, como 1102 Bancos — HNL o 1101 Caja y efectivo. Las cuentas agrupadoras no pueden vincularse a Tesorería."
        />
      </Modal>
    )
  }

  return (
    <Modal open title="Nueva cuenta de Tesorería" onClose={onClose}>
      <form
        className="nx-treasury__form"
        onSubmit={(event) => {
          event.preventDefault()
          mutation.mutate()
        }}
      >
        <Input
          name="treasuryAccountName"
          label="Nombre de la cuenta"
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder={kind === 'CASH' ? 'Ej. Caja general' : 'Ej. Banco principal HNL'}
          required
        />
        <Select
          name="treasuryAccountKind"
          label="Tipo de cuenta"
          value={kind}
          onChange={(event) => setKind(event.target.value as TreasuryAccount['kind'])}
          required
        >
          {Object.entries(TREASURY_KIND_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </Select>
        <Select
          name="currencyCode"
          label="Moneda"
          value={currencyCode}
          onChange={(event) => setCurrencyCode(event.target.value)}
          required
        >
          <option value="HNL">HNL — Lempira hondureño</option>
          <option value="USD">USD — Dólar estadounidense</option>
        </Select>
        <Select
          name="glAccountId"
          label="Cuenta contable vinculada"
          value={glAccountId}
          onChange={(event) => setGlAccountId(event.target.value)}
          required
        >
          {glAccounts.map((account) => (
            <option key={account.id} value={account.id}>
              {account.code} · {account.name}
            </option>
          ))}
        </Select>
        <p className="nx-field__hint">
          Solo aparecen cuentas registrables de tipo Activo que todavía no están vinculadas a otra
          cuenta de Tesorería.
        </p>
        <Input
          name="institution"
          label="Institución"
          value={institution}
          onChange={(event) => setInstitution(event.target.value)}
          placeholder="Opcional, ej. Banco de Occidente"
        />
        <Input
          name="accountReference"
          label="Referencia / número de cuenta"
          value={accountReference}
          onChange={(event) => setAccountReference(event.target.value)}
          placeholder="Opcional"
        />
        {mutation.isError ? (
          <p className="nx-field__error" role="alert">
            {(mutation.error as Error).message}
          </p>
        ) : null}
        <Button
          type="submit"
          loading={mutation.isPending}
          disabled={!name.trim() || !glAccountId || !currencyCode}
        >
          Crear cuenta de Tesorería
        </Button>
      </form>
    </Modal>
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
  const [provider, setProvider] = useState('')
  const [channel, setChannel] = useState('TRANSFER')
  const [reference, setReference] = useState('')
  const [notes, setNotes] = useState('')
  const [remittanceDate, setRemittanceDate] = useState(new Date().toISOString().slice(0, 10))
  const [amount, setAmount] = useState<number | null>(null)
  const [fxRate, setFxRate] = useState(1)

  const selectedTreasuryAccount = treasuryAccounts.find((account) => account.id === treasuryAccountId)
  const selectedCurrency = selectedTreasuryAccount?.currencyCode ?? 'HNL'

  const mutation = useMutation({
    mutationFn: ({
      payload,
      idempotencyKey,
    }: {
      payload: CreateRemittancePayload
      idempotencyKey: string
    }) => treasuryService.createRemittance(payload, idempotencyKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['treasury', 'accounts'] })
      queryClient.invalidateQueries({ queryKey: ['treasury', 'remittances'] })
      onClose()
    },
  })

  if (treasuryAccounts.length === 0 || counterAccounts.length === 0) {
    return (
      <Modal open title="Registrar remesa" onClose={onClose}>
        <EmptyState
          title="Faltan cuentas para registrar la remesa"
          description="Configura una cuenta de Tesorería y una cuenta contable de contrapartida distinta antes de continuar."
        />
      </Modal>
    )
  }

  return (
    <Modal open title="Registrar remesa" onClose={onClose}>
      <form
        className="nx-treasury__form"
        onSubmit={(event) => {
          event.preventDefault()
          mutation.mutate({
            payload: {
              companyId,
              treasuryAccountId,
              counterAccountId,
              sender,
              provider: provider || null,
              channel: channel || null,
              reference: reference || null,
              currencyCode: selectedCurrency,
              originalAmount: String(amount ?? 0),
              fxRate: String(selectedCurrency === 'HNL' ? 1 : fxRate),
              remittanceDate,
              notes: notes || null,
            },
            idempotencyKey: crypto.randomUUID(),
          })
        }}
      >
        <Select
          name="treasuryAccountId"
          label="Cuenta de tesorería"
          value={treasuryAccountId}
          onChange={(event) => {
            setTreasuryAccountId(event.target.value)
            setFxRate(1)
          }}
        >
          {treasuryAccounts.map((account) => (
            <option key={account.id} value={account.id}>
              {account.name} — {account.currencyCode}
            </option>
          ))}
        </Select>
        <Select
          name="counterAccountId"
          label="Cuenta contrapartida"
          value={counterAccountId}
          onChange={(event) => setCounterAccountId(event.target.value)}
        >
          {counterAccounts.map((account) => (
            <option key={account.id} value={account.id}>
              {account.name}
            </option>
          ))}
        </Select>
        <label className="nx-field">
          <span className="nx-field__label">Fecha</span>
          <input
            className="nx-input"
            type="date"
            value={remittanceDate}
            onChange={(event) => setRemittanceDate(event.target.value)}
            required
          />
        </label>
        <label className="nx-field">
          <span className="nx-field__label">Documento / referencia</span>
          <input
            className="nx-input"
            value={reference}
            onChange={(event) => setReference(event.target.value)}
            placeholder="Ej. REM-2026-001"
          />
        </label>
        <label className="nx-field">
          <span className="nx-field__label">Remitente</span>
          <input
            className="nx-input"
            value={sender}
            onChange={(event) => setSender(event.target.value)}
            required
          />
        </label>
        <label className="nx-field">
          <span className="nx-field__label">Banco / proveedor</span>
          <input
            className="nx-input"
            value={provider}
            onChange={(event) => setProvider(event.target.value)}
            placeholder="Opcional"
          />
        </label>
        <Select
          name="channel"
          label="Método / canal"
          value={channel}
          onChange={(event) => setChannel(event.target.value)}
        >
          <option value="TRANSFER">Transferencia</option>
          <option value="CASH">Efectivo</option>
          <option value="CHECK">Cheque</option>
          <option value="OTHER">Otro</option>
        </Select>
        <MoneyInput label={`Monto (${selectedCurrency})`} value={amount} onChange={setAmount} />
        {selectedCurrency !== 'HNL' ? (
          <label className="nx-field">
            <span className="nx-field__label">Tipo de cambio a HNL</span>
            <input
              className="nx-input"
              type="number"
              min="0.000001"
              step="0.000001"
              value={fxRate}
              onChange={(event) => setFxRate(Number(event.target.value))}
              required
            />
          </label>
        ) : null}
        <label className="nx-field">
          <span className="nx-field__label">Notas</span>
          <input
            className="nx-input"
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            placeholder="Opcional"
          />
        </label>
        {mutation.isError ? (
          <p className="nx-field__error">{(mutation.error as Error).message}</p>
        ) : null}
        <Button
          type="submit"
          loading={mutation.isPending}
          disabled={
            !treasuryAccountId ||
            !counterAccountId ||
            !sender.trim() ||
            !remittanceDate ||
            !amount ||
            amount <= 0 ||
            (selectedCurrency !== 'HNL' && fxRate <= 0)
          }
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
    mutationFn: ({
      payload,
      idempotencyKey,
    }: {
      payload: CreateGeneralExpensePayload
      idempotencyKey: string
    }) => treasuryService.createGeneralExpense(payload, idempotencyKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['treasury', 'accounts'] })
      onClose()
    },
  })

  if (expenseAccounts.length === 0) {
    return (
      <Modal open title="Registrar gasto general" onClose={onClose}>
        <EmptyState title="No hay cuentas de gasto configuradas todavía." />
      </Modal>
    )
  }

  return (
    <Modal open title="Registrar gasto general" onClose={onClose}>
      <form
        className="nx-treasury__form"
        onSubmit={(event) => {
          event.preventDefault()
          mutation.mutate({
            payload: {
              companyId,
              treasuryAccountId,
              expenseAccountId,
              category,
              amount: String(amount ?? 0),
              currencyCode: 'HNL',
              expenseDate: new Date().toISOString().slice(0, 10),
              description,
            },
            idempotencyKey: crypto.randomUUID(),
          })
        }}
      >
        <Select
          name="treasuryAccountId"
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
          name="expenseAccountId"
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
    mutationFn: ({
      payload,
      idempotencyKey,
    }: {
      payload: CreateTransferPayload
      idempotencyKey: string
    }) => treasuryService.createTransfer(payload, idempotencyKey),
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
          mutation.mutate({
            payload: {
              companyId,
              sourceTreasuryAccountId: sourceId,
              destinationTreasuryAccountId: destinationId,
              amount: String(amount ?? 0),
              currencyCode: source?.currencyCode ?? 'HNL',
              transferDate: new Date().toISOString().slice(0, 10),
            },
            idempotencyKey: crypto.randomUUID(),
          })
        }}
      >
        <Select
          name="sourceId"
          label="Origen"
          value={sourceId}
          onChange={(e) => setSourceId(e.target.value)}
        >
          {treasuryAccounts.map((account) => (
            <option key={account.id} value={account.id}>
              {account.name}
            </option>
          ))}
        </Select>
        <Select
          name="destinationId"
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
