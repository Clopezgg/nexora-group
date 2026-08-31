import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Badge,
  Card,
  CompanySelector,
  EmptyState,
  ErrorState,
  LoadingState,
  Select,
} from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { projectService } from '../../services/projectService'
import { projectCockpitService } from '../../services/projectCockpitService'
import { formatMoney } from '../../utils/currency'
import '../finance/FinancialControlCenterPage.css'

function Metric({
  label,
  value,
  hint,
  tone,
}: {
  label: string
  value: string
  hint?: string
  tone?: 'ok' | 'warning' | 'critical' | 'info'
}) {
  return (
    <div className={`nx-fcc-kpi nx-fcc-kpi--${tone ?? 'info'}`}>
      <p className="nx-fcc-kpi__label">{label}</p>
      <p className="nx-fcc-kpi__value">{value}</p>
      {hint ? <p className="nx-fcc-kpi__hint">{hint}</p> : null}
    </div>
  )
}

export function ProjectCockpitPage() {
  const { companies, activeCompanyId, setActiveCompanyId, isLoading, isError, refetch } =
    useActiveCompany()
  const [projectId, setProjectId] = useState('')

  const projectsQuery = useQuery({
    queryKey: ['projects', 'list', activeCompanyId],
    queryFn: () => projectService.list(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  const cockpitQuery = useQuery({
    queryKey: ['project-cockpit', projectId],
    queryFn: () => projectCockpitService.get(projectId),
    enabled: Boolean(projectId),
  })

  if (isLoading) return <LoadingState label="Cargando compañías…" />
  if (isError) return <ErrorState description="No se pudieron cargar las compañías." onRetry={() => refetch()} />
  if (companies.length === 0) {
    return <EmptyState icon="project" title="Configura una compañía primero" description="El Project Cockpit necesita una compañía con proyectos." />
  }

  const c = cockpitQuery.data
  const currency = c?.currencyCode
  const money = (v: number | null | undefined) => (v == null ? '—' : formatMoney(v, currency))
  const cpiTone = c?.costPerformanceIndex == null ? 'info' : c.costPerformanceIndex >= 1 ? 'ok' : 'critical'
  const vacTone =
    c?.varianceAtCompletion == null ? 'info' : c.varianceAtCompletion >= 0 ? 'ok' : 'critical'
  const marginTone =
    c?.projectedMargin == null ? 'info' : c.projectedMargin >= 0 ? 'ok' : 'critical'

  return (
    <div>
      <header className="nx-page__header">
        <div>
          <p className="nx-page__eyebrow">Proyectos</p>
          <h1 className="nx-dashboard__title">Project Financial Cockpit</h1>
          <p className="nx-field__hint">
            EAC / ETC / CPI / margen. El costo real se lee del General Ledger (todo el gasto imputado
            al proyecto), no solo del subledger de AP.
          </p>
        </div>
        <CompanySelector
          options={companies.map((company) => ({ id: company.id, label: company.name }))}
          value={activeCompanyId}
          onChange={(value) => {
            setActiveCompanyId(value)
            setProjectId('')
          }}
        />
      </header>

      <Card title="Proyecto">
        {projectsQuery.isLoading ? (
          <LoadingState label="Cargando proyectos…" />
        ) : (
          <Select label="Proyecto" value={projectId} onChange={(event) => setProjectId(event.target.value)}>
            <option value="">Selecciona un proyecto…</option>
            {(projectsQuery.data ?? []).map((project) => (
              <option key={project.id} value={project.id}>
                {project.code ? `${project.code} · ` : ''}{project.name}
              </option>
            ))}
          </Select>
        )}
      </Card>

      {projectId ? (
        <Card title="Salud financiera del proyecto">
          {cockpitQuery.isLoading ? (
            <LoadingState label="Calculando EAC/ETC…" />
          ) : cockpitQuery.isError ? (
            <ErrorState description="No se pudo calcular el cockpit." onRetry={() => cockpitQuery.refetch()} />
          ) : c ? (
            <>
              <div className="nx-treasury__actions">
                <Badge tone={cpiTone === 'ok' ? 'success' : cpiTone === 'critical' ? 'danger' : 'neutral'}>
                  CPI {c.costPerformanceIndex == null ? '—' : c.costPerformanceIndex.toFixed(2)}
                </Badge>
                <Badge tone={vacTone === 'ok' ? 'success' : vacTone === 'critical' ? 'danger' : 'neutral'}>
                  {c.varianceAtCompletion == null
                    ? 'VAC —'
                    : c.varianceAtCompletion >= 0
                      ? 'Dentro de presupuesto'
                      : 'Sobrecosto proyectado'}
                </Badge>
                {c.percentComplete == null ? (
                  <Badge tone="warning">Sin avance registrado</Badge>
                ) : null}
              </div>
              <div className="nx-fcc-grid" style={{ marginTop: '0.75rem' }}>
                <Metric label="Presupuesto (BAC)" value={money(c.budgetAtCompletion)} />
                <Metric label="Comprometido (OC abiertas)" value={money(c.committed)} />
                <Metric label="Costo real (AC · desde el GL)" value={money(c.actualCost)} />
                <Metric
                  label="Avance físico"
                  value={c.percentComplete == null ? '—' : `${c.percentComplete.toFixed(2)}%`}
                />
                <Metric label="Valor ganado (EV)" value={money(c.earnedValue)} />
                <Metric label="Estimado para completar (ETC)" value={money(c.estimateToComplete)} />
                <Metric
                  label="Estimado al completar (EAC)"
                  value={money(c.estimateAtCompletion)}
                  tone={vacTone}
                />
                <Metric
                  label="Variación al completar (VAC = BAC − EAC)"
                  value={money(c.varianceAtCompletion)}
                  tone={vacTone}
                />
                <Metric label="Ingreso por contrato" value={money(c.contractRevenue)} />
                <Metric
                  label="Margen proyectado"
                  value={
                    c.projectedMargin == null
                      ? '—'
                      : `${money(c.projectedMargin)}${c.projectedMarginPct != null ? ` (${c.projectedMarginPct.toFixed(2)}%)` : ''}`
                  }
                  tone={marginTone}
                />
              </div>
            </>
          ) : null}
        </Card>
      ) : null}
    </div>
  )
}
