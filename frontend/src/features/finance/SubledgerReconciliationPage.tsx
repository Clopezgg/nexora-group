import { useQuery } from '@tanstack/react-query'
import {
  Badge,
  Card,
  CompanySelector,
  EmptyState,
  ErrorState,
  LoadingState,
  Table,
  type TableColumn,
} from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import {
  reconciliationService,
  type ReconciliationLine,
} from '../../services/reconciliationService'
import { formatMoney } from '../../utils/currency'

const SUBLEDGER_LABEL: Record<ReconciliationLine['subledger'], string> = {
  TREASURY: 'Tesorería',
  ACCOUNTS_PAYABLE: 'Cuentas por pagar',
  ACCOUNTS_RECEIVABLE: 'Cuentas por cobrar',
  CONTRACT_PAYMENTS: 'Pagos contractuales',
}

export function SubledgerReconciliationPage() {
  const { companies, activeCompanyId, activeCompany, setActiveCompanyId, isLoading, isError, refetch } =
    useActiveCompany()
  const currency = activeCompany?.functionalCurrencyCode ?? undefined

  const query = useQuery({
    queryKey: ['reconciliation', 'subledger-gl', activeCompanyId],
    queryFn: () => reconciliationService.subledgerGl(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  if (isLoading) return <LoadingState label="Cargando compañías…" />
  if (isError) return <ErrorState description="No se pudieron cargar las compañías." onRetry={() => refetch()} />
  if (companies.length === 0) {
    return (
      <EmptyState
        icon="shuffle"
        title="Configura una compañía primero"
        description="La conciliación Subledger ↔ GL necesita una compañía."
      />
    )
  }

  const columns: TableColumn<ReconciliationLine>[] = [
    { key: 'subledger', header: 'Subledger', render: (row) => SUBLEDGER_LABEL[row.subledger] },
    { key: 'subledgerTotal', header: 'Saldo subledger', render: (row) => formatMoney(row.subledgerTotal, currency) },
    { key: 'glTotal', header: 'Saldo GL (cuenta de control)', render: (row) => formatMoney(row.glTotal, currency) },
    { key: 'difference', header: 'Diferencia', render: (row) => formatMoney(row.difference, currency) },
    {
      key: 'reconciled',
      header: 'Estado',
      render: (row) => (
        <Badge tone={row.reconciled ? 'success' : 'danger'}>
          {row.reconciled ? 'Cuadra' : 'DESCUADRE'}
        </Badge>
      ),
    },
  ]

  return (
    <div>
      <header className="nx-page__header">
        <div>
          <p className="nx-page__eyebrow">Finanzas</p>
          <h1 className="nx-dashboard__title">Conciliación Subledger ↔ GL</h1>
          <p className="nx-field__hint">
            El General Ledger es la verdad contable. Un trial balance que cuadra no es suficiente: cada
            subledger debe cuadrar contra el saldo de su cuenta de control.
          </p>
        </div>
        <CompanySelector
          options={companies.map((company) => ({ id: company.id, label: company.name }))}
          value={activeCompanyId}
          onChange={setActiveCompanyId}
        />
      </header>

      <Card>
        {query.isLoading ? (
          <LoadingState label="Conciliando subledgers contra el GL…" />
        ) : query.isError ? (
          <ErrorState description="No se pudo calcular la conciliación." onRetry={() => query.refetch()} />
        ) : query.data ? (
          <>
            <Badge tone={query.data.allReconciled ? 'success' : 'danger'}>
              {query.data.allReconciled
                ? 'Todos los subledgers cuadran contra el GL'
                : 'Hay descuadres — resolver antes del cierre'}
            </Badge>
            <Table
              columns={columns}
              rows={query.data.lines}
              getRowKey={(row) => row.subledger}
              emptyMessage="Sin subledgers para conciliar."
            />
          </>
        ) : null}
      </Card>
    </div>
  )
}
