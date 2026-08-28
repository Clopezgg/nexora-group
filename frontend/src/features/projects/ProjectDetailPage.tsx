import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  Input,
  LoadingState,
  Select,
  StatCard,
  Textarea,
} from '../../design-system'
import { crmService } from '../../services/crmService'
import { masterDataService } from '../../services/masterDataService'
import { projectService } from '../../services/projectService'
import type { Project, ProjectStatus } from '../../types/project'
import { formatMoney } from '../../utils/currency'
import { statusLabel } from '../../utils/statusLabels'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { useActiveContext } from '../context/useActiveContext'

const TRANSITIONS: Partial<Record<ProjectStatus, Array<{ status: ProjectStatus; label: string }>>> = {
  PLANNING: [{ status: 'ACTIVE', label: 'Activar proyecto' }, { status: 'CANCELLED', label: 'Cancelar proyecto' }],
  ACTIVE: [{ status: 'ON_HOLD', label: 'Pausar' }, { status: 'COMPLETED', label: 'Completar' }, { status: 'CANCELLED', label: 'Cancelar proyecto' }],
  ON_HOLD: [{ status: 'ACTIVE', label: 'Reanudar' }, { status: 'CANCELLED', label: 'Cancelar proyecto' }],
  COMPLETED: [{ status: 'CLOSED', label: 'Cerrar administrativamente' }],
}

function money(value: string | null, currency: string) {
  return value === null ? '—' : formatMoney(Number(value), currency)
}

function percent(value: string | null) {
  return value === null ? '—' : `${Number(value).toFixed(1)}%`
}

const EMPTY_FORM = {
  name: '',
  code: '',
  customerId: '',
  manager: '',
  currencyCode: 'HNL',
  costCenterId: '',
  plannedStart: '',
  plannedEnd: '',
  description: '',
}

export function ProjectDetailPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const queryClient = useQueryClient()
  const { activeCompanyId } = useActiveCompany()
  const { context, setActiveProject } = useActiveContext()
  const [form, setForm] = useState(EMPTY_FORM)

  const projectQuery = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectService.get(projectId as string),
    enabled: Boolean(projectId),
  })
  const financialQuery = useQuery({
    queryKey: ['project', projectId, 'financial-summary'],
    queryFn: () => projectService.getFinancialSummary(projectId as string),
    enabled: Boolean(projectId),
  })
  const customersQuery = useQuery({
    queryKey: ['crm', 'customers', activeCompanyId],
    queryFn: () => crmService.listCustomers(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })
  const usersQuery = useQuery({
    queryKey: ['master-data', 'users', activeCompanyId],
    queryFn: () => masterDataService.listUsers(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })
  const costCentersQuery = useQuery({
    queryKey: ['master-data', 'cost-centers', activeCompanyId],
    queryFn: () => masterDataService.listCostCenters(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  const project = projectQuery.data ?? null
  useEffect(() => {
    if (!project) {
      setForm(EMPTY_FORM)
      return
    }
    setForm({
      name: project.name,
      code: project.code ?? '',
      customerId: project.customerId ?? '',
      manager: project.manager ?? '',
      currencyCode: project.currencyCode ?? 'HNL',
      costCenterId: project.costCenterId ?? '',
      plannedStart: project.plannedStart ?? '',
      plannedEnd: project.plannedEnd ?? '',
      description: project.description ?? '',
    })
  }, [project])

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['project', projectId] })
    queryClient.invalidateQueries({ queryKey: ['project', projectId, 'financial-summary'] })
    queryClient.invalidateQueries({ queryKey: ['projects'] })
    queryClient.invalidateQueries({ queryKey: ['dashboard', 'summary'] })
  }

  const updateMutation = useMutation({
    mutationFn: () =>
      projectService.update(projectId as string, {
        name: form.name.trim(),
        code: form.code.trim() || undefined,
        customerId: form.customerId || null,
        manager: form.manager || null,
        currencyCode: form.currencyCode,
        costCenterId: form.costCenterId || null,
        plannedStart: form.plannedStart || null,
        plannedEnd: form.plannedEnd || null,
        description: form.description.trim() || null,
      }),
    onSuccess: (updated: Project) => {
      invalidate()
      if (context.activeProjectId === updated.id) setActiveProject(updated.id)
    },
  })

  const statusMutation = useMutation({
    mutationFn: (status: ProjectStatus) => projectService.transitionStatus(projectId as string, status),
    onSuccess: invalidate,
  })

  const selectedCustomer = useMemo(
    () => (customersQuery.data ?? []).find((customer) => customer.id === project?.customerId) ?? null,
    [customersQuery.data, project?.customerId],
  )

  if (projectQuery.isLoading) return <LoadingState label="Cargando proyecto…" />
  if (projectQuery.isError || !project) {
    return <ErrorState description="No se pudo cargar el proyecto." onRetry={() => projectQuery.refetch()} />
  }
  if (activeCompanyId && project.companyId !== activeCompanyId) {
    return <EmptyState title="Proyecto fuera de la empresa activa" description="Cambia la empresa activa para abrir este proyecto." />
  }

  const summary = financialQuery.data
  const currency = summary?.currencyCode ?? project.currencyCode ?? 'HNL'

  return (
    <div>
      <header className="nx-page__header">
        <div>
          <p className="nx-home__eyebrow">Proyecto {project.code ?? 'sin código'}</p>
          <h1 className="nx-dashboard__title">{project.name}</h1>
          <p className="nx-field__hint">
            <Badge>{statusLabel(project.status)}</Badge> · Cliente: {selectedCustomer?.legalName ?? 'Sin cliente asignado'}
          </p>
        </div>
        {context.activeProjectId !== project.id ? (
          <Button variant="secondary" onClick={() => setActiveProject(project.id)}>Seleccionar como contexto</Button>
        ) : <Badge tone="info">Proyecto seleccionado</Badge>}
      </header>

      {financialQuery.isLoading ? <LoadingState label="Calculando resumen financiero…" /> : null}
      {financialQuery.isError ? <ErrorState description="No se pudo calcular el resumen financiero." onRetry={() => financialQuery.refetch()} /> : null}
      {summary ? (
        <>
          <Card title="Resumen comercial y rentabilidad">
            <div className="nx-home__grid">
              <StatCard label="Valor contractual" value={money(summary.contractValue, currency)} />
              <StatCard label="Presupuesto de costos BASELINE" value={money(summary.baselineBudget, currency)} />
              <StatCard label="Presupuesto de costos vigente" value={money(summary.currentBudget, currency)} />
              <StatCard label="Utilidad esperada" value={money(summary.expectedProfit, currency)} />
              <StatCard label="Margen esperado" value={percent(summary.expectedMarginPercent)} />
              <StatCard label="Avance físico" value={percent(summary.progressPercent)} />
            </div>
            {summary.contractValue === null ? <p className="nx-field__hint">El valor contractual no se inventa: aparecerá cuando exista un Contrato de venta asociado a este proyecto.</p> : null}
          </Card>

          <Card title="Costos y ejecución">
            <div className="nx-home__grid">
              <StatCard label="Comprometido" value={money(summary.committed, currency)} />
              <StatCard label="Devengado" value={money(summary.accrued, currency)} />
              <StatCard label="Pagado" value={money(summary.paid, currency)} />
              <StatCard label="Disponible de presupuesto" value={money(summary.available, currency)} />
              <StatCard label="Costo real contable" value={money(summary.actualCost, currency)} />
            </div>
          </Card>

          <Card title="Facturación y cobros">
            <div className="nx-home__grid">
              <StatCard label="Facturado al cliente" value={money(summary.invoiced, currency)} />
              <StatCard label="Cobrado" value={money(summary.collected, currency)} />
              <StatCard label="Por cobrar" value={money(summary.receivablesOutstanding, currency)} />
              <StatCard label="Ingreso reconocido" value={money(summary.recognizedRevenue, currency)} />
              <StatCard label="Utilidad contable actual" value={money(summary.actualProfit, currency)} />
              <StatCard label="Margen actual" value={percent(summary.actualMarginPercent)} />
            </div>
          </Card>

          <Card title="Earned Value">
            <div className="nx-home__grid">
              <StatCard label="BAC" value={money(summary.bac, currency)} />
              <StatCard label="PV" value={money(summary.pv, currency)} />
              <StatCard label="EV" value={money(summary.ev, currency)} />
              <StatCard label="AC" value={money(summary.ac, currency)} />
              <StatCard label="CPI" value={summary.cpi ?? '—'} />
              <StatCard label="SPI" value={summary.spi ?? '—'} />
              <StatCard label="ETC" value={money(summary.etc, currency)} />
              <StatCard label="EAC" value={money(summary.eac, currency)} />
              <StatCard label="VAC" value={money(summary.vac, currency)} />
            </div>
          </Card>
        </>
      ) : null}

      <Card title="Estado del proyecto">
        <div className="nx-treasury__actions">
          {(TRANSITIONS[project.status] ?? []).map((transition) => (
            <Button
              key={transition.status}
              variant={transition.status === 'CANCELLED' ? 'ghost' : 'secondary'}
              loading={statusMutation.isPending}
              onClick={() => {
                if (transition.status === 'CANCELLED' && !window.confirm('¿Cancelar este proyecto? La transición quedará registrada en auditoría.')) return
                statusMutation.mutate(transition.status)
              }}
            >
              {transition.label}
            </Button>
          ))}
          {(TRANSITIONS[project.status] ?? []).length === 0 ? <span className="nx-field__hint">No hay más transiciones operativas disponibles.</span> : null}
        </div>
        {statusMutation.isError ? <p className="nx-field__error">{(statusMutation.error as Error).message}</p> : null}
      </Card>

      <Card title="Ficha del proyecto">
        <form onSubmit={(event) => { event.preventDefault(); updateMutation.mutate() }}>
          <Input label="Nombre" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required />
          <Input label="Código" value={form.code} onChange={(event) => setForm({ ...form, code: event.target.value })} />
          <Select label="Cliente" value={form.customerId} onChange={(event) => setForm({ ...form, customerId: event.target.value })}>
            <option value="">Sin cliente asignado</option>
            {(customersQuery.data ?? []).map((customer) => <option key={customer.id} value={customer.id}>{customer.legalName}</option>)}
          </Select>
          <Select label="Responsable" value={form.manager} onChange={(event) => setForm({ ...form, manager: event.target.value })}>
            <option value="">Sin responsable asignado</option>
            {(usersQuery.data ?? []).map((user) => <option key={user.id} value={user.fullName}>{user.fullName}</option>)}
          </Select>
          <Select label="Centro de costo" value={form.costCenterId} onChange={(event) => setForm({ ...form, costCenterId: event.target.value })}>
            <option value="">Sin centro de costo</option>
            {(costCentersQuery.data ?? []).map((item) => <option key={item.id} value={item.id}>{item.code} · {item.name}</option>)}
          </Select>
          <Select label="Moneda" value={form.currencyCode} onChange={(event) => setForm({ ...form, currencyCode: event.target.value })}>
            <option value="HNL">HNL — Lempira hondureño</option>
            <option value="USD">USD — Dólar estadounidense</option>
          </Select>
          <Input label="Inicio previsto" type="date" value={form.plannedStart} onChange={(event) => setForm({ ...form, plannedStart: event.target.value })} />
          <Input label="Final previsto" type="date" value={form.plannedEnd} onChange={(event) => setForm({ ...form, plannedEnd: event.target.value })} />
          <Textarea label="Descripción" value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} />
          <Button type="submit" loading={updateMutation.isPending} disabled={!form.name.trim() || Boolean(form.plannedStart && form.plannedEnd && form.plannedEnd < form.plannedStart)}>Guardar ficha</Button>
          {updateMutation.isSuccess ? <p className="nx-field__hint" role="status">Ficha actualizada.</p> : null}
          {updateMutation.isError ? <p className="nx-field__error" role="alert">{(updateMutation.error as Error).message}</p> : null}
        </form>
      </Card>

      <Card title="Módulos del proyecto">
        <div className="nx-treasury__actions">
          <Link to="/proyectos/wbs">WBS</Link>
          <Link to="/proyectos/presupuestos">Presupuesto de costos</Link>
          <Link to="/proyectos/avances">Avances</Link>
          <Link to="/proyectos/ordenes-de-cambio">Órdenes de cambio</Link>
          <Link to="/comercial/contratos">Contratos de venta</Link>
          <Link to="/comercial/facturacion">Facturación</Link>
          <Link to="/comercial/cobros">Cobros</Link>
        </div>
      </Card>
    </div>
  )
}
