import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Badge,
  Button,
  Card,
  CompanySelector,
  EmptyState,
  ErrorState,
  Input,
  LoadingState,
  Select,
  Table,
  type TableColumn,
} from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { fiscalService } from '../../services/fiscalService'
import { masterDataService } from '../../services/masterDataService'
import type { FiscalPeriod, FiscalPeriodStatus, FiscalYear } from '../../types/fiscal'
import type { Company } from '../../types/masterData'
import { statusLabel } from '../../utils/statusLabels'

export function CompanySettingsPage() {
  const { companies, activeCompanyId, setActiveCompanyId, isLoading, isError, refetch } = useActiveCompany()
  const queryClient = useQueryClient()
  const selectedCompany = companies.find((company) => company.id === activeCompanyId) ?? null

  const [syncedCompanyId, setSyncedCompanyId] = useState<string | null>(null)
  const [form, setForm] = useState({ name: '', code: '', legalName: '', fiscalId: '', country: 'HN', functionalCurrencyCode: 'HNL' })
  if (selectedCompany && selectedCompany.id !== syncedCompanyId) {
    setSyncedCompanyId(selectedCompany.id)
    setForm({
      name: selectedCompany.name,
      code: selectedCompany.code ?? '',
      legalName: selectedCompany.legalName ?? '',
      fiscalId: selectedCompany.fiscalId ?? '',
      country: selectedCompany.country ?? 'HN',
      functionalCurrencyCode: selectedCompany.functionalCurrencyCode ?? 'HNL',
    })
  }

  const yearsQuery = useQuery({
    queryKey: ['fiscal', 'years', activeCompanyId],
    queryFn: () => fiscalService.listYears(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })
  const periodsQuery = useQuery({
    queryKey: ['fiscal', 'periods', activeCompanyId],
    queryFn: () => fiscalService.listPeriods(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  const updateMutation = useMutation({
    mutationFn: () => masterDataService.updateCompany(selectedCompany!.id, {
      name: form.name,
      code: selectedCompany?.code ? undefined : form.code || undefined,
      legalName: form.legalName,
      fiscalId: form.fiscalId,
      country: form.country,
      functionalCurrencyCode: selectedCompany?.functionalCurrencyCode ? undefined : form.functionalCurrencyCode,
    }),
    onSuccess: (updatedCompany: Company) => {
      queryClient.invalidateQueries({ queryKey: ['master-data', 'companies'] })
      setSyncedCompanyId(null)
      setForm((current) => ({ ...current, name: updatedCompany.name }))
    },
  })

  const [yearForm, setYearForm] = useState({ code: '', startDate: '', endDate: '' })
  const createYearMutation = useMutation({
    mutationFn: () => fiscalService.createYear({
      companyId: activeCompanyId as string,
      code: yearForm.code.trim(),
      startDate: yearForm.startDate,
      endDate: yearForm.endDate,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['fiscal', 'years', activeCompanyId] })
      setYearForm({ code: '', startDate: '', endDate: '' })
    },
  })
  const generateMutation = useMutation({
    mutationFn: (yearId: string) => fiscalService.generateMonthlyPeriods(yearId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['fiscal', 'periods', activeCompanyId] })
      queryClient.invalidateQueries({ queryKey: ['fiscal', 'current', activeCompanyId] })
      queryClient.invalidateQueries({ queryKey: ['dashboard', 'summary', activeCompanyId] })
    },
  })
  const statusMutation = useMutation({
    mutationFn: ({ periodId, status }: { periodId: string; status: FiscalPeriodStatus }) => fiscalService.setPeriodStatus(periodId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['fiscal', 'periods', activeCompanyId] })
      queryClient.invalidateQueries({ queryKey: ['fiscal', 'current', activeCompanyId] })
      queryClient.invalidateQueries({ queryKey: ['dashboard', 'summary', activeCompanyId] })
    },
  })

  if (isLoading) return <LoadingState label="Cargando compañías…" />
  if (isError) return <ErrorState description="No se pudieron cargar las compañías." onRetry={() => refetch()} />
  if (companies.length === 0) return <EmptyState icon="tool" title="No hay compañías registradas" description="Crea una compañía antes de editar su perfil." />

  const years = yearsQuery.data ?? []
  const periods = periodsQuery.data ?? []
  const yearById = new Map(years.map((year) => [year.id, year]))
  const periodColumns: TableColumn<FiscalPeriod>[] = [
    { key: 'period', header: 'Período', render: (row) => `${yearById.get(row.fiscalYearId)?.code ?? ''} · P${String(row.periodNumber).padStart(2, '0')}` },
    { key: 'dates', header: 'Fechas', render: (row) => `${row.startDate} → ${row.endDate}` },
    { key: 'status', header: 'Estado', render: (row) => <Badge>{statusLabel(row.status)}</Badge> },
    {
      key: 'actions',
      header: 'Acciones',
      render: (row) => (
        <div className="nx-treasury__actions">
          {row.status === 'OPEN' ? <Button variant="secondary" onClick={() => statusMutation.mutate({ periodId: row.id, status: 'SOFT_CLOSED' })}>Cierre preliminar</Button> : null}
          {row.status === 'SOFT_CLOSED' ? <Button variant="secondary" onClick={() => statusMutation.mutate({ periodId: row.id, status: 'OPEN' })}>Reabrir</Button> : null}
          {row.status !== 'CLOSED' ? <Button variant="secondary" onClick={() => window.confirm('¿Cerrar este período? Los nuevos postings quedarán bloqueados por el Posting Engine.') && statusMutation.mutate({ periodId: row.id, status: 'CLOSED' })}>Cerrar</Button> : null}
        </div>
      ),
    },
  ]

  return (
    <div>
      <header className="nx-page__header"><h1 className="nx-dashboard__title">Configuración</h1></header>
      <Card title="Empresa activa">
        <CompanySelector
          options={companies.map((company) => ({ id: company.id, label: company.name }))}
          value={activeCompanyId}
          onChange={setActiveCompanyId}
        />
      </Card>

      {selectedCompany ? (
        <Card title="Perfil de la compañía">
          <form onSubmit={(event) => { event.preventDefault(); updateMutation.mutate() }}>
            <Input label="Nombre" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required />
            <Input
              label={selectedCompany.code ? 'Código · inmutable' : 'Código · se asigna una sola vez'}
              value={form.code}
              onChange={(event) => setForm({ ...form, code: event.target.value })}
              disabled={Boolean(selectedCompany.code)}
              required={!selectedCompany.code}
            />
            <Input label="Razón social" value={form.legalName} onChange={(event) => setForm({ ...form, legalName: event.target.value })} />
            <Input label="Identificación fiscal / RTN" value={form.fiscalId} onChange={(event) => setForm({ ...form, fiscalId: event.target.value })} />
            <Select label="País" value={form.country} onChange={(event) => setForm({ ...form, country: event.target.value })}>
              <option value="HN">HN — Honduras</option>
            </Select>
            <Select
              label={selectedCompany.functionalCurrencyCode ? 'Moneda funcional · inmutable' : 'Moneda funcional · se asigna una sola vez'}
              value={form.functionalCurrencyCode}
              onChange={(event) => setForm({ ...form, functionalCurrencyCode: event.target.value })}
              disabled={Boolean(selectedCompany.functionalCurrencyCode)}
            >
              <option value="HNL">HNL — Lempira hondureño</option>
              <option value="USD">USD — Dólar estadounidense</option>
            </Select>
            <Button type="submit" loading={updateMutation.isPending} disabled={!form.name.trim() || (!selectedCompany.code && !form.code.trim())}>Guardar cambios</Button>
            {updateMutation.isSuccess ? <p className="nx-field__hint" role="status">Cambios guardados.</p> : null}
            {updateMutation.isError ? <p className="nx-field__error" role="alert">{(updateMutation.error as Error).message}</p> : null}
          </form>
        </Card>
      ) : null}

      <Card title="Años fiscales">
        <p className="nx-field__hint">Crear un año fiscal no genera períodos automáticamente. Después confirma explícitamente “Generar períodos mensuales”.</p>
        <Input label="Código del año fiscal" placeholder="2026" value={yearForm.code} onChange={(event) => setYearForm({ ...yearForm, code: event.target.value })} />
        <Input label="Inicio" type="date" value={yearForm.startDate} onChange={(event) => setYearForm({ ...yearForm, startDate: event.target.value })} />
        <Input label="Fin" type="date" value={yearForm.endDate} onChange={(event) => setYearForm({ ...yearForm, endDate: event.target.value })} />
        <Button
          loading={createYearMutation.isPending}
          disabled={!yearForm.code.trim() || !yearForm.startDate || !yearForm.endDate || yearForm.endDate < yearForm.startDate}
          onClick={() => createYearMutation.mutate()}
        >Crear año fiscal</Button>
        {createYearMutation.isError ? <p className="nx-field__error">{(createYearMutation.error as Error).message}</p> : null}
        {yearsQuery.isLoading ? <LoadingState label="Cargando años fiscales…" /> : null}
        {years.map((year: FiscalYear) => {
          const hasPeriods = periods.some((period) => period.fiscalYearId === year.id)
          return (
            <div key={year.id} className="nx-treasury__actions">
              <strong>{year.code}</strong><span>{year.startDate} → {year.endDate}</span>
              {!hasPeriods ? <Button variant="secondary" loading={generateMutation.isPending} onClick={() => window.confirm(`¿Generar períodos mensuales para ${year.code}?`) && generateMutation.mutate(year.id)}>Generar períodos mensuales</Button> : <Badge tone="success">Períodos generados</Badge>}
            </div>
          )
        })}
        {generateMutation.isError ? <p className="nx-field__error">{(generateMutation.error as Error).message}</p> : null}
      </Card>

      <Card title="Períodos fiscales">
        {periodsQuery.isLoading ? <LoadingState label="Cargando períodos…" /> : periodsQuery.isError ? <ErrorState description="No se pudieron cargar los períodos fiscales." onRetry={() => periodsQuery.refetch()} /> : <Table columns={periodColumns} rows={periods} getRowKey={(row) => row.id} emptyMessage="Todavía no hay períodos fiscales. Crea un año fiscal y genera sus períodos." />}
        {statusMutation.isError ? <p className="nx-field__error">{(statusMutation.error as Error).message}</p> : null}
      </Card>
    </div>
  )
}
