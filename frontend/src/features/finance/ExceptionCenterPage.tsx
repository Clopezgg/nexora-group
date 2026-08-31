import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
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
import { exceptionService, type FinancialException } from '../../services/exceptionService'

const SEVERITY_TONE: Record<FinancialException['severity'], 'info' | 'warning' | 'danger'> = {
  info: 'info',
  warning: 'warning',
  critical: 'danger',
}

export function ExceptionCenterPage() {
  const { companies, activeCompanyId, setActiveCompanyId, isLoading, isError, refetch } =
    useActiveCompany()

  const query = useQuery({
    queryKey: ['exception-center', activeCompanyId],
    queryFn: () => exceptionService.list(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  if (isLoading) return <LoadingState label="Cargando compañías…" />
  if (isError) return <ErrorState description="No se pudieron cargar las compañías." onRetry={() => refetch()} />
  if (companies.length === 0) {
    return (
      <EmptyState
        icon="warning"
        title="Configura una compañía primero"
        description="El Exception Center necesita una compañía."
      />
    )
  }

  const data = query.data
  const columns: TableColumn<FinancialException>[] = [
    {
      key: 'severity',
      header: 'Severidad',
      render: (row) => (
        <Badge tone={SEVERITY_TONE[row.severity]}>
          {row.severity === 'critical' ? 'Crítica' : row.severity === 'warning' ? 'Advertencia' : 'Informativa'}
        </Badge>
      ),
    },
    { key: 'title', header: 'Excepción', render: (row) => row.title },
    { key: 'count', header: 'Casos', render: (row) => row.count },
    { key: 'detail', header: 'Detalle', render: (row) => row.detail },
    { key: 'suggestedAction', header: 'Acción sugerida', render: (row) => row.suggestedAction },
    {
      key: 'route',
      header: '',
      render: (row) =>
        row.route ? (
          <Link to={row.route}>Resolver →</Link>
        ) : null,
    },
  ]

  return (
    <div>
      <header className="nx-page__header">
        <div>
          <p className="nx-page__eyebrow">Finanzas</p>
          <h1 className="nx-dashboard__title">Exception Center</h1>
          <p className="nx-field__hint">
            Meta: <strong>Exception Zero</strong>. Todo lo que aparece aquí debe resolverse — no ignorarse.
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
          <LoadingState label="Buscando excepciones…" />
        ) : query.isError ? (
          <ErrorState description="No se pudieron cargar las excepciones." onRetry={() => query.refetch()} />
        ) : data ? (
          data.exceptionZero ? (
            <EmptyState
              icon="check"
              title="Exception Zero"
              description="No hay excepciones financieras ni de datos abiertas para esta compañía."
            />
          ) : (
            <>
              <Badge tone={data.criticalCount > 0 ? 'danger' : 'warning'}>
                {data.total} excepción(es){data.criticalCount > 0 ? ` · ${data.criticalCount} crítica(s)` : ''}
              </Badge>
              <Table
                columns={columns}
                rows={data.exceptions}
                getRowKey={(row) => row.code}
                emptyMessage="Sin excepciones."
              />
            </>
          )
        ) : null}
      </Card>
    </div>
  )
}
