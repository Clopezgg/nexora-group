import { useMemo, useState } from 'react'
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
  Tabs,
  Textarea,
} from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { crmService } from '../../services/crmService'
import { masterDataService } from '../../services/masterDataService'
import { projectService } from '../../services/projectService'
import type { Project } from '../../types/project'
import { formatMoney } from '../../utils/currency'
import { projectStatusLabel } from '../../utils/statusLabels'
import { useActiveContext } from '../context/useActiveContext'
import { ProjectContractsTab } from './ProjectContractsTab'
import { ProjectStatusCard } from './ProjectStatusCard'
import './ProjectDetailPage.css'

function money(value: string | null, currency: string) {
  return value === null ? '—' : formatMoney(value, currency)
}

function percent(value: string | null) {
  return value === null ? '—' : `${Number(value).toFixed(1)}%`
}

function ProjectEditForm({
  project,
  functionalCurrencyCode,
  customers,
  users,
  costCenters,
  onUpdated,
}: {
  project: Project
  functionalCurrencyCode: string
  customers: Array<{ id: string; legalName: string }>
  users: Array<{ id: string; fullName: string }>
  costCenters: Array<{ id: string; code: string; name: string }>
  onUpdated: (updated: Project) => void
}) {
  const [form, setForm] = useState({
    name: project.name,
    code: project.code ?? '',
    customerId: project.customerId ?? '',
    managerUserId: project.managerUserId ?? '',
    currencyCode: project.currencyCode ?? functionalCurrencyCode,
    costCenterId: project.costCenterId ?? '',
    plannedStart: project.plannedStart ?? '',
    plannedEnd: project.plannedEnd ?? '',
    description: project.description ?? '',
    addressLine1: project.addressLine1 ?? '',
    addressLine2: project.addressLine2 ?? '',
    city: project.city ?? '',
    stateDepartment: project.stateDepartment ?? '',
    country: project.country ?? '',
    locationReference: project.locationReference ?? '',
  })

  const updateMutation = useMutation({
    mutationFn: () =>
      projectService.update(project.id, {
        name: form.name.trim(),
        code: form.code.trim() || undefined,
        customerId: form.customerId || null,
        managerUserId: form.managerUserId || null,
        currencyCode: functionalCurrencyCode,
        costCenterId: form.costCenterId || null,
        plannedStart: form.plannedStart || null,
        plannedEnd: form.plannedEnd || null,
        description: form.description.trim() || null,
        addressLine1: form.addressLine1.trim() || null,
        addressLine2: form.addressLine2.trim() || null,
        city: form.city.trim() || null,
        stateDepartment: form.stateDepartment.trim() || null,
        country: form.country.trim() || null,
        locationReference: form.locationReference.trim() || null,
      }),
    onSuccess: onUpdated,
  })

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault()
        updateMutation.mutate()
      }}
    >
      <Input
        label="Nombre"
        value={form.name}
        onChange={(event) => setForm({ ...form, name: event.target.value })}
        required
      />
      <Input
        label="Código"
        value={form.code}
        onChange={(event) => setForm({ ...form, code: event.target.value })}
      />
      <Select
        label="Cliente"
        value={form.customerId}
        onChange={(event) => setForm({ ...form, customerId: event.target.value })}
      >
        <option value="">Sin cliente asignado</option>
        {customers.map((customer) => (
          <option key={customer.id} value={customer.id}>
            {customer.legalName}
          </option>
        ))}
      </Select>
      <Select
        label="Responsable"
        value={form.managerUserId}
        onChange={(event) => setForm({ ...form, managerUserId: event.target.value })}
      >
        <option value="">Sin responsable asignado</option>
        {users.map((user) => (
          <option key={user.id} value={user.id}>
            {user.fullName}
          </option>
        ))}
      </Select>
      <Select
        label="Centro de costo"
        value={form.costCenterId}
        onChange={(event) => setForm({ ...form, costCenterId: event.target.value })}
      >
        <option value="">Sin centro de costo</option>
        {costCenters.map((item) => (
          <option key={item.id} value={item.id}>
            {item.code} · {item.name}
          </option>
        ))}
      </Select>
      <Input label="Moneda funcional" value={functionalCurrencyCode} readOnly />
      <Input
        label="Inicio previsto"
        type="date"
        value={form.plannedStart}
        onChange={(event) => setForm({ ...form, plannedStart: event.target.value })}
      />
      <Input
        label="Final previsto"
        type="date"
        value={form.plannedEnd}
        onChange={(event) => setForm({ ...form, plannedEnd: event.target.value })}
      />
      <Input
        label="Dirección de la obra"
        value={form.addressLine1}
        onChange={(event) => setForm({ ...form, addressLine1: event.target.value })}
      />
      <Input
        label="Ciudad"
        value={form.city}
        onChange={(event) => setForm({ ...form, city: event.target.value })}
      />
      <Input
        label="Departamento / Estado"
        value={form.stateDepartment}
        onChange={(event) => setForm({ ...form, stateDepartment: event.target.value })}
      />
      <Input
        label="País (ISO-2)"
        value={form.country}
        maxLength={2}
        onChange={(event) => setForm({ ...form, country: event.target.value.toUpperCase() })}
      />
      <Textarea
        label="Cómo llegar / referencia"
        value={form.locationReference}
        onChange={(event) => setForm({ ...form, locationReference: event.target.value })}
      />
      <Textarea
        label="Descripción"
        value={form.description}
        onChange={(event) => setForm({ ...form, description: event.target.value })}
      />
      <Button
        type="submit"
        loading={updateMutation.isPending}
        disabled={
          !form.name.trim() ||
          Boolean(form.plannedStart && form.plannedEnd && form.plannedEnd < form.plannedStart)
        }
      >
        Guardar ficha
      </Button>
      {updateMutation.isSuccess ? (
        <p className="nx-field__hint" role="status">
          Ficha actualizada.
        </p>
      ) : null}
      {updateMutation.isError ? (
        <p className="nx-field__error" role="alert">
          {(updateMutation.error as Error).message}
        </p>
      ) : null}
    </form>
  )
}

export function ProjectDetailPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const queryClient = useQueryClient()
  const { activeCompanyId, activeCompany } = useActiveCompany()
  const { context, setActiveProject } = useActiveContext()

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

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['project', projectId] })
    queryClient.invalidateQueries({ queryKey: ['project', projectId, 'financial-summary'] })
    queryClient.invalidateQueries({ queryKey: ['projects'] })
    queryClient.invalidateQueries({ queryKey: ['dashboard', 'summary'] })
  }

  const selectedCustomer = useMemo(
    () =>
      (customersQuery.data ?? []).find((customer) => customer.id === project?.customerId) ?? null,
    [customersQuery.data, project?.customerId],
  )

  if (projectQuery.isLoading) return <LoadingState label="Cargando proyecto…" />
  if (projectQuery.isError || !project) {
    return (
      <ErrorState
        description="No se pudo cargar el proyecto."
        onRetry={() => projectQuery.refetch()}
      />
    )
  }
  if (!activeCompanyId || !activeCompany) {
    return (
      <EmptyState
        title="Selecciona una compañía"
        description="El detalle financiero del proyecto requiere una compañía activa explícita."
      />
    )
  }
  if (project.companyId !== activeCompanyId) {
    return (
      <EmptyState
        title="Proyecto fuera de la empresa activa"
        description="Cambia la empresa activa para abrir este proyecto."
      />
    )
  }
  if (!activeCompany.functionalCurrencyCode) {
    return (
      <EmptyState
        icon="warning"
        title="La compañía activa no tiene moneda funcional"
        description="Configura la moneda funcional antes de consultar cifras del proyecto."
      />
    )
  }

  const summary = financialQuery.data
  const functionalCurrency = activeCompany.functionalCurrencyCode
  const projectCurrencyMismatch = Boolean(
    project.currencyCode && project.currencyCode !== functionalCurrency,
  )
  const summaryCurrencyMismatch = Boolean(
    summary?.currencyCode && summary.currencyCode !== functionalCurrency,
  )
  if (projectCurrencyMismatch || summaryCurrencyMismatch) {
    return (
      <ErrorState description="La moneda del proyecto no coincide con la moneda funcional de la compañía activa. NEXORA bloquea la vista financiera para evitar mezclar monedas sin una política FX autoritativa." />
    )
  }
  const currency = functionalCurrency
  const managerName =
    (usersQuery.data ?? []).find((u) => u.id === project.managerUserId)?.fullName ??
    project.manager ??
    'Sin responsable'
  const locationText =
    [project.addressLine1, project.city, project.stateDepartment, project.country]
      .filter(Boolean)
      .join(', ') || 'Sin ubicación registrada'
  const planText =
    project.plannedStart && project.plannedEnd
      ? `${project.plannedStart} → ${project.plannedEnd}`
      : '—'

  const statusCard = (
    <ProjectStatusCard
      project={project}
      onUpdated={(updated) => {
        if (context.activeProjectId === updated.id) setActiveProject(updated.id)
      }}
    />
  )

  const resumenTab = (
    <>
      {financialQuery.isLoading ? <LoadingState label="Calculando resumen financiero…" /> : null}
      {financialQuery.isError ? (
        <ErrorState
          description="No se pudo calcular el resumen financiero."
          onRetry={() => financialQuery.refetch()}
        />
      ) : null}
      {summary ? (
        <Card title="Resumen comercial y rentabilidad">
          <div className="nx-home__grid">
            <StatCard label="Valor comercial contratado" value={money(summary.contractValue, currency)} />
            <StatCard label="Presupuesto BASELINE" value={money(summary.baselineBudget, currency)} />
            <StatCard label="Presupuesto vigente" value={money(summary.currentBudget, currency)} />
            <StatCard label="Costo contratado de ejecución" value={money(summary.executionContractValue, currency)} />
            <StatCard label="Órdenes de compra comprometidas" value={money(summary.poCommitted, currency)} />
            <StatCard label="Pagado a contratos de ejecución" value={money(summary.executionContractPaid, currency)} />
            <StatCard label="Saldo contractual de ejecución" value={money(summary.executionContractBalance, currency)} />
            <StatCard label="Devengado" value={money(summary.accrued, currency)} />
            <StatCard label="Pagado" value={money(summary.paid, currency)} />
            <StatCard label="Costo real GL" value={money(summary.actualCost, currency)} />
            <StatCard label="Utilidad esperada" value={money(summary.expectedProfit, currency)} />
            <StatCard label="Utilidad actual" value={money(summary.actualProfit, currency)} />
            <StatCard label="Avance físico" value={percent(summary.progressPercent)} />
          </div>
          {summary.contractValue === null ? (
            <p className="nx-field__hint">
              El valor comercial aparecerá cuando exista un contrato de venta asociado; no se
              confunde con contratos de ejecución.
            </p>
          ) : null}
        </Card>
      ) : null}
    </>
  )

  const finanzasTab = summary ? (
    <>
      <Card title="Costos y ejecución">
        <div className="nx-home__grid">
          <StatCard label="Costo contratado de ejecución" value={money(summary.executionContractValue, currency)} />
          <StatCard label="Pagado a contratos de ejecución" value={money(summary.executionContractPaid, currency)} />
          <StatCard label="Saldo contractual de ejecución" value={money(summary.executionContractBalance, currency)} />
          <StatCard label="Órdenes de compra comprometidas" value={money(summary.poCommitted, currency)} />
          <StatCard label="Compromiso abierto" value={money(summary.openCommitment ?? summary.committed, currency)} />
          <StatCard label="Devengado / costo reconocido (AP)" value={money(summary.accrued, currency)} />
          <StatCard label="Pagado (AP)" value={money(summary.paid, currency)} />
          {summary.available !== null ? (
            <StatCard label="Disponible de presupuesto" value={money(summary.available, currency)} />
          ) : (
            <>
              <StatCard label="Presupuesto autorizado" value="Sin configurar" />
              <StatCard label="Exposición sin presupuesto" value={money(summary.unbudgetedExposure ?? '0', currency)} />
            </>
          )}
          <StatCard label="Costo real contable (GL)" value={money(summary.actualCost, currency)} />
        </div>
        {summary.available === null ? (
          <p className="nx-field__hint">
            Este proyecto no tiene un presupuesto BASELINE. La cifra mostrada es exposición real,
            no un disponible negativo.{' '}
            <Link to="/proyectos/presupuestos">Configurar WBS y presupuesto</Link>.
          </p>
        ) : null}
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
  ) : (
    <EmptyState icon="chart" title="Sin resumen financiero disponible todavía" />
  )

  const fichaTab = (
    <>
      {statusCard}
      <Card title="Ficha del proyecto">
        <ProjectEditForm
          key={project.id}
          project={project}
          functionalCurrencyCode={functionalCurrency}
          customers={customersQuery.data ?? []}
          users={usersQuery.data ?? []}
          costCenters={costCentersQuery.data ?? []}
          onUpdated={(updated) => {
            invalidate()
            if (context.activeProjectId === updated.id) setActiveProject(updated.id)
          }}
        />
      </Card>
    </>
  )

  const accionesTab = (
    <>
      <Card title="Qué hacer ahora">
        <p className="nx-field__hint">
          Trabaja por proceso, no por módulos técnicos. Para obligaciones de contratistas usa
          primero la pestaña Contratos: desde allí preparas la obligación y pagas la próxima cuota
          con contexto contractual.
        </p>
        <div className="nx-treasury__actions">
          <Link to="/proyectos/wbs">Estructurar alcance (WBS)</Link>
          <Link to="/proyectos/presupuestos">Configurar presupuesto</Link>
          <Link to="/proyectos/avances">Registrar avance físico</Link>
          <Link to="/proyectos/ordenes-de-cambio">Gestionar cambio</Link>
        </div>
      </Card>
      <Card title="Ciclo comercial del proyecto">
        <div className="nx-treasury__actions">
          <Link to="/comercial/contratos">Contrato con cliente</Link>
          <Link to="/comercial/facturacion">Facturar al cliente</Link>
          <Link to="/comercial/cobros">Registrar cobro</Link>
        </div>
      </Card>
      <Card title="Excepciones financieras">
        <p className="nx-field__hint">
          Cuentas por pagar se usa para facturas u obligaciones sueltas y para aprobaciones
          pendientes. Los pagos contractuales normales deben iniciarse desde Contratos.
        </p>
        <div className="nx-treasury__actions">
          <Link to="/finanzas/cuentas-por-pagar">Abrir cuentas por pagar</Link>
          <Link to="/finanzas/inspector">Inspeccionar transacción</Link>
        </div>
      </Card>
    </>
  )

  return (
    <div className="nx-object-page">
      <header className="nx-object-header">
        <div className="nx-object-header__top">
          <div>
            <p className="nx-object-header__eyebrow">Proyecto · {project.code ?? 'sin código'}</p>
            <h1 className="nx-dashboard__title">{project.name}</h1>
          </div>
          <div className="nx-object-header__actions">
            <Badge>{projectStatusLabel(project.status)}</Badge>
            {context.activeProjectId !== project.id ? (
              <Button variant="secondary" onClick={() => setActiveProject(project.id)}>
                Seleccionar como contexto
              </Button>
            ) : (
              <Badge tone="info">Contexto activo</Badge>
            )}
          </div>
        </div>
        <dl className="nx-object-header__facts">
          <div>
            <dt>Cliente</dt>
            <dd>{selectedCustomer?.legalName ?? 'Sin cliente asignado'}</dd>
          </div>
          <div>
            <dt>Responsable</dt>
            <dd>{managerName}</dd>
          </div>
          <div>
            <dt>Ubicación</dt>
            <dd>{locationText}</dd>
          </div>
          <div>
            <dt>Plan</dt>
            <dd>{planText}</dd>
          </div>
          {summary ? (
            <>
              <div>
                <dt>Costo contratado de ejecución</dt>
                <dd>{money(summary.executionContractValue, currency)}</dd>
              </div>
              <div>
                <dt>Saldo contractual de ejecución</dt>
                <dd>{money(summary.executionContractBalance, currency)}</dd>
              </div>
            </>
          ) : null}
        </dl>
      </header>

      <Tabs
        items={[
          { key: 'resumen', label: 'Resumen', content: resumenTab },
          { key: 'finanzas', label: 'Finanzas', content: finanzasTab },
          {
            key: 'contratos',
            label: 'Contratos y pagos',
            content: <ProjectContractsTab companyId={project.companyId} projectId={project.id} />,
          },
          { key: 'acciones', label: 'Acciones', content: accionesTab },
          { key: 'ficha', label: 'Ficha y estado', content: fichaTab },
        ]}
      />
    </div>
  )
}
