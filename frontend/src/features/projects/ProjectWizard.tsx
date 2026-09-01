import { useMemo, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Button, Input, Select, Textarea } from '../../design-system'
import { projectService } from '../../services/projectService'
import type { Project } from '../../types/project'
import { formatMoney } from '../../utils/currency'
import './ProjectWizard.css'

interface WizardProps {
  companyId: string
  customers: Array<{ id: string; legalName: string }>
  users: Array<{ id: string; fullName: string }>
  costCenters: Array<{ id: string; code: string; name: string }>
  onCreated: (project: Project) => void
}

const STEPS = [
  'Datos generales',
  'Ubicación de la obra',
  'Alcance y fechas',
  'Equipo',
  'Revisión',
] as const

const EMPTY = {
  name: '',
  code: '',
  customerId: '',
  currencyCode: 'HNL',
  description: '',
  addressLine1: '',
  addressLine2: '',
  city: '',
  stateDepartment: '',
  country: 'HN',
  locationReference: '',
  plannedStart: '',
  plannedEnd: '',
  costCenterId: '',
  managerUserId: '',
}

/**
 * Alta guiada de proyecto (ORDEN MAESTRA §11). Un wizard con pasos reales
 * —datos / ubicación / alcance / equipo / revisión— que termina en
 * "crear como borrador" (PLANNING) o "crear y activar" (ACTIVE). No es el
 * mismo formulario plano envuelto: cada paso valida lo suyo y la ubicación
 * (§17) viaja de verdad al backend.
 */
export function ProjectWizard({ companyId, customers, users, costCenters, onCreated }: WizardProps) {
  const [step, setStep] = useState(0)
  const [form, setForm] = useState(EMPTY)
  const set = (patch: Partial<typeof EMPTY>) => setForm((prev) => ({ ...prev, ...patch }))

  const datesInvalid = Boolean(
    form.plannedStart && form.plannedEnd && form.plannedEnd < form.plannedStart,
  )
  const canContinue = useMemo(() => {
    if (step === 0) return form.name.trim().length > 0
    if (step === 2) return !datesInvalid
    return true
  }, [step, form.name, datesInvalid])

  const create = useMutation({
    mutationFn: (activate: boolean) =>
      projectService
        .create({
          companyId,
          name: form.name.trim(),
          code: form.code.trim() || undefined,
          customerId: form.customerId || undefined,
          currencyCode: form.currencyCode || undefined,
          description: form.description.trim() || undefined,
          addressLine1: form.addressLine1.trim() || undefined,
          addressLine2: form.addressLine2.trim() || undefined,
          city: form.city.trim() || undefined,
          stateDepartment: form.stateDepartment.trim() || undefined,
          country: form.country.trim() || undefined,
          locationReference: form.locationReference.trim() || undefined,
          plannedStart: form.plannedStart || undefined,
          plannedEnd: form.plannedEnd || undefined,
          costCenterId: form.costCenterId || undefined,
          managerUserId: form.managerUserId || undefined,
        })
        .then(async (project) => {
          if (activate) {
            return projectService.transitionStatus(project.id, 'ACTIVE')
          }
          return project
        }),
    onSuccess: onCreated,
  })

  const managerName = users.find((u) => u.id === form.managerUserId)?.fullName ?? 'Sin asignar'
  const customerName =
    customers.find((c) => c.id === form.customerId)?.legalName ?? 'Sin cliente'

  return (
    <div className="nx-wizard">
      <ol className="nx-wizard__steps">
        {STEPS.map((label, index) => (
          <li
            key={label}
            className={`nx-wizard__step${index === step ? ' nx-wizard__step--active' : ''}${
              index < step ? ' nx-wizard__step--done' : ''
            }`}
            aria-current={index === step ? 'step' : undefined}
          >
            <span className="nx-wizard__step-index">{index + 1}</span>
            {label}
          </li>
        ))}
      </ol>

      <div className="nx-wizard__body">
        {step === 0 ? (
          <>
            <Input label="Nombre del proyecto" value={form.name} onChange={(e) => set({ name: e.target.value })} required />
            <Input label="Código (opcional)" value={form.code} onChange={(e) => set({ code: e.target.value })} />
            <Select label="Cliente" value={form.customerId} onChange={(e) => set({ customerId: e.target.value })}>
              <option value="">Sin cliente asignado todavía</option>
              {customers.map((c) => (
                <option key={c.id} value={c.id}>{c.legalName}</option>
              ))}
            </Select>
            <Select label="Moneda" value={form.currencyCode} onChange={(e) => set({ currencyCode: e.target.value })}>
              <option value="HNL">HNL — Lempira hondureño</option>
              <option value="USD">USD — Dólar estadounidense</option>
            </Select>
            <Textarea label="Descripción" value={form.description} onChange={(e) => set({ description: e.target.value })} />
          </>
        ) : null}

        {step === 1 ? (
          <>
            <Input label="Dirección" value={form.addressLine1} onChange={(e) => set({ addressLine1: e.target.value })} />
            <Input label="Referencia adicional" value={form.addressLine2} onChange={(e) => set({ addressLine2: e.target.value })} />
            <Input label="Ciudad" value={form.city} onChange={(e) => set({ city: e.target.value })} />
            <Input label="Departamento / Estado" value={form.stateDepartment} onChange={(e) => set({ stateDepartment: e.target.value })} />
            <Input label="País (ISO-2)" value={form.country} maxLength={2} onChange={(e) => set({ country: e.target.value.toUpperCase() })} />
            <Textarea label="Cómo llegar / referencia" value={form.locationReference} onChange={(e) => set({ locationReference: e.target.value })} />
          </>
        ) : null}

        {step === 2 ? (
          <>
            <Input label="Inicio previsto" type="date" value={form.plannedStart} onChange={(e) => set({ plannedStart: e.target.value })} />
            <Input label="Final previsto" type="date" value={form.plannedEnd} onChange={(e) => set({ plannedEnd: e.target.value })} />
            {datesInvalid ? (
              <p className="nx-field__error">La fecha final no puede ser anterior al inicio.</p>
            ) : null}
            <Select label="Centro de costo" value={form.costCenterId} onChange={(e) => set({ costCenterId: e.target.value })}>
              <option value="">Sin centro de costo</option>
              {costCenters.map((cc) => (
                <option key={cc.id} value={cc.id}>{cc.code} · {cc.name}</option>
              ))}
            </Select>
          </>
        ) : null}

        {step === 3 ? (
          <Select label="Responsable del proyecto" value={form.managerUserId} onChange={(e) => set({ managerUserId: e.target.value })}>
            <option value="">Sin responsable asignado</option>
            {users.map((u) => (
              <option key={u.id} value={u.id}>{u.fullName}</option>
            ))}
          </Select>
        ) : null}

        {step === 4 ? (
          <dl className="nx-voucher-preview">
            <div><dt>Nombre</dt><dd>{form.name || '—'}</dd></div>
            <div><dt>Código</dt><dd>{form.code || '—'}</dd></div>
            <div><dt>Cliente</dt><dd>{customerName}</dd></div>
            <div><dt>Moneda</dt><dd>{form.currencyCode}</dd></div>
            <div><dt>Ubicación</dt><dd>{[form.addressLine1, form.city, form.stateDepartment, form.country].filter(Boolean).join(', ') || '—'}</dd></div>
            <div><dt>Plan</dt><dd>{form.plannedStart && form.plannedEnd ? `${form.plannedStart} → ${form.plannedEnd}` : '—'}</dd></div>
            <div><dt>Responsable</dt><dd>{managerName}</dd></div>
            <div><dt>Presupuesto</dt><dd>{formatMoney(0, form.currencyCode)} · se define después de crear</dd></div>
          </dl>
        ) : null}
      </div>

      {create.isError ? (
        <p className="nx-field__error" role="alert">{(create.error as Error).message}</p>
      ) : null}

      <div className="nx-wizard__actions">
        <Button variant="ghost" onClick={() => setStep((s) => Math.max(0, s - 1))} disabled={step === 0 || create.isPending}>
          Atrás
        </Button>
        {step < STEPS.length - 1 ? (
          <Button onClick={() => setStep((s) => s + 1)} disabled={!canContinue}>
            Continuar
          </Button>
        ) : (
          <div className="nx-wizard__finish">
            <Button
              variant="secondary"
              loading={create.isPending && create.variables === false}
              disabled={!form.name.trim() || datesInvalid || create.isPending}
              onClick={() => create.mutate(false)}
            >
              Crear como borrador
            </Button>
            <Button
              loading={create.isPending && create.variables === true}
              disabled={!form.name.trim() || datesInvalid || create.isPending}
              onClick={() => create.mutate(true)}
            >
              Crear y activar
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
