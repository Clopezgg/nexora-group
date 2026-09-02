import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Button,
  Card,
  EmptyState,
  ErrorState,
  LoadingState,
  MoneyInput,
  Select,
  StatCard,
  Table,
  Textarea,
  type TableColumn,
} from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { fiscalService } from '../../services/fiscalService'
import { masterDataService } from '../../services/masterDataService'
import { projectService, type BudgetLineInput } from '../../services/projectService'
import type { WBSNode } from '../../types/project'
import { formatMoney } from '../../utils/currency'
import { RequiresActiveProject } from './RequiresActiveProject'

function formatAmount(value: string | null, currencyCode = 'HNL'): string {
  if (value === null) return '—'
  return formatMoney(Number(value), currencyCode)
}

interface BudgetBreakdownRow { key: string; wbs: string; authorized: number }
interface DraftLine extends BudgetLineInput { key: number }
let draftKey = 1
const makeLine = (): DraftLine => ({ key: draftKey++, authorizedAmount: 0, wbsNodeId: null, economicCategoryId: null, costCenterId: null, fiscalPeriodId: null })

function BudgetLineEditor({
  lines,
  onChange,
  wbs,
  economicCategories,
  costCenters,
  periods,
  requireWbs,
}: {
  lines: DraftLine[]
  onChange: (lines: DraftLine[]) => void
  wbs: WBSNode[]
  economicCategories: Array<{ id: string; code: string; name: string }>
  costCenters: Array<{ id: string; code: string; name: string }>
  periods: Array<{ id: string; periodNumber: number; startDate: string; endDate: string }>
  requireWbs: boolean
}) {
  const update = (key: number, patch: Partial<DraftLine>) => onChange(lines.map((line) => line.key === key ? { ...line, ...patch } : line))
  return <>
    {lines.map((line, index) => <Card key={line.key} title={`Línea ${index + 1}`}>
      <Select label="WBS" value={line.wbsNodeId ?? ''} onChange={(event) => update(line.key, { wbsNodeId: event.target.value || null })}>
        <option value="">{requireWbs ? 'Selecciona WBS' : 'Sin WBS'}</option>
        {wbs.map((node) => <option key={node.id} value={node.id}>{'—'.repeat(node.level)} {node.code} · {node.name}</option>)}
      </Select>
      <Select label="Categoría económica" value={line.economicCategoryId ?? ''} onChange={(event) => update(line.key, { economicCategoryId: event.target.value || null })}>
        <option value="">Sin categoría</option>
        {economicCategories.map((item) => <option key={item.id} value={item.id}>{item.code} · {item.name}</option>)}
      </Select>
      <Select label="Centro de costo" value={line.costCenterId ?? ''} onChange={(event) => update(line.key, { costCenterId: event.target.value || null })}>
        <option value="">Sin centro de costo</option>
        {costCenters.map((item) => <option key={item.id} value={item.id}>{item.code} · {item.name}</option>)}
      </Select>
      <Select label="Período fiscal" value={line.fiscalPeriodId ?? ''} onChange={(event) => update(line.key, { fiscalPeriodId: event.target.value || null })}>
        <option value="">Sin período específico</option>
        {periods.map((period) => <option key={period.id} value={period.id}>P{String(period.periodNumber).padStart(2, '0')} · {period.startDate} → {period.endDate}</option>)}
      </Select>
      <MoneyInput label="Presupuesto de costos autorizado (HNL)" value={line.authorizedAmount || null} onChange={(value) => update(line.key, { authorizedAmount: value ?? 0 })} />
      {lines.length > 1 ? <Button variant="ghost" onClick={() => onChange(lines.filter((candidate) => candidate.key !== line.key))}>Eliminar línea</Button> : null}
    </Card>)}
    <Button variant="secondary" onClick={() => onChange([...lines, makeLine()])}>Agregar línea</Button>
  </>
}

function BudgetAndForecast({ projectId }: { projectId: string }) {
  const queryClient = useQueryClient()
  const { activeCompanyId } = useActiveCompany()
  const [baselineLines, setBaselineLines] = useState<DraftLine[]>([makeLine()])
  const [redistributionLines, setRedistributionLines] = useState<DraftLine[]>([makeLine()])
  const [notes, setNotes] = useState('')

  const summaryQuery = useQuery({ queryKey: ['budget-summary', projectId], queryFn: () => projectService.getBudgetSummary(projectId) })
  const activeBudgetQuery = useQuery({ queryKey: ['budget-active', projectId], queryFn: () => projectService.getActiveBudget(projectId), retry: false })
  const wbsQuery = useQuery({ queryKey: ['wbs', projectId], queryFn: () => projectService.listWbs(projectId) })
  const forecastQuery = useQuery({ queryKey: ['forecast', projectId], queryFn: () => projectService.getForecast(projectId) })
  const categoriesQuery = useQuery({ queryKey: ['master-data', 'economic-categories', activeCompanyId], queryFn: () => masterDataService.listEconomicCategories(activeCompanyId as string), enabled: Boolean(activeCompanyId) })
  const costCentersQuery = useQuery({ queryKey: ['master-data', 'cost-centers', activeCompanyId], queryFn: () => masterDataService.listCostCenters(activeCompanyId as string), enabled: Boolean(activeCompanyId) })
  const periodsQuery = useQuery({ queryKey: ['fiscal', 'periods', activeCompanyId], queryFn: () => fiscalService.listPeriods(activeCompanyId as string), enabled: Boolean(activeCompanyId) })

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['budget-summary', projectId] })
    queryClient.invalidateQueries({ queryKey: ['budget-active', projectId] })
    queryClient.invalidateQueries({ queryKey: ['forecast', projectId] })
    queryClient.invalidateQueries({ queryKey: ['wbs', projectId, 'financial-summary'] })
    queryClient.invalidateQueries({ queryKey: ['project', projectId, 'financial-summary'] })
  }

  const createBaseline = useMutation({
    mutationFn: () => projectService.createBaseline(projectId, {
      currencyCode: 'HNL',
      lines: baselineLines.map(({ key: _key, ...line }) => line),
      notes: notes.trim() || undefined,
    }),
    onSuccess: () => { invalidate(); setBaselineLines([makeLine()]); setNotes('') },
  })
  const redistribute = useMutation({
    mutationFn: () => projectService.redistributeUnassignedBudget(projectId, {
      lines: redistributionLines.map(({ key: _key, ...line }) => line),
      notes: 'Redistribución auditada por WBS desde la interfaz de NEXORA.',
    }),
    onSuccess: () => { invalidate(); setRedistributionLines([makeLine()]) },
  })

  if (summaryQuery.isLoading || forecastQuery.isLoading) return <LoadingState label="Cargando presupuesto…" />
  if (summaryQuery.isError || forecastQuery.isError) return <ErrorState description="No se pudo cargar el presupuesto." onRetry={() => summaryQuery.refetch()} />

  const summary = summaryQuery.data
  const forecast = forecastQuery.data
  const activeBudget = activeBudgetQuery.data
  const showCreateBaseline = !activeBudgetQuery.isLoading && !activeBudget
  const currencyCode = activeBudget?.currencyCode ?? 'HNL'
  const authorized = Number(summary?.authorized ?? 0)
  const accrued = Number(summary?.accrued ?? 0)
  const executedPercent = authorized > 0 ? `${((accrued / authorized) * 100).toFixed(1)}%` : '—'
  const wbsNodes = Array.isArray(wbsQuery.data) ? wbsQuery.data : []
  const wbsById = new Map(wbsNodes.map((node) => [node.id, `${node.code} — ${node.name}`]))
  const authorizedByWbs = new Map<string, BudgetBreakdownRow>()
  for (const line of activeBudget?.lines ?? []) {
    const key = line.wbsNodeId ?? 'unassigned'
    const current = authorizedByWbs.get(key)
    authorizedByWbs.set(key, { key, wbs: line.wbsNodeId ? (wbsById.get(line.wbsNodeId) ?? 'WBS no disponible') : 'Sin WBS asignado', authorized: (current?.authorized ?? 0) + Number(line.authorizedAmount) })
  }
  const breakdownRows = [...authorizedByWbs.values()]
  const breakdownColumns: TableColumn<BudgetBreakdownRow>[] = [
    { key: 'wbs', header: 'WBS', render: (row) => row.wbs },
    { key: 'authorized', header: 'Presupuesto de costos autorizado', render: (row) => formatMoney(row.authorized, currencyCode) },
  ]

  const baselineTotal = baselineLines.reduce((sum, line) => sum + Number(line.authorizedAmount || 0), 0)
  const baselineValid = wbsNodes.length > 0 && baselineLines.length > 0 && baselineLines.every((line) => line.authorizedAmount > 0 && Boolean(line.wbsNodeId))
  const hasOnlyUnassigned = Boolean(activeBudget?.lines.length) && activeBudget!.lines.every((line) => !line.wbsNodeId)
  const historicTotal = (activeBudget?.lines ?? []).reduce((sum, line) => sum + Number(line.authorizedAmount), 0)
  const redistributionTotal = redistributionLines.reduce((sum, line) => sum + Number(line.authorizedAmount || 0), 0)
  const redistributionValid = wbsNodes.length > 0 && redistributionLines.every((line) => line.authorizedAmount > 0 && Boolean(line.wbsNodeId)) && Math.abs(redistributionTotal - historicTotal) < 0.005

  return <div>
    {showCreateBaseline ? <Card title="Crear BASELINE de costos">
      <p className="nx-field__hint"><strong>Este presupuesto representa el COSTO previsto/autorizado de ejecución, no el precio contratado al cliente.</strong> El valor de venta vive en Comercial → Contratos.</p>
      {wbsNodes.length === 0 ? <EmptyState icon="project" title="Crea primero la WBS" description="NEXORA evita congelar accidentalmente todo el presupuesto como “Sin WBS asignado”. Define la estructura WBS y vuelve aquí." /> : <>
        <BudgetLineEditor lines={baselineLines} onChange={setBaselineLines} wbs={wbsNodes} economicCategories={categoriesQuery.data ?? []} costCenters={costCentersQuery.data ?? []} periods={periodsQuery.data ?? []} requireWbs />
        <p><strong>Total BASELINE de costos: {formatMoney(baselineTotal, 'HNL')}</strong></p>
        <Textarea label="Notas del BASELINE" value={notes} onChange={(event) => setNotes(event.target.value)} />
        <Button disabled={!baselineValid || createBaseline.isPending} loading={createBaseline.isPending} onClick={() => window.confirm(`¿Congelar BASELINE de costos por ${formatMoney(baselineTotal, 'HNL')}? No se sobrescribirá; cambios posteriores requerirán una revisión.`) && createBaseline.mutate()}>Congelar BASELINE</Button>
        {createBaseline.isError ? <p className="nx-field__error" role="alert">{(createBaseline.error as Error).message}</p> : null}
      </>}
    </Card> : null}

    {summary ? <div className="nx-home__grid">
      <StatCard label="Presupuesto de costos autorizado" value={formatAmount(summary.authorized, currencyCode)} />
      <StatCard label="Comprometido (total)" value={formatAmount(summary.committed, currencyCode)} />
      <StatCard label="Compromiso abierto" value={formatAmount(summary.openCommitment ?? summary.committed, currencyCode)} />
      <StatCard label="Devengado (costo)" value={formatAmount(summary.accrued, currencyCode)} />
      {Number(summary.advances ?? 0) > 0 ? (
        <StatCard label="Anticipos (prepago, no costo)" value={formatAmount(summary.advances ?? '0', currencyCode)} />
      ) : null}
      <StatCard label="Pagado" value={formatAmount(summary.paid, currencyCode)} />
      <StatCard label="Disponible" value={formatAmount(summary.available, currencyCode)} />
      <StatCard label="Ejecutado" value={executedPercent} />
    </div> : null}

    {activeBudget ? <Card title="Detalle del presupuesto de costos por WBS">
      {wbsQuery.isLoading ? <LoadingState label="Cargando detalle WBS…" /> : wbsQuery.isError ? <ErrorState description="No se pudo cargar el detalle WBS." onRetry={() => wbsQuery.refetch()} /> : <Table columns={breakdownColumns} rows={breakdownRows} getRowKey={(row) => row.key} emptyMessage="El presupuesto activo todavía no tiene líneas autorizadas." />}
    </Card> : null}

    {activeBudget && hasOnlyUnassigned ? <Card title="Distribuir presupuesto histórico por WBS">
      <p className="nx-field__hint">El presupuesto actual está íntegramente “Sin WBS asignado”. Esta operación <strong>no edita ni borra el BASELINE</strong>: crea una versión REVISED auditada y conserva exactamente el total histórico {formatMoney(historicTotal, currencyCode)}. Si ya existe ejecución financiera el backend bloqueará la reclasificación.</p>
      {wbsNodes.length === 0 ? <EmptyState icon="project" title="Crea primero la WBS" description="Se necesita una WBS real para distribuir el histórico." /> : <>
        <BudgetLineEditor lines={redistributionLines} onChange={setRedistributionLines} wbs={wbsNodes} economicCategories={categoriesQuery.data ?? []} costCenters={costCentersQuery.data ?? []} periods={periodsQuery.data ?? []} requireWbs />
        <p><strong>Total a redistribuir: {formatMoney(redistributionTotal, currencyCode)} / histórico: {formatMoney(historicTotal, currencyCode)}</strong></p>
        <Button disabled={!redistributionValid || redistribute.isPending} loading={redistribute.isPending} onClick={() => window.confirm('¿Crear una revisión auditada que redistribuya el presupuesto histórico por WBS sin cambiar su total?') && redistribute.mutate()}>Distribuir presupuesto por WBS</Button>
        {redistribute.isError ? <p className="nx-field__error" role="alert">{(redistribute.error as Error).message}</p> : null}
      </>}
    </Card> : null}

    {forecast ? <Card title="Forecast (Earned Value)">
      <p className="nx-field__hint">BAC usa el presupuesto de COSTOS vigente; AC usa costo real contabilizado del proyecto. Los indicadores no calculables muestran “—”.</p>
      <div className="nx-home__grid">
        <StatCard label="BAC" value={formatAmount(forecast.bac, currencyCode)} /><StatCard label="PV" value={formatAmount(forecast.pv, currencyCode)} /><StatCard label="EV" value={formatAmount(forecast.ev, currencyCode)} /><StatCard label="AC" value={formatAmount(forecast.ac, currencyCode)} /><StatCard label="CPI" value={forecast.cpi ?? '—'} /><StatCard label="SPI" value={forecast.spi ?? '—'} /><StatCard label="ETC" value={formatAmount(forecast.etc, currencyCode)} /><StatCard label="EAC" value={formatAmount(forecast.eac, currencyCode)} /><StatCard label="VAC" value={formatAmount(forecast.vac, currencyCode)} />
      </div>
      {forecast.pv === null ? <EmptyState icon="chart" title="Forecast incompleto" description="Registra un avance de proyecto en Avances para calcular PV/EV/CPI/SPI." /> : null}
    </Card> : null}
  </div>
}

export function BudgetPage() {
  return <div><h1 className="nx-dashboard__title">Presupuesto de costos</h1><RequiresActiveProject>{(projectId) => <BudgetAndForecast projectId={projectId} />}</RequiresActiveProject></div>
}
