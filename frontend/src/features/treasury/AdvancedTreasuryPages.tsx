import { useMemo, useState } from 'react'
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
  Table,
  type TableColumn,
} from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { useMutationError } from '../../hooks/useMutationError'
import { masterDataService } from '../../services/masterDataService'
import { projectService } from '../../services/projectService'
import {
  treasuryService,
  type BankStatement,
  type BankStatementLine,
  type CashClosing,
  type FundRestriction,
  type ReconciliationCandidate,
} from '../../services/treasuryService'
import { formatMoney } from '../../utils/currency'
import { statusLabel } from '../../utils/statusLabels'
import './TreasuryPage.css'

function CompanyHeader({ title, description }: { title: string; description: string }) {
  const { companies, activeCompanyId, setActiveCompanyId } = useActiveCompany()
  return (
    <header className="nx-treasury__header">
      <div>
        <p className="nx-page__eyebrow">Tesorería</p>
        <h1 className="nx-dashboard__title">{title}</h1>
        <p className="nx-field__hint">{description}</p>
      </div>
      <Select value={activeCompanyId ?? ''} onChange={(event) => setActiveCompanyId(event.target.value)} aria-label="Compañía">
        {companies.map((company) => <option key={company.id} value={company.id}>{company.name}</option>)}
      </Select>
    </header>
  )
}

function CompanyGuard({ children }: { children: React.ReactNode }) {
  const { companies, isLoading, isError, refetch } = useActiveCompany()
  if (isLoading) return <LoadingState label="Cargando Tesorería…" />
  if (isError) return <ErrorState description="No se pudieron cargar las compañías." onRetry={() => refetch()} />
  if (companies.length === 0) return <EmptyState icon="bank" title="No hay compañía configurada" description="Configura una compañía antes de operar Tesorería." />
  return <>{children}</>
}

export function BankReconciliationPage() {
  const queryClient = useQueryClient()
  const handleMutationError = useMutationError()
  const { activeCompanyId } = useActiveCompany()
  const [selectedStatementId, setSelectedStatementId] = useState('')
  const [createStatementOpen, setCreateStatementOpen] = useState(false)
  const [addLineOpen, setAddLineOpen] = useState(false)
  const [matchLine, setMatchLine] = useState<BankStatementLine | null>(null)

  const accountsQuery = useQuery({
    queryKey: ['treasury', 'accounts', activeCompanyId],
    queryFn: () => treasuryService.listAccounts(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })
  const statementsQuery = useQuery({
    queryKey: ['treasury', 'bank-statements', activeCompanyId],
    queryFn: () => treasuryService.listBankStatements(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })
  const statements = statementsQuery.data ?? []
  const effectiveStatementId = selectedStatementId || statements[0]?.id || ''
  const linesQuery = useQuery({
    queryKey: ['treasury', 'bank-statement-lines', effectiveStatementId],
    queryFn: () => treasuryService.listBankStatementLines(effectiveStatementId),
    enabled: Boolean(effectiveStatementId),
  })

  const unmatch = useMutation({
    mutationFn: (lineId: string) => treasuryService.unmatchReconciliationLine(lineId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['treasury', 'bank-statement-lines', effectiveStatementId] }),
    onError: (error) => handleMutationError(error, 'Deshacer conciliación'),
  })
  const exclude = useMutation({
    mutationFn: (lineId: string) => treasuryService.excludeReconciliationLine(lineId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['treasury', 'bank-statement-lines', effectiveStatementId] }),
    onError: (error) => handleMutationError(error, 'Excluir línea bancaria'),
  })

  const accountNames = new Map((accountsQuery.data ?? []).map((account) => [account.id, account.name]))
  const statementColumns: TableColumn<BankStatement>[] = [
    { key: 'date', header: 'Fecha', render: (row) => row.statementDate },
    { key: 'account', header: 'Cuenta', render: (row) => accountNames.get(row.treasuryAccountId) ?? 'Cuenta bancaria' },
    { key: 'opening', header: 'Inicial', render: (row) => formatMoney(row.openingBalance, 'HNL') },
    { key: 'closing', header: 'Final', render: (row) => formatMoney(row.closingBalance, 'HNL') },
    { key: 'ref', header: 'Referencia', render: (row) => row.reference ?? '—' },
    { key: 'actions', header: 'Acciones', render: (row) => <Button variant="secondary" onClick={() => setSelectedStatementId(row.id)}>Abrir</Button> },
  ]
  const lineColumns: TableColumn<BankStatementLine>[] = [
    { key: 'date', header: 'Fecha', render: (row) => row.lineDate },
    { key: 'description', header: 'Descripción', render: (row) => row.description },
    { key: 'amount', header: 'Monto', render: (row) => formatMoney(row.amount, 'HNL') },
    { key: 'status', header: 'Estado', render: (row) => <Badge>{statusLabel(row.status)}</Badge> },
    {
      key: 'actions',
      header: 'Acciones',
      render: (row) => (
        <div className="nx-treasury__actions">
          {['UNMATCHED', 'PARTIAL'].includes(row.status) ? <Button onClick={() => setMatchLine(row)}>Conciliar</Button> : null}
          {['MATCHED', 'PARTIAL'].includes(row.status) ? <Button variant="secondary" onClick={() => unmatch.mutate(row.id)}>Deshacer match</Button> : null}
          {row.status === 'UNMATCHED' ? <Button variant="ghost" onClick={() => exclude.mutate(row.id)}>Excluir</Button> : null}
        </div>
      ),
    },
  ]

  return (
    <CompanyGuard>
      <div className="nx-treasury">
        <CompanyHeader title="Conciliación bancaria" description="Carga estados, revisa líneas y concilia contra movimientos contables reales de la misma cuenta de Tesorería." />
        <Card title="Estados bancarios">
          <Button onClick={() => setCreateStatementOpen(true)}>Cargar estado</Button>
          {statementsQuery.isLoading ? <LoadingState label="Cargando estados…" /> : statementsQuery.isError ? <ErrorState description="No se pudieron cargar los estados bancarios." onRetry={() => statementsQuery.refetch()} /> : <Table columns={statementColumns} rows={statements} getRowKey={(row) => row.id} emptyMessage="Todavía no hay estados bancarios cargados." />}
        </Card>
        {effectiveStatementId ? (
          <Card title="Líneas del estado seleccionado">
            <Button variant="secondary" onClick={() => setAddLineOpen(true)}>Agregar línea</Button>
            {linesQuery.isLoading ? <LoadingState label="Cargando líneas…" /> : linesQuery.isError ? <ErrorState description="No se pudieron cargar las líneas." onRetry={() => linesQuery.refetch()} /> : <Table columns={lineColumns} rows={linesQuery.data ?? []} getRowKey={(row) => row.id} emptyMessage="El estado no tiene líneas." />}
          </Card>
        ) : null}
        {createStatementOpen && activeCompanyId ? <CreateStatementModal accounts={accountsQuery.data ?? []} onClose={() => setCreateStatementOpen(false)} onCreated={() => queryClient.invalidateQueries({ queryKey: ['treasury', 'bank-statements', activeCompanyId] })} /> : null}
        {addLineOpen && effectiveStatementId ? <AddStatementLineModal statementId={effectiveStatementId} onClose={() => setAddLineOpen(false)} onCreated={() => queryClient.invalidateQueries({ queryKey: ['treasury', 'bank-statement-lines', effectiveStatementId] })} /> : null}
        {matchLine ? <MatchLineModal line={matchLine} onClose={() => setMatchLine(null)} onMatched={() => queryClient.invalidateQueries({ queryKey: ['treasury', 'bank-statement-lines', effectiveStatementId] })} /> : null}
      </div>
    </CompanyGuard>
  )
}

function CreateStatementModal({ accounts, onClose, onCreated }: { accounts: Awaited<ReturnType<typeof treasuryService.listAccounts>>; onClose: () => void; onCreated: () => void }) {
  const handleMutationError = useMutationError()
  const bankAccounts = accounts.filter((account) => account.kind === 'BANK' && account.status === 'ACTIVE')
  const [treasuryAccountId, setTreasuryAccountId] = useState(bankAccounts[0]?.id ?? '')
  const [statementDate, setStatementDate] = useState(new Date().toISOString().slice(0, 10))
  const [openingBalance, setOpeningBalance] = useState<number | null>(0)
  const [closingBalance, setClosingBalance] = useState<number | null>(0)
  const [reference, setReference] = useState('')
  const create = useMutation({
    mutationFn: () => treasuryService.createBankStatement({ treasuryAccountId, statementDate, openingBalance: String(openingBalance ?? 0), closingBalance: String(closingBalance ?? 0), reference: reference.trim() || undefined }),
    onSuccess: () => { onCreated(); onClose() },
    onError: (error) => handleMutationError(error, 'Cargar estado bancario'),
  })
  return <Modal open title="Cargar estado bancario" onClose={onClose}><form className="nx-treasury__form" onSubmit={(event) => { event.preventDefault(); create.mutate() }}>
    <Select label="Cuenta bancaria" value={treasuryAccountId} onChange={(event) => setTreasuryAccountId(event.target.value)}>{bankAccounts.map((account) => <option key={account.id} value={account.id}>{account.name}</option>)}</Select>
    <Input label="Fecha del estado" type="date" value={statementDate} onChange={(event) => setStatementDate(event.target.value)} required />
    <MoneyInput label="Saldo inicial" value={openingBalance} onChange={setOpeningBalance} />
    <MoneyInput label="Saldo final" value={closingBalance} onChange={setClosingBalance} />
    <Input label="Referencia" value={reference} onChange={(event) => setReference(event.target.value)} />
    {bankAccounts.length === 0 ? <p className="nx-field__error">No hay cuentas BANK activas.</p> : null}
    <Button type="submit" loading={create.isPending} disabled={!treasuryAccountId || !statementDate}>Guardar estado</Button>
  </form></Modal>
}

function AddStatementLineModal({ statementId, onClose, onCreated }: { statementId: string; onClose: () => void; onCreated: () => void }) {
  const handleMutationError = useMutationError()
  const [lineDate, setLineDate] = useState(new Date().toISOString().slice(0, 10))
  const [description, setDescription] = useState('')
  const [amount, setAmount] = useState<number | null>(null)
  const create = useMutation({
    mutationFn: () => treasuryService.addBankStatementLine(statementId, { lineDate, description: description.trim(), amount: String(amount ?? 0) }),
    onSuccess: () => { onCreated(); onClose() },
    onError: (error) => handleMutationError(error, 'Agregar línea bancaria'),
  })
  return <Modal open title="Agregar línea bancaria" onClose={onClose}><form className="nx-treasury__form" onSubmit={(event) => { event.preventDefault(); create.mutate() }}>
    <Input label="Fecha" type="date" value={lineDate} onChange={(event) => setLineDate(event.target.value)} required />
    <Input label="Descripción" value={description} onChange={(event) => setDescription(event.target.value)} required />
    <MoneyInput label="Monto (+ ingreso / - salida)" value={amount} onChange={setAmount} />
    <Button type="submit" loading={create.isPending} disabled={!lineDate || !description.trim() || !amount}>Agregar línea</Button>
  </form></Modal>
}

function MatchLineModal({ line, onClose, onMatched }: { line: BankStatementLine; onClose: () => void; onMatched: () => void }) {
  const handleMutationError = useMutationError()
  const candidatesQuery = useQuery({ queryKey: ['treasury', 'reconciliation-candidates', line.id], queryFn: () => treasuryService.listReconciliationCandidates(line.id) })
  const [candidate, setCandidate] = useState<ReconciliationCandidate | null>(null)
  const [amount, setAmount] = useState<number | null>(Math.abs(line.amount))
  const match = useMutation({
    mutationFn: () => treasuryService.matchReconciliationLine(line.id, (candidate as ReconciliationCandidate).accountingDocumentId, amount ?? 0),
    onSuccess: () => { onMatched(); onClose() },
    onError: (error) => handleMutationError(error, 'Conciliar línea bancaria'),
  })
  const columns: TableColumn<ReconciliationCandidate>[] = [
    { key: 'document', header: 'Documento', render: (row) => `${row.documentTypeCode} · ${row.documentNumber}` },
    { key: 'description', header: 'Descripción', render: (row) => row.description ?? '—' },
    { key: 'available', header: 'Disponible', render: (row) => formatMoney(row.availableAmount, 'HNL') },
    { key: 'exact', header: 'Matching', render: (row) => row.exactMatch ? <Badge tone="success">Exacto</Badge> : <Badge>Parcial</Badge> },
    { key: 'action', header: 'Acción', render: (row) => <Button variant={candidate?.accountingDocumentId === row.accountingDocumentId ? 'primary' : 'secondary'} onClick={() => { setCandidate(row); setAmount(Math.min(Math.abs(line.amount), row.availableAmount)) }}>Seleccionar</Button> },
  ]
  return <Modal open title="Conciliar línea" onClose={onClose}>
    <p className="nx-field__hint">Línea: {line.description} · {formatMoney(line.amount, 'HNL')}</p>
    {candidatesQuery.isLoading ? <LoadingState label="Buscando movimientos compatibles…" /> : candidatesQuery.isError ? <ErrorState description="No se pudieron cargar candidatos." onRetry={() => candidatesQuery.refetch()} /> : <Table columns={columns} rows={candidatesQuery.data ?? []} getRowKey={(row) => row.accountingDocumentId} emptyMessage="No hay movimientos contables compatibles disponibles." />}
    {candidate ? <div className="nx-treasury__form"><MoneyInput label="Monto a conciliar" value={amount} onChange={setAmount} /><Button loading={match.isPending} disabled={!amount || amount <= 0 || amount > Math.abs(line.amount) || amount > candidate.availableAmount} onClick={() => match.mutate()}>Confirmar match</Button></div> : null}
  </Modal>
}

export function CashClosingsPage() {
  const queryClient = useQueryClient()
  const handleMutationError = useMutationError()
  const { activeCompanyId } = useActiveCompany()
  const [createOpen, setCreateOpen] = useState(false)
  const [approveClosing, setApproveClosing] = useState<CashClosing | null>(null)

  const accountsQuery = useQuery({ queryKey: ['treasury', 'accounts', activeCompanyId], queryFn: () => treasuryService.listAccounts(activeCompanyId as string), enabled: Boolean(activeCompanyId) })
  const closingsQuery = useQuery({ queryKey: ['treasury', 'cash-closings', activeCompanyId], queryFn: () => treasuryService.listCashClosings(activeCompanyId as string), enabled: Boolean(activeCompanyId) })
  const glAccountsQuery = useQuery({ queryKey: ['master-data', 'accounts', activeCompanyId], queryFn: () => masterDataService.listAccounts(activeCompanyId as string), enabled: Boolean(activeCompanyId) })
  const accountNames = new Map((accountsQuery.data ?? []).map((account) => [account.id, account.name]))
  const columns: TableColumn<CashClosing>[] = [
    { key: 'date', header: 'Fecha', render: (row) => row.closingDate },
    { key: 'account', header: 'Cuenta', render: (row) => accountNames.get(row.treasuryAccountId) ?? 'Caja' },
    { key: 'expected', header: 'Saldo sistema', render: (row) => formatMoney(row.expectedAmount, 'HNL') },
    { key: 'counted', header: 'Saldo contado', render: (row) => formatMoney(row.countedAmount, 'HNL') },
    { key: 'difference', header: 'Diferencia', render: (row) => formatMoney(row.differenceAmount, 'HNL') },
    { key: 'status', header: 'Estado', render: (row) => <Badge>{statusLabel(row.status)}</Badge> },
    { key: 'actions', header: 'Acciones', render: (row) => row.status === 'DRAFT' ? <Button onClick={() => setApproveClosing(row)}>Aprobar</Button> : <span className="nx-field__hint">Aprobado</span> },
  ]

  return <CompanyGuard><div className="nx-treasury">
    <CompanyHeader title="Cierres de caja" description="Compara saldo del sistema contra conteo físico y somete diferencias a aprobación con SoD." />
    <Card title="Operación"><Button onClick={() => setCreateOpen(true)}>Nuevo cierre</Button></Card>
    {closingsQuery.isLoading ? <LoadingState label="Cargando cierres…" /> : closingsQuery.isError ? <ErrorState description="No se pudieron cargar los cierres." onRetry={() => closingsQuery.refetch()} /> : <Table columns={columns} rows={closingsQuery.data ?? []} getRowKey={(row) => row.id} emptyMessage="Todavía no hay cierres de caja." />}
    {createOpen ? <CreateCashClosingModal accounts={(accountsQuery.data ?? []).filter((account) => account.status === 'ACTIVE')} onClose={() => setCreateOpen(false)} onCreated={() => queryClient.invalidateQueries({ queryKey: ['treasury', 'cash-closings', activeCompanyId] })} /> : null}
    {approveClosing ? <ApproveCashClosingModal closing={approveClosing} differenceAccounts={(glAccountsQuery.data ?? []).filter((account) => account.isPostable)} onClose={() => setApproveClosing(null)} onApproved={() => queryClient.invalidateQueries({ queryKey: ['treasury', 'cash-closings', activeCompanyId] })} onError={handleMutationError} /> : null}
  </div></CompanyGuard>
}

function CreateCashClosingModal({ accounts, onClose, onCreated }: { accounts: Awaited<ReturnType<typeof treasuryService.listAccounts>>; onClose: () => void; onCreated: () => void }) {
  const handleMutationError = useMutationError()
  const cashAccounts = accounts.filter((account) => account.kind === 'CASH')
  const [treasuryAccountId, setTreasuryAccountId] = useState(cashAccounts[0]?.id ?? '')
  const selected = cashAccounts.find((account) => account.id === treasuryAccountId)
  const [closingDate, setClosingDate] = useState(new Date().toISOString().slice(0, 10))
  const [openingAmount, setOpeningAmount] = useState<number | null>(0)
  const [countedAmount, setCountedAmount] = useState<number | null>(null)
  const create = useMutation({
    mutationFn: () => treasuryService.createCashClosing({ treasuryAccountId, closingDate, openingAmount: String(openingAmount ?? 0), expectedAmount: String(selected?.balance ?? 0), countedAmount: String(countedAmount ?? 0) }),
    onSuccess: () => { onCreated(); onClose() },
    onError: (error) => handleMutationError(error, 'Crear cierre de caja'),
  })
  return <Modal open title="Nuevo cierre de caja" onClose={onClose}><form className="nx-treasury__form" onSubmit={(event) => { event.preventDefault(); create.mutate() }}>
    <Select label="Cuenta de caja" value={treasuryAccountId} onChange={(event) => setTreasuryAccountId(event.target.value)}>{cashAccounts.map((account) => <option key={account.id} value={account.id}>{account.name}</option>)}</Select>
    <Input label="Fecha" type="date" value={closingDate} onChange={(event) => setClosingDate(event.target.value)} />
    <MoneyInput label="Saldo de apertura" value={openingAmount} onChange={setOpeningAmount} />
    <p className="nx-field__hint">Saldo sistema actual: {formatMoney(selected?.balance ?? 0, selected?.currencyCode ?? 'HNL')}</p>
    <MoneyInput label="Saldo contado" value={countedAmount} onChange={setCountedAmount} />
    {cashAccounts.length === 0 ? <p className="nx-field__error">No hay cuentas CASH activas.</p> : null}
    <Button type="submit" loading={create.isPending} disabled={!treasuryAccountId || !closingDate || countedAmount === null || countedAmount < 0 || (openingAmount ?? 0) < 0}>Registrar cierre</Button>
  </form></Modal>
}

function ApproveCashClosingModal({ closing, differenceAccounts, onClose, onApproved, onError }: { closing: CashClosing; differenceAccounts: { id: string; name: string }[]; onClose: () => void; onApproved: () => void; onError: ReturnType<typeof useMutationError> }) {
  const [differenceAccountId, setDifferenceAccountId] = useState('')
  const approve = useMutation({
    mutationFn: () => treasuryService.approveCashClosing(closing.id, differenceAccountId || undefined),
    onSuccess: () => { onApproved(); onClose() },
    onError: (error) => onError(error, 'Aprobar cierre de caja'),
  })
  const requiresAccount = closing.differenceAmount !== 0
  return <Modal open title="Aprobar cierre de caja" onClose={onClose}><div className="nx-treasury__form">
    <p>Diferencia: <strong>{formatMoney(closing.differenceAmount, 'HNL')}</strong></p>
    {requiresAccount ? <Select label="Cuenta contable para diferencia" value={differenceAccountId} onChange={(event) => setDifferenceAccountId(event.target.value)}><option value="">Selecciona cuenta postable…</option>{differenceAccounts.map((account) => <option key={account.id} value={account.id}>{account.name}</option>)}</Select> : <p className="nx-field__hint">Sin diferencia: no se generará ajuste contable.</p>}
    <Button loading={approve.isPending} disabled={requiresAccount && !differenceAccountId} onClick={() => approve.mutate()}>Aprobar cierre</Button>
  </div></Modal>
}

export function FundRestrictionsPage() {
  const queryClient = useQueryClient()
  const handleMutationError = useMutationError()
  const { activeCompanyId } = useActiveCompany()
  const [createOpen, setCreateOpen] = useState(false)
  const [selectedAccountId, setSelectedAccountId] = useState('')

  const accountsQuery = useQuery({ queryKey: ['treasury', 'accounts', activeCompanyId], queryFn: () => treasuryService.listAccounts(activeCompanyId as string), enabled: Boolean(activeCompanyId) })
  const projectsQuery = useQuery({ queryKey: ['projects', activeCompanyId], queryFn: () => projectService.list(activeCompanyId as string), enabled: Boolean(activeCompanyId) })
  const restrictionsQuery = useQuery({ queryKey: ['treasury', 'fund-restrictions', activeCompanyId], queryFn: () => treasuryService.listFundRestrictions(activeCompanyId as string), enabled: Boolean(activeCompanyId) })
  const accounts = accountsQuery.data ?? []
  const effectiveAccountId = selectedAccountId || accounts[0]?.id || ''
  const availabilityQuery = useQuery({ queryKey: ['treasury', 'availability', effectiveAccountId], queryFn: () => treasuryService.getAvailability(effectiveAccountId), enabled: Boolean(effectiveAccountId) })
  const projects = Array.isArray(projectsQuery.data) ? projectsQuery.data : []
  const accountNames = new Map(accounts.map((account) => [account.id, account.name]))
  const projectNames = new Map(projects.map((project) => [project.id, `${project.code ? `${project.code} — ` : ''}${project.name}`]))
  const release = useMutation({
    mutationFn: (restrictionId: string) => treasuryService.releaseFundRestriction(restrictionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['treasury', 'fund-restrictions', activeCompanyId] })
      queryClient.invalidateQueries({ queryKey: ['treasury', 'availability'] })
    },
    onError: (error) => handleMutationError(error, 'Liberar restricción de fondos'),
  })
  const columns: TableColumn<FundRestriction>[] = [
    { key: 'account', header: 'Cuenta', render: (row) => accountNames.get(row.treasuryAccountId) ?? 'Tesorería' },
    { key: 'amount', header: 'Importe', render: (row) => formatMoney(row.amount, 'HNL') },
    { key: 'project', header: 'Reservado para', render: (row) => row.restrictedForProjectId ? projectNames.get(row.restrictedForProjectId) ?? 'Proyecto' : 'Uso restringido general' },
    { key: 'reason', header: 'Motivo', render: (row) => row.description },
    { key: 'status', header: 'Estado', render: (row) => <Badge tone={row.active ? 'warning' : 'neutral'}>{row.active ? 'Activa' : 'Liberada'}</Badge> },
    { key: 'actions', header: 'Acciones', render: (row) => row.active ? <Button variant="secondary" onClick={() => release.mutate(row.id)}>Liberar</Button> : <span className="nx-field__hint">Liberada</span> },
  ]
  const availability = availabilityQuery.data

  return <CompanyGuard><div className="nx-treasury">
    <CompanyHeader title="Restricciones de fondos" description="Reserva efectivo sin transferir su propiedad al proyecto y muestra el saldo realmente disponible para nuevas salidas." />
    <Card title="Disponibilidad">
      <Select label="Cuenta de Tesorería" value={effectiveAccountId} onChange={(event) => setSelectedAccountId(event.target.value)}>{accounts.map((account) => <option key={account.id} value={account.id}>{account.name}</option>)}</Select>
      {availabilityQuery.isLoading ? <LoadingState label="Calculando disponibilidad…" /> : availability ? <div className="nx-dashboard__kpi-grid"><Card title="Saldo contable"><strong>{formatMoney(availability.balance, 'HNL')}</strong></Card><Card title="Restringido"><strong>{formatMoney(availability.reservedAmount, 'HNL')}</strong></Card><Card title="Disponible"><strong>{formatMoney(availability.availableAmount, 'HNL')}</strong></Card></div> : null}
      <Button onClick={() => setCreateOpen(true)} disabled={accounts.length === 0}>Nueva restricción</Button>
    </Card>
    {restrictionsQuery.isLoading ? <LoadingState label="Cargando restricciones…" /> : restrictionsQuery.isError ? <ErrorState description="No se pudieron cargar las restricciones." onRetry={() => restrictionsQuery.refetch()} /> : <Table columns={columns} rows={restrictionsQuery.data ?? []} getRowKey={(row) => row.id} emptyMessage="No hay restricciones de fondos activas o históricas." />}
    {createOpen ? <CreateRestrictionModal accounts={accounts} projects={projects} onClose={() => setCreateOpen(false)} onCreated={() => { queryClient.invalidateQueries({ queryKey: ['treasury', 'fund-restrictions', activeCompanyId] }); queryClient.invalidateQueries({ queryKey: ['treasury', 'availability'] }) }} /> : null}
  </div></CompanyGuard>
}

function CreateRestrictionModal({ accounts, projects, onClose, onCreated }: { accounts: Awaited<ReturnType<typeof treasuryService.listAccounts>>; projects: Awaited<ReturnType<typeof projectService.list>>; onClose: () => void; onCreated: () => void }) {
  const handleMutationError = useMutationError()
  const [treasuryAccountId, setTreasuryAccountId] = useState(accounts[0]?.id ?? '')
  const [projectId, setProjectId] = useState('')
  const [amount, setAmount] = useState<number | null>(null)
  const [description, setDescription] = useState('')
  const create = useMutation({
    mutationFn: () => treasuryService.createFundRestriction({ treasuryAccountId, restrictedForProjectId: projectId || null, amount: String(amount ?? 0), description: description.trim() }),
    onSuccess: () => { onCreated(); onClose() },
    onError: (error) => handleMutationError(error, 'Crear restricción de fondos'),
  })
  return <Modal open title="Nueva restricción de fondos" onClose={onClose}><form className="nx-treasury__form" onSubmit={(event) => { event.preventDefault(); create.mutate() }}>
    <Select label="Cuenta" value={treasuryAccountId} onChange={(event) => setTreasuryAccountId(event.target.value)}>{accounts.map((account) => <option key={account.id} value={account.id}>{account.name} — {account.currencyCode}</option>)}</Select>
    <Select label="Proyecto beneficiario (opcional)" value={projectId} onChange={(event) => setProjectId(event.target.value)}><option value="">Restricción general</option>{projects.map((project) => <option key={project.id} value={project.id}>{project.code ? `${project.code} — ` : ''}{project.name}</option>)}</Select>
    <MoneyInput label="Importe" value={amount} onChange={setAmount} />
    <Input label="Motivo" value={description} onChange={(event) => setDescription(event.target.value)} required />
    <Button type="submit" loading={create.isPending} disabled={!treasuryAccountId || !amount || amount <= 0 || !description.trim()}>Crear restricción</Button>
  </form></Modal>
}
