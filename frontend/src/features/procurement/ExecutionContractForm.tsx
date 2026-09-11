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
  defaultCurrency,
  onCreated,
  onCancel,
}: {
  lockedProjectId?: string
  defaultCurrency?: string
  onCreated: (contract: SupplierContract) => void
  onCancel?: () => void
}) {
  const { activeCompanyId, activeCompany } = useActiveCompany()
  const authoritativeCurrency = defaultCurrency ?? activeCompany?.functionalCurrencyCode ?? ''
  const currencyMismatch = Boolean(
    defaultCurrency &&
      activeCompany?.functionalCurrencyCode &&
      defaultCurrency !== activeCompany.functionalCurrencyCode,
  )
  const queryClient = useQueryClient()
  const [form, setForm] = useState({
    supplierId: '',
    projectId: lockedProjectId ?? '',
    contractNumber: '',
    contractCategory: 'LABOR' as SupplierContractCategory,
    value: '',
    startDate: '',
    endDate: '',
    advanceMode: 'AMOUNT' as 'AMOUNT' | 'PERCENT',
    advanceAmount: '',
    advancePercentage: '',
    advanceDueDate: '',
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
    const rank = (supplier: (typeof rawSuppliers)[number]) => {
      if (supplier.status === 'BLOCKED' || supplier.status === 'ARCHIVED') return 3
      if (supplier.status === 'INACTIVE') return 2
      if (supplier.partyRole === 'CONTRACTOR' || supplier.partyRole === 'BOTH') return 0
      return 1
    }
    return rank(a) - rank(b) || a.legalName.localeCompare(b.legalName)
  })
  const projects = projectsQuery.data ?? []

  const datesInvalid = Boolean(form.endDate && form.startDate && form.endDate < form.startDate)

  const createMutation = useMutation({
    mutationFn: () => {
      if (!activeCompanyId || !authoritativeCurrency || currencyMismatch) {
        throw new Error(
          currencyMismatch
            ? 'La moneda del proyecto/contrato no coincide con la moneda funcional de la compañía activa.'
            : 'Selecciona una compañía con moneda funcional antes de crear el contrato.',
        )
      }
      return procurementService.createContract({
        companyId: activeCompanyId,
        supplierId: form.supplierId,
        projectId: lockedProjectId ?? (form.projectId || undefined),
        contractNumber: form.contractNumber.trim(),
        contractCategory: form.contractCategory,
        value: form.value,
        currencyCode: authoritativeCurrency,
        startDate: form.startDate,
        endDate: form.endDate || undefined,
        // El anticipo se guarda como MONTO exacto (§7/§8); el % es informativo.
        advanceAmount:
          form.advanceMode === 'AMOUNT' && form.advanceAmount ? form.advanceAmount : undefined,
        advancePercentage:
          form.advanceMode === 'PERCENT' && form.advancePercentage
            ? form.advancePercentage
            : undefined,
        advanceDueDate: form.advanceDueDate || undefined,
        retentionPercentage: form.retentionPercentage || undefined,
        scopeDescription: form.scopeDescription.trim() || undefined,
        paymentTermsType: form.paymentTermsType,
      })
    },
    onSuccess: (contract) => {
      queryClient.invalidateQueries({ queryKey: ['procurement', 'contracts', activeCompanyId] })
      queryClient.invalidateQueries({ queryKey: ['project', lockedProjectId] })
      queryClient.invalidateQueries({
        queryKey: ['project', lockedProjectId, 'financial-summary'],
      })
      onCreated(contract)
    },
  })

  const canSubmit = useMemo(
    () =>
      Boolean(activeCompanyId) &&
      Boolean(authoritativeCurrency) &&
      !currencyMismatch &&
      Boolean(form.supplierId) &&
      Boolean(form.contractNumber.trim()) &&
      Boolean(form.value) &&
      Number(form.value) > 0 &&
      Boolean(form.startDate) &&
      !datesInvalid,
    [
      activeCompanyId,
      authoritativeCurrency,
      currencyMismatch,
      form.supplierId,
      form.contractNumber,
      form.value,
      form.startDate,
      datesInvalid,
    ],
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
        onChange={(event) => setForm({ ...form, supplierId: event.target.value })}
        required
      >
        <option value="" disabled>
          Selecciona un contratista
        </option>
        {suppliers.map((supplier) => (
          <option
            key={supplier.id}
            value={supplier.id}
            disabled={supplier.status === 'BLOCKED' || supplier.status === 'ARCHIVED'}
          >
            {supplier.legalName}
            {supplier.status === 'BLOCKED'
              ? ' — bloqueado'
              : supplier.status === 'ARCHIVED'
                ? ' — archivado'
                : supplier.status === 'INACTIVE'
                  ? ' — inactivo'
                  : ''}
          </option>
        ))}
      </Select>

      {lockedProjectId ? null : (
        <Select
          label="Proyecto (opcional)"
          value={form.projectId}
          onChange={(event) => setForm({ ...form, projectId: event.target.value })}
        >
          <option value="">General (sin proyecto)</option>
          {projects.map((project) => (
            <option key={project.id} value={project.id}>
              {project.name}
            </option>
          ))}
        </Select>
      )}

      <Input
        label="Número de contrato"
        value={form.contractNumber}
        onChange={(event) => setForm({ ...form, contractNumber: event.target.value })}
        required
      />
      <Select
        label="Categoría del costo"
        value={form.contractCategory}
        onChange={(event) =>
          setForm({ ...form, contractCategory: event.target.value as SupplierContractCategory })
        }
        required
      >
        {(Object.keys(SUPPLIER_CONTRACT_CATEGORY_LABELS) as SupplierContractCategory[]).map(
          (category) => (
            <option key={category} value={category}>
              {SUPPLIER_CONTRACT_CATEGORY_LABELS[category]}
            </option>
          ),
        )}
      </Select>
      <Input
        label={`Valor contractual${authoritativeCurrency ? ` (${authoritativeCurrency})` : ''}`}
        inputMode="decimal"
        value={form.value}
        onChange={(event) => setForm({ ...form, value: event.target.value })}
        required
      />
      <Input
        label="Moneda"
        value={authoritativeCurrency}
        readOnly
        placeholder="Configura la moneda funcional de la compañía"
      />
      {currencyMismatch ? (
        <p className="nx-field__error" role="alert">
          La moneda heredada del proyecto no coincide con la moneda funcional de la compañía
          activa. Corrige el contexto antes de crear el contrato.
        </p>
      ) : null}
      {!authoritativeCurrency ? (
        <p className="nx-field__error" role="alert">
          La compañía activa no tiene moneda funcional configurada.
        </p>
      ) : null}
      <Input
        label="Fecha de inicio"
        type="date"
        value={form.startDate}
        onChange={(event) => setForm({ ...form, startDate: event.target.value })}
        required
      />
      <Input
        label="Fecha de fin (opcional)"
        type="date"
        value={form.endDate}
        onChange={(event) => setForm({ ...form, endDate: event.target.value })}
      />
      <Select
        label="Anticipo pactado — modo"
        value={form.advanceMode}
        onChange={(event) =>
          setForm({ ...form, advanceMode: event.target.value as 'AMOUNT' | 'PERCENT' })
        }
      >
        <option value="AMOUNT">Monto</option>
        <option value="PERCENT">Porcentaje</option>
      </Select>
      {form.advanceMode === 'AMOUNT' ? (
        <Input
          label="Anticipo pactado (monto)"
          inputMode="decimal"
          value={form.advanceAmount}
          onChange={(event) => setForm({ ...form, advanceAmount: event.target.value })}
        />
      ) : (
        <Input
          label="Anticipo pactado (%)"
          inputMode="decimal"
          value={form.advancePercentage}
          onChange={(event) => setForm({ ...form, advancePercentage: event.target.value })}
        />
      )}
      {form.advanceMode === 'AMOUNT' && form.advanceAmount && Number(form.value) > 0 ? (
        <p className="nx-field__hint">
          Equivale aproximadamente a{' '}
          {((Number(form.advanceAmount) / Number(form.value)) * 100).toFixed(4)}% — el monto exacto
          guardado es {form.advanceAmount}.
        </p>
      ) : null}
      <Input
        label="Vencimiento del anticipo (opcional)"
        type="date"
        value={form.advanceDueDate}
        onChange={(event) => setForm({ ...form, advanceDueDate: event.target.value })}
      />
      <Input
        label="Retención %"
        inputMode="decimal"
        value={form.retentionPercentage}
        onChange={(event) => setForm({ ...form, retentionPercentage: event.target.value })}
      />
      <Select
        label="Esquema de pago"
        value={form.paymentTermsType}
        onChange={(event) =>
          setForm({
            ...form,
            paymentTermsType: event.target.value as SupplierContractPaymentTermsType,
          })
        }
      >
        {(
          Object.keys(SUPPLIER_CONTRACT_PAYMENT_TERMS_LABELS) as SupplierContractPaymentTermsType[]
        ).map((termsType) => (
          <option key={termsType} value={termsType}>
            {SUPPLIER_CONTRACT_PAYMENT_TERMS_LABELS[termsType]}
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
        onChange={(event) => setForm({ ...form, scopeDescription: event.target.value })}
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
