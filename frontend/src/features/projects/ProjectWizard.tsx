import { useMemo, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Button, Input, Select, Textarea } from '../../design-system'
import { projectService } from '../../services/projectService'
import { documentService } from '../../services/documentService'
import type { Project } from '../../types/project'
import type { Supplier } from '../../types/procurement'
import { formatMoney } from '../../utils/currency'
import { businessTodayIso } from '../../utils/businessDate'
import './ProjectWizard.css'

interface WizardProps {
  companyId: string
  customers: Array<{ id: string; legalName: string }>
  users: Array<{ id: string; fullName: string }>
  costCenters: Array<{ id: string; code: string; name: string }>
  suppliers: Supplier[]
  onCreated: (project: Project) => void
}

const STEPS = [
  'Datos generales',
  'Ubicación',
  'Alcance y fechas',
  'Equipo',
  'WBS inicial',
  'Presupuesto',
  'Contrato de ejecución',
  'Documentos',
  'Revisión',
] as const

const EMPTY = {
  name: '', code: '', customerId: '', currencyCode: 'HNL', description: '',
  addressLine1: '', addressLine2: '', city: '', stateDepartment: '', country: 'HN', locationReference: '',
  plannedStart: '', plannedEnd: '', costCenterId: '', managerUserId: '',
  wbsCode: '', wbsName: '',
  baselineAmount: '',
  contractSupplierId: '', contractNumber: '', contractCategory: 'LABOR', contractValue: '',
  contractStartDate: businessTodayIso(), contractEndDate: '', advanceAmount: '',
  advanceDueDate: '', retentionPercentage: '0', paymentTermsType: 'MONTHLY', regularMonths: '7', dueDay: '1',
}

function cents(value: string): bigint | null {
  const match = value.trim().match(/^(\d+)(?:\.(\d{1,2}))?$/)
  if (!match) return null
  return BigInt(match[1]) * 100n + BigInt((match[2] ?? '').padEnd(2, '0'))
}

function isPositiveMoney(value: string) {
  const amount = cents(value)
  return amount !== null && amount > 0n
}

export function ProjectWizard({ companyId, customers, users, costCenters, suppliers, onCreated }: WizardProps) {
  const [step, setStep] = useState(0)
  const [form, setForm] = useState(EMPTY)
  const [files, setFiles] = useState<File[]>([])
  const [setupRunId, setSetupRunId] = useState<string | null>(null)
  const set = (patch: Partial<typeof EMPTY>) => setForm((prev) => ({ ...prev, ...patch }))

  const datesInvalid = Boolean(form.plannedStart && form.plannedEnd && form.plannedEnd < form.plannedStart)
  const contractEnabled = Boolean(form.contractNumber.trim() || form.contractSupplierId || form.contractValue.trim())
  const contractValueCents = cents(form.contractValue)
  const advanceCents = cents(form.advanceAmount)
  const advanceConfigured = isPositiveMoney(form.advanceAmount)
  const contractInvalid = contractEnabled && (!form.contractNumber.trim() || !form.contractSupplierId || !isPositiveMoney(form.contractValue) || (advanceCents !== null && contractValueCents !== null && advanceCents > contractValueCents) || (advanceConfigured && !form.advanceDueDate) || (form.contractEndDate && form.contractEndDate < form.contractStartDate) || !/^(0|[1-9]\d?|100)(\.\d+)?$/.test(form.retentionPercentage) || (form.paymentTermsType !== 'LUMP_SUM' && (!/^[1-9]\d*$/.test(form.regularMonths) || !/^(?:[1-9]|[12]\d|3[01])$/.test(form.dueDay))))
  const canContinue = useMemo(() => {
    if (step === 0) return form.name.trim().length > 0
    if (step === 2) return !datesInvalid
    if (step === 6) return !contractInvalid
    return true
  }, [step, form.name, datesInvalid, contractInvalid])

  const create = useMutation({
    mutationFn: async (activate: boolean) => {
      const payload = {
        project: { companyId, name: form.name.trim(), code: form.code.trim() || undefined, customerId: form.customerId || undefined, currencyCode: form.currencyCode || undefined, description: form.description.trim() || undefined, addressLine1: form.addressLine1.trim() || undefined, addressLine2: form.addressLine2.trim() || undefined, city: form.city.trim() || undefined, stateDepartment: form.stateDepartment.trim() || undefined, country: form.country.trim() || undefined, locationReference: form.locationReference.trim() || undefined, plannedStart: form.plannedStart || undefined, plannedEnd: form.plannedEnd || undefined, costCenterId: form.costCenterId || undefined, managerUserId: form.managerUserId || undefined },
        wbs: { code: form.wbsCode.trim() || undefined, name: form.wbsName.trim() || undefined },
        baselineAmount: isPositiveMoney(form.baselineAmount) ? form.baselineAmount : undefined,
        contract: contractEnabled ? { supplierId: form.contractSupplierId, contractNumber: form.contractNumber.trim(), contractCategory: form.contractCategory, value: form.contractValue, startDate: form.contractStartDate || form.plannedStart || businessTodayIso(), endDate: form.contractEndDate || undefined, advanceAmount: advanceConfigured ? form.advanceAmount : undefined, advanceDueDate: advanceConfigured ? form.advanceDueDate : undefined, retentionPercentage: form.retentionPercentage, paymentTermsType: form.paymentTermsType as 'LUMP_SUM' | 'MONTHLY' | 'CUSTOM', regularMonths: form.paymentTermsType === 'LUMP_SUM' ? undefined : Number(form.regularMonths), dueDay: form.paymentTermsType === 'LUMP_SUM' ? undefined : Number(form.dueDay) } : undefined,
        activate,
      }
      const run = setupRunId ? await projectService.getSetupRun(setupRunId) : await projectService.createSetupRun(payload, crypto.randomUUID())
      setSetupRunId(run.id)
      const alreadyStaged = await documentService.listEvidence(companyId, 'PROJECT_SETUP_STAGED', run.id)
      const stagedFiles = new Set(alreadyStaged.map((evidence) => `${evidence.originalFilename}:${evidence.sizeBytes}`))
      await Promise.all(
        files
          .filter((file) => !stagedFiles.has(`${file.name}:${file.size}`))
          .map((file) => documentService.uploadEvidence(companyId, file, 'OTHER', 'PROJECT_SETUP_STAGED', run.id)),
      )
      const completed = await projectService.executeSetupRun(run.id)
      if (!completed.projectId) throw new Error('La configuración no devolvió un proyecto creado.')
      return projectService.get(completed.projectId)
    },
    onSuccess: onCreated,
  })

  const managerName = users.find((u) => u.id === form.managerUserId)?.fullName ?? 'Sin asignar'
  const customerName = customers.find((c) => c.id === form.customerId)?.legalName ?? 'Sin cliente'
  const contractorName = suppliers.find((s) => s.id === form.contractSupplierId)?.legalName ?? 'Sin contrato inicial'
  const wbsIncomplete = Boolean(form.wbsCode.trim()) !== Boolean(form.wbsName.trim())
  const canSaveDraft = Boolean(form.name.trim()) && !datesInvalid && !wbsIncomplete && !contractInvalid && !create.isPending

  return (
    <div className="nx-wizard">
      <ol className="nx-wizard__steps">
        {STEPS.map((label, index) => (
          <li key={label} className={`nx-wizard__step${index === step ? ' nx-wizard__step--active' : ''}${index < step ? ' nx-wizard__step--done' : ''}`} aria-current={index === step ? 'step' : undefined}>
            <span className="nx-wizard__step-index">{index + 1}</span>{label}
          </li>
        ))}
      </ol>

      <div className="nx-wizard__body">
        {step === 0 ? <>
          <Input label="Nombre del proyecto" value={form.name} onChange={(e) => set({ name: e.target.value })} required />
          <Input label="Código (opcional)" value={form.code} onChange={(e) => set({ code: e.target.value })} />
          <Select label="Cliente" value={form.customerId} onChange={(e) => set({ customerId: e.target.value })}>
            <option value="">Sin cliente asignado todavía</option>
            {customers.map((c) => <option key={c.id} value={c.id}>{c.legalName}</option>)}
          </Select>
          <Select label="Moneda" value={form.currencyCode} onChange={(e) => set({ currencyCode: e.target.value })}>
            <option value="HNL">HNL — Lempira hondureño</option><option value="USD">USD — Dólar estadounidense</option>
          </Select>
          <Textarea label="Descripción" value={form.description} onChange={(e) => set({ description: e.target.value })} />
        </> : null}

        {step === 1 ? <>
          <Input label="Dirección" value={form.addressLine1} onChange={(e) => set({ addressLine1: e.target.value })} />
          <Input label="Referencia adicional" value={form.addressLine2} onChange={(e) => set({ addressLine2: e.target.value })} />
          <Input label="Ciudad" value={form.city} onChange={(e) => set({ city: e.target.value })} />
          <Input label="Departamento / Estado" value={form.stateDepartment} onChange={(e) => set({ stateDepartment: e.target.value })} />
          <Input label="País (ISO-2)" value={form.country} maxLength={2} onChange={(e) => set({ country: e.target.value.toUpperCase() })} />
          <Textarea label="Cómo llegar / referencia" value={form.locationReference} onChange={(e) => set({ locationReference: e.target.value })} />
        </> : null}

        {step === 2 ? <>
          <Input label="Inicio previsto" type="date" value={form.plannedStart} onChange={(e) => set({ plannedStart: e.target.value, contractStartDate: form.contractStartDate === EMPTY.contractStartDate ? e.target.value : form.contractStartDate })} />
          <Input label="Final previsto" type="date" value={form.plannedEnd} onChange={(e) => set({ plannedEnd: e.target.value })} />
          {datesInvalid ? <p className="nx-field__error">La fecha final no puede ser anterior al inicio.</p> : null}
          <Select label="Centro de costo" value={form.costCenterId} onChange={(e) => set({ costCenterId: e.target.value })}>
            <option value="">Sin centro de costo</option>{costCenters.map((cc) => <option key={cc.id} value={cc.id}>{cc.code} · {cc.name}</option>)}
          </Select>
        </> : null}

        {step === 3 ? <Select label="Responsable del proyecto" value={form.managerUserId} onChange={(e) => set({ managerUserId: e.target.value })}>
          <option value="">Sin responsable asignado</option>{users.map((u) => <option key={u.id} value={u.id}>{u.fullName}</option>)}
        </Select> : null}

        {step === 4 ? <>
          <p className="nx-field__hint">Opcional. Si defines ambos campos, se crea una WBS raíz real junto con el proyecto.</p>
          <Input label="Código WBS" value={form.wbsCode} onChange={(e) => set({ wbsCode: e.target.value })} placeholder="Ej. 1.0" />
          <Input label="Nombre WBS" value={form.wbsName} onChange={(e) => set({ wbsName: e.target.value })} placeholder="Ej. Obra principal" />
          {Boolean(form.wbsCode) !== Boolean(form.wbsName) ? <p className="nx-field__error">Completa código y nombre WBS o deja ambos vacíos.</p> : null}
        </> : null}

        {step === 5 ? <>
          <p className="nx-field__hint">Opcional. Si ingresas un monto mayor que cero, el sistema crea el presupuesto BASELINE real. Sin monto, el proyecto queda “Sin configurar”, no con disponible negativo.</p>
          <Input label={`Presupuesto BASELINE (${form.currencyCode})`} inputMode="decimal" value={form.baselineAmount} onChange={(e) => set({ baselineAmount: e.target.value })} />
        </> : null}

        {step === 6 ? <>
          <p className="nx-field__hint">Opcional. Completa contrato, contratista y valor para dejar el contrato de ejecución y su plan listos desde el alta.</p>
          <Select label="Contratista / proveedor" value={form.contractSupplierId} onChange={(e) => set({ contractSupplierId: e.target.value })}>
            <option value="">Sin contrato inicial</option>
            {suppliers.filter((s) => s.status === 'ACTIVE').map((s) => <option key={s.id} value={s.id}>{s.legalName}</option>)}
          </Select>
          <Input label="Número de contrato" value={form.contractNumber} onChange={(e) => set({ contractNumber: e.target.value })} />
          <Select label="Categoría" value={form.contractCategory} onChange={(e) => set({ contractCategory: e.target.value })}>
            <option value="LABOR">Mano de obra</option><option value="SUBCONTRACT">Subcontrato</option><option value="MATERIALS">Materiales</option><option value="EQUIPMENT">Equipo</option><option value="PROFESSIONAL_SERVICES">Servicios profesionales</option><option value="OTHER">Otro</option>
          </Select>
          <Input label={`Valor contractual (${form.currencyCode})`} inputMode="decimal" value={form.contractValue} onChange={(e) => set({ contractValue: e.target.value })} />
          <Input label="Inicio del contrato" type="date" value={form.contractStartDate} onChange={(e) => set({ contractStartDate: e.target.value })} />
          <Input label="Fin del contrato (opcional)" type="date" value={form.contractEndDate} onChange={(e) => set({ contractEndDate: e.target.value })} />
          <Input label={`Anticipo pactado (${form.currencyCode}, opcional)`} inputMode="decimal" value={form.advanceAmount} onChange={(e) => set({ advanceAmount: e.target.value })} />
          {advanceConfigured ? <Input label="Vencimiento del anticipo" type="date" value={form.advanceDueDate} onChange={(e) => set({ advanceDueDate: e.target.value })} required /> : null}
          <Input label="Retención %" type="number" min={0} max={100} value={form.retentionPercentage} onChange={(e) => set({ retentionPercentage: e.target.value })} />
          <Select label="Esquema de pago" value={form.paymentTermsType} onChange={(e) => set({ paymentTermsType: e.target.value })}>
            <option value="MONTHLY">Cuotas mensuales</option><option value="CUSTOM">Cuotas personalizadas (plan inicial mensual editable)</option><option value="LUMP_SUM">Pago único / suma alzada</option>
          </Select>
          {form.paymentTermsType !== 'LUMP_SUM' ? <>
            <Input label="Número de mensualidades" type="number" min={1} value={form.regularMonths} onChange={(e) => set({ regularMonths: e.target.value })} />
            <Input label="Día de vencimiento mensual" type="number" min={1} max={31} value={form.dueDay} onChange={(e) => set({ dueDay: e.target.value })} />
          </> : null}
          {contractInvalid ? <p className="nx-field__error">Para crear contrato inicial completa contratista/proveedor, número y valor.</p> : null}
        </> : null}

        {step === 7 ? <>
          <p className="nx-field__hint">Opcional. Los archivos se cargan como Evidence privado y Documento del proyecto después de crear la ficha.</p>
          <Input label="Documentos iniciales" type="file" multiple accept="application/pdf,image/jpeg,image/png,image/webp,image/heic,image/heif" onChange={(e) => setFiles(Array.from(e.target.files ?? []))} />
          {files.length ? <p className="nx-field__hint">{files.length} archivo(s) seleccionado(s): {files.map((file) => file.name).join(', ')}</p> : null}
        </> : null}

        {step === 8 ? <dl className="nx-voucher-preview">
          <div><dt>Nombre</dt><dd>{form.name || '—'}</dd></div>
          <div><dt>Código</dt><dd>{form.code || '—'}</dd></div>
          <div><dt>Cliente</dt><dd>{customerName}</dd></div>
          <div><dt>Moneda</dt><dd>{form.currencyCode}</dd></div>
          <div><dt>Ubicación</dt><dd>{[form.addressLine1, form.city, form.stateDepartment, form.country].filter(Boolean).join(', ') || '—'}</dd></div>
          <div><dt>Plan</dt><dd>{form.plannedStart && form.plannedEnd ? `${form.plannedStart} → ${form.plannedEnd}` : '—'}</dd></div>
          <div><dt>Responsable</dt><dd>{managerName}</dd></div>
          <div><dt>WBS inicial</dt><dd>{form.wbsCode && form.wbsName ? `${form.wbsCode} · ${form.wbsName}` : 'No configurada'}</dd></div>
          <div><dt>Presupuesto BASELINE</dt><dd>{isPositiveMoney(form.baselineAmount) ? formatMoney(form.baselineAmount, form.currencyCode) : 'Sin configurar'}</dd></div>
          <div><dt>Contrato de ejecución</dt><dd>{contractEnabled ? `${form.contractNumber} · ${contractorName} · ${formatMoney(form.contractValue || '0', form.currencyCode)}` : 'No configurado'}</dd></div>
          <div><dt>Documentos iniciales</dt><dd>{files.length ? `${files.length} archivo(s)` : 'Ninguno'}</dd></div>
        </dl> : null}
      </div>

      {create.isError ? (
        <p className="nx-field__error" role="alert">
          {(create.error as Error).message} No hay proyecto, WBS, BASELINE, contrato, plan ni documento final parcialmente creados. Los archivos ya subidos permanecen identificados como «en preparación» y puedes continuar esta configuración sin duplicarla.
        </p>
      ) : null}

      <div className="nx-wizard__actions">
        <Button variant="ghost" onClick={() => setStep((s) => Math.max(0, s - 1))} disabled={step === 0 || create.isPending}>Atrás</Button>
        {step < STEPS.length - 1 ? (
          <div className="nx-wizard__finish">
            {step > 0 ? (
              <Button
                variant="secondary"
                loading={create.isPending && create.variables === false}
                disabled={!canSaveDraft}
                onClick={() => create.mutate(false)}
              >
                Crear como borrador
              </Button>
            ) : null}
            <Button onClick={() => setStep((s) => s + 1)} disabled={!canContinue || (step === 4 && Boolean(form.wbsCode) !== Boolean(form.wbsName)) || create.isPending}>Continuar</Button>
          </div>
        ) : (
          <div className="nx-wizard__finish">
            <Button variant="secondary" loading={create.isPending && create.variables === false} disabled={!canSaveDraft} onClick={() => create.mutate(false)}>{setupRunId ? 'Continuar configuración como borrador' : 'Crear como borrador'}</Button>
            <Button loading={create.isPending && create.variables === true} disabled={!canSaveDraft} onClick={() => create.mutate(true)}>{setupRunId ? 'Continuar configuración y activar' : 'Crear configuración y activar'}</Button>
          </div>
        )}
      </div>
    </div>
  )
}
