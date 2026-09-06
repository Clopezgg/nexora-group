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
import type {
  Account,
  Company,
  ResourcePostingConfig,
  ResourcePostingSource,
} from '../../types/masterData'
import { statusLabel } from '../../utils/statusLabels'
import { BuildInfoCard } from './BuildInfoCard'
import { ThemeSettingsCard } from './ThemeSettingsCard'

function CompanyProfileForm({ company }: { company: Company }) {
  const queryClient = useQueryClient()
  const advanceAccountsQuery = useQuery({
    queryKey: ['master-data', 'accounts', company.id, 'supplier-advance'],
    queryFn: () => masterDataService.listAccounts(company.id),
  })
  const [form, setForm] = useState({
    name: company.name,
    code: company.code ?? '',
    legalName: company.legalName ?? '',
    fiscalId: company.fiscalId ?? '',
    country: company.country ?? 'HN',
    functionalCurrencyCode: company.functionalCurrencyCode ?? 'HNL',
    voucherPayerName: company.voucherPayerName ?? '',
    voucherApproverName: company.voucherApproverName ?? '',
    tradeName: company.tradeName ?? '',
    addressLine1: company.addressLine1 ?? '',
    addressLine2: company.addressLine2 ?? '',
    city: company.city ?? '',
    stateDepartment: company.stateDepartment ?? '',
    phone: company.phone ?? '',
    email: company.email ?? '',
    website: company.website ?? '',
    voucherFooterText: company.voucherFooterText ?? '',
    supplierAdvanceAccountId: company.supplierAdvanceAccountId ?? '',
  })

  const updateMutation = useMutation({
    mutationFn: () => masterDataService.updateCompany(company.id, {
      name: form.name,
      code: company.code ? undefined : form.code || undefined,
      legalName: form.legalName,
      fiscalId: form.fiscalId,
      country: form.country,
      functionalCurrencyCode: company.functionalCurrencyCode ? undefined : form.functionalCurrencyCode,
      voucherPayerName: company.voucherPayerName ? undefined : form.voucherPayerName || undefined,
      voucherApproverName: form.voucherApproverName || undefined,
      tradeName: form.tradeName || undefined,
      addressLine1: form.addressLine1 || undefined,
      addressLine2: form.addressLine2 || undefined,
      city: form.city || undefined,
      stateDepartment: form.stateDepartment || undefined,
      phone: form.phone || undefined,
      email: form.email || undefined,
      website: form.website || undefined,
      voucherFooterText: form.voucherFooterText || undefined,
      supplierAdvanceAccountId: form.supplierAdvanceAccountId || undefined,
    }),
    onSuccess: (updatedCompany: Company) => {
      queryClient.invalidateQueries({ queryKey: ['master-data', 'companies'] })
      setForm({
        name: updatedCompany.name,
        code: updatedCompany.code ?? '',
        legalName: updatedCompany.legalName ?? '',
        fiscalId: updatedCompany.fiscalId ?? '',
        country: updatedCompany.country ?? 'HN',
        functionalCurrencyCode: updatedCompany.functionalCurrencyCode ?? 'HNL',
        voucherPayerName: updatedCompany.voucherPayerName ?? '',
        voucherApproverName: updatedCompany.voucherApproverName ?? '',
        tradeName: updatedCompany.tradeName ?? '',
        addressLine1: updatedCompany.addressLine1 ?? '',
        addressLine2: updatedCompany.addressLine2 ?? '',
        city: updatedCompany.city ?? '',
        stateDepartment: updatedCompany.stateDepartment ?? '',
        phone: updatedCompany.phone ?? '',
        email: updatedCompany.email ?? '',
        website: updatedCompany.website ?? '',
        voucherFooterText: updatedCompany.voucherFooterText ?? '',
        supplierAdvanceAccountId: updatedCompany.supplierAdvanceAccountId ?? '',
      })
    },
  })

  return (
    <form onSubmit={(event) => { event.preventDefault(); updateMutation.mutate() }}>
      <Input label="Nombre" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required />
      <Input
        label={company.code ? 'Código · inmutable' : 'Código · se asigna una sola vez'}
        value={form.code}
        onChange={(event) => setForm({ ...form, code: event.target.value })}
        disabled={Boolean(company.code)}
        required={!company.code}
      />
      <Input label="Razón social" value={form.legalName} onChange={(event) => setForm({ ...form, legalName: event.target.value })} />
      <Input label="Identificación fiscal / RTN" value={form.fiscalId} onChange={(event) => setForm({ ...form, fiscalId: event.target.value })} />
      <Input
        label={company.voucherPayerName ? 'Pagador de comprobantes · inmutable' : 'Pagador de comprobantes · se asigna una sola vez'}
        value={form.voucherPayerName}
        onChange={(event) => setForm({ ...form, voucherPayerName: event.target.value })}
        disabled={Boolean(company.voucherPayerName)}
      />
      <Input
        label="Aprobador de comprobantes · configurable"
        value={form.voucherApproverName}
        onChange={(event) => setForm({ ...form, voucherApproverName: event.target.value })}
      />
      <Select
        label="Cuenta de anticipos a proveedores"
        value={form.supplierAdvanceAccountId}
        onChange={(event) => setForm({ ...form, supplierAdvanceAccountId: event.target.value })}
      >
        <option value="">Sin configurar · los anticipos no pueden registrarse</option>
        {(advanceAccountsQuery.data ?? [])
          .filter((account) => account.accountType === 'ASSET' && account.isPostable)
          .map((account) => (
            <option key={account.id} value={account.id}>{account.code} — {account.name}</option>
          ))}
      </Select>
      <p className="nx-field__hint">
        Los anticipos se contabilizan como activo hasta su aplicación; no son gasto al pagarse.
      </p>

      <fieldset style={{ border: 0, padding: 0, margin: '12px 0 0' }}>
        <legend className="nx-field__label">Documentos · datos impresos en el comprobante</legend>
        <Input label="Nombre comercial" value={form.tradeName} onChange={(e) => setForm({ ...form, tradeName: e.target.value })} />
        <Input label="Dirección (línea 1)" value={form.addressLine1} onChange={(e) => setForm({ ...form, addressLine1: e.target.value })} />
        <Input label="Dirección (línea 2)" value={form.addressLine2} onChange={(e) => setForm({ ...form, addressLine2: e.target.value })} />
        <Input label="Ciudad" value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} />
        <Input label="Departamento" value={form.stateDepartment} onChange={(e) => setForm({ ...form, stateDepartment: e.target.value })} />
        <Input label="Teléfono" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
        <Input label="Correo" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        <Input label="Sitio web" value={form.website} onChange={(e) => setForm({ ...form, website: e.target.value })} />
        <Input label="Texto de pie del comprobante" value={form.voucherFooterText} onChange={(e) => setForm({ ...form, voucherFooterText: e.target.value })} />
      </fieldset>
      <Select label="País" value={form.country} onChange={(event) => setForm({ ...form, country: event.target.value })}>
        <option value="HN">HN — Honduras</option>
      </Select>
      <Select
        label={company.functionalCurrencyCode ? 'Moneda funcional · inmutable' : 'Moneda funcional · se asigna una sola vez'}
        value={form.functionalCurrencyCode}
        onChange={(event) => setForm({ ...form, functionalCurrencyCode: event.target.value })}
        disabled={Boolean(company.functionalCurrencyCode)}
      >
        <option value="HNL">HNL — Lempira hondureño</option>
        <option value="USD">USD — Dólar estadounidense</option>
      </Select>
      <Button type="submit" loading={updateMutation.isPending} disabled={!form.name.trim() || (!company.code && !form.code.trim())}>Guardar cambios</Button>
      {updateMutation.isSuccess ? <p className="nx-field__hint" role="status">Cambios guardados.</p> : null}
      {updateMutation.isError ? <p className="nx-field__error" role="alert">{(updateMutation.error as Error).message}</p> : null}
    </form>
  )
}

const RESOURCE_POSTING_SOURCES: Array<{ source: ResourcePostingSource; label: string; detail: string }> = [
  { source: 'FUEL', label: 'Combustible', detail: 'Contabiliza cada registro de combustible como FUE.' },
  { source: 'MAINTENANCE', label: 'Mantenimiento', detail: 'Contabiliza el costo total al cerrar una orden como MNT.' },
  { source: 'LABOR', label: 'Mano de obra', detail: 'Contabiliza el costo calculado al aprobar horas como LAB.' },
]

function ResourcePostingRow({
  companyId,
  source,
  label,
  detail,
  config,
  expenseAccounts,
  offsetAccounts,
}: {
  companyId: string
  source: ResourcePostingSource
  label: string
  detail: string
  config: ResourcePostingConfig | undefined
  expenseAccounts: Account[]
  offsetAccounts: Account[]
}) {
  const queryClient = useQueryClient()
  const [expenseAccountId, setExpenseAccountId] = useState(config?.expenseAccountId ?? '')
  const [offsetAccountId, setOffsetAccountId] = useState(config?.offsetAccountId ?? '')
  const [active, setActive] = useState(config?.active ?? true)
  const save = useMutation({
    mutationFn: () => masterDataService.saveResourcePostingConfig(companyId, source, {
      expenseAccountId,
      offsetAccountId,
      active,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['master-data', 'resource-posting-configs', companyId] })
    },
  })

  return (
    <Card title={label}>
      <p className="nx-field__hint">{detail}</p>
      <Select label="Cuenta de gasto (débito)" value={expenseAccountId} onChange={(event) => setExpenseAccountId(event.target.value)}>
        <option value="">Selecciona una cuenta EXPENSE postable…</option>
        {expenseAccounts.map((account) => <option key={account.id} value={account.id}>{account.code} — {account.name}</option>)}
      </Select>
      <Select label="Cuenta de contrapartida (crédito)" value={offsetAccountId} onChange={(event) => setOffsetAccountId(event.target.value)}>
        <option value="">Selecciona una cuenta LIABILITY postable…</option>
        {offsetAccounts.map((account) => <option key={account.id} value={account.id}>{account.code} — {account.name}</option>)}
      </Select>
      <label className="nx-field">
        <span className="nx-field__label">Estado</span>
        <select className="nx-select" value={active ? 'ACTIVE' : 'INACTIVE'} onChange={(event) => setActive(event.target.value === 'ACTIVE')}>
          <option value="ACTIVE">Activo</option>
          <option value="INACTIVE">Inactivo</option>
        </select>
      </label>
      <div className="nx-treasury__actions">
        <Badge tone={config?.active ? 'success' : 'neutral'}>{config ? (config.active ? 'Configurado' : 'Configurado · inactivo') : 'Configuración requerida'}</Badge>
        <Button loading={save.isPending} disabled={!expenseAccountId || !offsetAccountId || expenseAccountId === offsetAccountId} onClick={() => save.mutate()}>
          Guardar mapeo
        </Button>
      </div>
      {save.isSuccess ? <p className="nx-field__hint" role="status">Mapeo contable guardado.</p> : null}
      {save.isError ? <p className="nx-field__error" role="alert">{(save.error as Error).message}</p> : null}
    </Card>
  )
}

function ResourcePostingSettings({ companyId }: { companyId: string }) {
  const accountsQuery = useQuery({
    queryKey: ['master-data', 'accounts', companyId, 'resource-posting'],
    queryFn: () => masterDataService.listAccounts(companyId),
  })
  const configsQuery = useQuery({
    queryKey: ['master-data', 'resource-posting-configs', companyId],
    queryFn: () => masterDataService.listResourcePostingConfigs(companyId),
  })

  if (accountsQuery.isLoading || configsQuery.isLoading) return <LoadingState label="Cargando configuración contable de recursos…" />
  if (accountsQuery.isError || configsQuery.isError) {
    return <ErrorState description="No se pudo cargar la configuración contable automática." onRetry={() => { accountsQuery.refetch(); configsQuery.refetch() }} />
  }

  const accounts = accountsQuery.data ?? []
  const configs = configsQuery.data ?? []
  const expenseAccounts = accounts.filter((account) => account.isPostable && account.accountType === 'EXPENSE')
  const offsetAccounts = accounts.filter((account) => account.isPostable && account.accountType === 'LIABILITY')

  return (
    <Card title="Posting automático de recursos">
      <p className="nx-field__hint">
        Estas cuentas son propiedad de la compañía. NEXORA no utiliza códigos contables hardcodeados: si un origen no está configurado y activo, el evento financiero se bloquea antes de quedar sin asiento.
      </p>
      {expenseAccounts.length === 0 || offsetAccounts.length === 0 ? (
        <p className="nx-field__error" role="alert">Necesitas al menos una cuenta EXPENSE y una LIABILITY postables para habilitar estos postings.</p>
      ) : null}
      <div className="nx-dashboard__kpi-grid">
        {RESOURCE_POSTING_SOURCES.map(({ source, label, detail }) => {
          const config = configs.find((item) => item.sourceType === source)
          return (
            <ResourcePostingRow
              key={`${source}-${config?.id ?? 'new'}`}
              companyId={companyId}
              source={source}
              label={label}
              detail={detail}
              config={config}
              expenseAccounts={expenseAccounts}
              offsetAccounts={offsetAccounts}
            />
          )
        })}
      </div>
    </Card>
  )
}

export function CompanySettingsPage() {
  const { companies, activeCompanyId, setActiveCompanyId, isLoading, isError, refetch } = useActiveCompany()
  const queryClient = useQueryClient()
  const selectedCompany = companies.find((company) => company.id === activeCompanyId) ?? null

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

  const years = Array.isArray(yearsQuery.data) ? yearsQuery.data : []
  const periods = Array.isArray(periodsQuery.data) ? periodsQuery.data : []
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
          <CompanyProfileForm key={selectedCompany.id} company={selectedCompany} />
        </Card>
      ) : null}

      <ThemeSettingsCard
        companyId={activeCompanyId}
        companyDefaultThemeId={selectedCompany?.defaultThemeId ?? null}
        companyDefaultDensity={selectedCompany?.defaultDensity ?? null}
      />

      {activeCompanyId ? <ResourcePostingSettings key={activeCompanyId} companyId={activeCompanyId} /> : null}

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

      <BuildInfoCard />
    </div>
  )
}
