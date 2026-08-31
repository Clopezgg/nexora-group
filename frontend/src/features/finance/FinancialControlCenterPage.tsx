import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  Card,
  CompanySelector,
  EmptyState,
  ErrorState,
  LoadingState,
} from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { financialControlService, type FinancialKpi } from '../../services/financialControlService'
import './FinancialControlCenterPage.css'

const SEVERITY_LABEL: Record<FinancialKpi['severity'], string> = {
  ok: 'En orden',
  info: 'Informativo',
  warning: 'Requiere atención',
  critical: 'Crítico',
}

function KpiCard({ kpi }: { kpi: FinancialKpi }) {
  const body = (
    <div className={`nx-fcc-kpi nx-fcc-kpi--${kpi.severity}`}>
      <p className="nx-fcc-kpi__label">{kpi.label}</p>
      <p className="nx-fcc-kpi__value">{kpi.value}</p>
      <p className="nx-fcc-kpi__severity">{SEVERITY_LABEL[kpi.severity]}</p>
      <p className="nx-fcc-kpi__hint">{kpi.hint}</p>
      {kpi.route ? <span className="nx-fcc-kpi__drill">Ver detalle →</span> : null}
    </div>
  )
  return kpi.route ? (
    <Link to={kpi.route} className="nx-fcc-kpi__link">
      {body}
    </Link>
  ) : (
    body
  )
}

export function FinancialControlCenterPage() {
  const { companies, activeCompanyId, setActiveCompanyId, isLoading, isError, refetch } =
    useActiveCompany()

  const statusQuery = useQuery({
    queryKey: ['financial-control', 'daily-status', activeCompanyId],
    queryFn: () => financialControlService.dailyStatus(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  if (isLoading) return <LoadingState label="Cargando compañías…" />
  if (isError) return <ErrorState description="No se pudieron cargar las compañías." onRetry={() => refetch()} />
  if (companies.length === 0) {
    return (
      <EmptyState
        icon="chart"
        title="Configura una compañía primero"
        description="El Centro de Control Financiero necesita al menos una compañía."
      />
    )
  }

  const status = statusQuery.data

  return (
    <div>
      <header className="nx-page__header">
        <div>
          <p className="nx-page__eyebrow">Finanzas</p>
          <h1 className="nx-dashboard__title">Centro de Control Financiero</h1>
          {status ? (
            <p className="nx-field__hint">
              Estado financiero del día · {status.asOf}
              {status.fiscalPeriodLabel
                ? ` · Período ${status.fiscalPeriodLabel} (${status.fiscalPeriodStatus})`
                : ' · Período fiscal no configurado'}
            </p>
          ) : null}
        </div>
        <CompanySelector
          options={companies.map((company) => ({ id: company.id, label: company.name }))}
          value={activeCompanyId}
          onChange={setActiveCompanyId}
        />
      </header>

      <Card>
        {statusQuery.isLoading ? (
          <LoadingState label="Calculando estado financiero del día…" />
        ) : statusQuery.isError ? (
          <ErrorState
            description="No se pudo calcular el estado financiero del día."
            onRetry={() => statusQuery.refetch()}
          />
        ) : status ? (
          <div className="nx-fcc-grid">
            {status.kpis.map((kpi) => (
              <KpiCard key={kpi.key} kpi={kpi} />
            ))}
          </div>
        ) : null}
      </Card>
    </div>
  )
}
