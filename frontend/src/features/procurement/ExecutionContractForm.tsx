import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button, Input, Select, Textarea } from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { procurementService } from '../../services/procurementService'
import { projectService } from '../../services/projectService'
import {
  SUPPLIER_CONTRACT_CATEGORY_LABELS,
  SUPPLIER_CONTRACT_PAYMENT_TERMS_LABELS,
  type SupplierContract,
  type SupplierContractCategory,
  type SupplierContractPaymentTermsType,
} from '../../types/procurement'

/**
 * Formulario canónico de alta de contrato de ejecución (ORDEN MAESTRA §4/§5).
 * Se abre desde Abastecimiento → Contratos, desde el Project Cockpit y desde el
 * Project Wizard. Cuando `lockedProjectId` está presente el proyecto se hereda y
 * queda bloqueado — nunca se vuelve a pedir.
 */
export function ExecutionContractForm({
  lockedProjectId,
  defaultCurrency = 'HNL',
  onCreated,
  onCancel,
}: {
  lockedProjectId?: string
  defaultCurrency?: string
  onCreated: (contract: SupplierContract) => void
  onCancel?: () => void
}) {
  const { activeCompanyId } = useActiveCompany()
  const queryClient = useQueryClient()
  const [form, setForm] = useState({
    supplierId: '',
    projectId: lockedProjectId ?? '',
    contractNumber: '',
    contractCategory: 'LABOR' as SupplierContractCategory,
    value: '',
    currencyCode: defaultCurrency,
    startDate: '',
    endDate: '',
    advancePercentage: '',
    retentionPercentage: '',
    scopeDescription: '',
    paymentTermsType: 'MONTHLY' as SupplierContractPaymentTermsType,
  })

  const suppliersQuery = useQuery({
    queryKey: ['procurement', 'suppliers', activeCompanyId],
    queryFn: () => procurementService.listSuppliers(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })
  const projectsQuery = useQuery({
    queryKey: ['projects', activeCompanyId],
    queryFn: () => projectService.list(activeCompanyId as string),
    enabled: Boolean(activeCompanyId) && !lockedProjectId,
  })
  // §19 — para un contrato de ejecución priorizamos contratistas activos.
  // No se ocultan INACTIVE/BLOCKED/ARCHIVED del todo (un proveedor puro puede
  // firmar un contrato de materiales), pero van al final y desactivados los que
  // no admiten nuevos contratos.
  const rawSuppliers = suppliersQuery.data ?? []
  const suppliers = [...rawSuppliers].sort((a, b) => {
    const rank = (s: (typeof rawSuppliers)[number]) => {
      if (s.status === 'BLOCKED' || s.status === 'ARCHIVED') return 3
      if (s.status === 'INACTIVE') return 2
      if (s.partyRole === 'CONTRACTOR' || s.partyRole === 'BOTH') return 0
      return 1
    }
    return rank(a) - rank(b) || a.legalName.localeCompare(b.legalName)
  })
  const projects = projectsQuery.data ?? []

  const datesInvalid = Boolean(form.endDate && form.startDate && form.endDate < form.startDate)

  const createMutation = useMutation({
    mutationFn: () =>
      procurementService.createContract({
        companyId: activeCompanyId as string,
        supplierId: form.supplierId,
        projectId: lockedProjectId ?? (form.projectId || undefined),
        contractNumber: form.contractNumber.trim(),
        contractCategory: form.contractCategory,
        value: form.value,
        currencyCode: form.currencyCode,
        startDate: form.startDate,
        endDate: form.endDate || undefined,
        advancePercentage: form.advancePercentage || undefined,
        retentionPercentage: form.retentionPercentage || undefined,
        scopeDescription: form.scopeDescription.trim() || undefined,
        paymentTermsType: form.paymentTermsType,
      }),
    onSuccess: (contract) => {
      queryClient.invalidateQueries({ queryKey: ['procurement', 'contracts', activeCompanyId] })
      queryClient.invalidateQueries({ queryKey: ['project', lockedProjectId] })
      queryClient.invalidateQueries({ queryKey: ['project', lockedProjectId, 'financial-summary'] })
      onCreated(contract)
    },
  })

  const canSubmit = useMemo(
    () =>
      Boolean(form.supplierId) &&
      Boolean(form.contractNumber.trim()) &&
      Boolean(form.value) &&
      Number(form.value) > 0 &&
      Boolean(form.startDate) &&
      !datesInvalid,
    [form.supplierId, form.contractNumber, form.value, form.startDate, datesInvalid],
  )

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault()
        if (canSubmit) createMutation.mutate()
      }}
    >
      <Select
        label="Contratista / proveedor"
        value={form.supplierId}
        onChange={(e) => setForm({ ...form, supplierId: e.target.value })}
        required
      >
        <option value="" disabled>
          Selecciona un contratista
        </option>
        {suppliers.map((s) => (
          <option
            key={s.id}
            value={s.id}
            disabled={s.status === 'BLOCKED' || s.status === 'ARCHIVED'}
          >
            {s.legalName}
            {s.status === 'BLOCKED' ? ' — bloqueado' : s.status === 'ARCHIVED' ? ' — archivado' : s.status === 'INACTIVE' ? ' — inactivo' : ''}
          </option>
        ))}
      </Select>

      {lockedProjectId ? null : (
        <Select
          label="Proyecto (opcional)"
          value={form.projectId}
          onChange={(e) => setForm({ ...form, projectId: e.target.value })}
        >
          <option value="">General (sin proyecto)</option>
          {projects.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </Select>
      )}

      <Input
        label="Número de contrato"
        value={form.contractNumber}
        onChange={(e) => setForm({ ...form, contractNumber: e.target.value })}
        required
      />
      <Select
        label="Categoría del costo"
        value={form.contractCategory}
        onChange={(e) => setForm({ ...form, contractCategory: e.target.value as SupplierContractCategory })}
        required
      >
        {(Object.keys(SUPPLIER_CONTRACT_CATEGORY_LABELS) as SupplierContractCategory[]).map((c) => (
          <option key={c} value={c}>
            {SUPPLIER_CONTRACT_CATEGORY_LABELS[c]}
          </option>
        ))}
      </Select>
      <Input
        label="Valor contractual"
        inputMode="decimal"
        value={form.value}
        onChange={(e) => setForm({ ...form, value: e.target.value })}
        required
      />
      <Select
        label="Moneda"
        value={form.currencyCode}
        onChange={(e) => setForm({ ...form, currencyCode: e.target.value })}
      >
        <option value="HNL">HNL — Lempira hondureño</option>
        <option value="USD">USD — Dólar estadounidense</option>
      </Select>
      <Input
        label="Fecha de inicio"
        type="date"
        value={form.startDate}
        onChange={(e) => setForm({ ...form, startDate: e.target.value })}
        required
      />
      <Input
        label="Fecha de fin (opcional)"
        type="date"
        value={form.endDate}
        onChange={(e) => setForm({ ...form, endDate: e.target.value })}
      />
      <Input
        label="Anticipo %"
        inputMode="decimal"
        value={form.advancePercentage}
        onChange={(e) => setForm({ ...form, advancePercentage: e.target.value })}
      />
      <Input
        label="Retención %"
        inputMode="decimal"
        value={form.retentionPercentage}
        onChange={(e) => setForm({ ...form, retentionPercentage: e.target.value })}
      />
      <Select
        label="Esquema de pago"
        value={form.paymentTermsType}
        onChange={(e) =>
          setForm({ ...form, paymentTermsType: e.target.value as SupplierContractPaymentTermsType })
        }
      >
        {(
          Object.keys(SUPPLIER_CONTRACT_PAYMENT_TERMS_LABELS) as SupplierContractPaymentTermsType[]
        ).map((t) => (
          <option key={t} value={t}>
            {SUPPLIER_CONTRACT_PAYMENT_TERMS_LABELS[t]}
          </option>
        ))}
      </Select>
      {form.paymentTermsType !== 'LUMP_SUM' ? (
        <p className="nx-field__hint">
          Este esquema exige un plan de pagos antes de poder pagar cuotas. Podrás crearlo desde la
          ficha del contrato.
        </p>
      ) : null}
      <Textarea
        label="Descripción / alcance"
        value={form.scopeDescription}
        onChange={(e) => setForm({ ...form, scopeDescription: e.target.value })}
      />

      {datesInvalid ? (
        <p className="nx-field__error" role="alert">
          La fecha de fin no puede ser anterior a la de inicio.
        </p>
      ) : null}
      {suppliers.length === 0 ? (
        <p className="nx-field__error" role="alert">
          Necesitas al menos un contratista registrado primero.
        </p>
      ) : null}

      <div className="nx-treasury__actions">
        <Button type="submit" loading={createMutation.isPending} disabled={!canSubmit}>
          Guardar contrato
        </Button>
        {onCancel ? (
          <Button type="button" variant="ghost" onClick={onCancel}>
            Cancelar
          </Button>
        ) : null}
      </div>
      {createMutation.isError ? (
        <p className="nx-field__error" role="alert">
          {(createMutation.error as Error).message}
        </p>
      ) : null}
    </form>
  )
}
