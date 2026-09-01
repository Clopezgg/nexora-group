import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Badge, Button, Input, Modal, Select, Textarea } from '../../design-system'
import { procurementService } from '../../services/procurementService'
import type { Supplier } from '../../types/procurement'
import {
  SUPPLIER_PARTY_ROLE_LABELS,
  SUPPLIER_STATUS_LABELS,
  supplierStatusLabel,
} from '../../utils/statusLabels'

const STATUS_TONE: Record<string, 'neutral' | 'warning' | 'danger' | 'success'> = {
  ACTIVE: 'success',
  INACTIVE: 'neutral',
  BLOCKED: 'danger',
  ARCHIVED: 'neutral',
}

// Transiciones permitidas por estado (espejo del backend §15).
const NEXT_STATUS: Record<string, string[]> = {
  ACTIVE: ['INACTIVE', 'BLOCKED', 'ARCHIVED'],
  INACTIVE: ['ACTIVE', 'BLOCKED', 'ARCHIVED'],
  BLOCKED: ['ACTIVE', 'INACTIVE', 'ARCHIVED'],
  ARCHIVED: ['ACTIVE'],
}
const SENSITIVE = new Set(['BLOCKED', 'ARCHIVED'])

/**
 * Ficha de Proveedor / Contratista (CORRECTIVA §14/§15/§17/§18). Editar master
 * data y cambiar de estado desde aquí; tras guardar la caché de React Query se
 * actualiza de inmediato — sin recargar.
 */
export function SupplierDrawer({ supplier, onClose }: { supplier: Supplier; onClose: () => void }) {
  const queryClient = useQueryClient()
  const [form, setForm] = useState({
    legalName: supplier.legalName,
    tradeName: supplier.tradeName ?? '',
    taxId: supplier.taxId ?? '',
    contactName: supplier.contactName ?? '',
    email: supplier.email ?? '',
    phone: supplier.phone ?? '',
    addressLine1: supplier.addressLine1 ?? '',
    city: supplier.city ?? '',
    stateDepartment: supplier.stateDepartment ?? '',
    country: supplier.country ?? '',
    partyRole: supplier.partyRole,
  })
  const [statusTarget, setStatusTarget] = useState('')
  const [statusReason, setStatusReason] = useState('')

  const refresh = (updated: Supplier) => {
    queryClient.setQueriesData<Supplier[]>({ queryKey: ['procurement', 'suppliers'] }, (rows) =>
      Array.isArray(rows) ? rows.map((r) => (r.id === updated.id ? updated : r)) : rows,
    )
    queryClient.invalidateQueries({ queryKey: ['procurement', 'suppliers'] })
  }

  const updateMutation = useMutation({
    mutationFn: () =>
      procurementService.updateSupplier(supplier.id, {
        legalName: form.legalName.trim(),
        tradeName: form.tradeName.trim() || null,
        taxId: form.taxId.trim() || null,
        contactName: form.contactName.trim() || null,
        email: form.email.trim() || null,
        phone: form.phone.trim() || null,
        addressLine1: form.addressLine1.trim() || null,
        city: form.city.trim() || null,
        stateDepartment: form.stateDepartment.trim() || null,
        country: form.country.trim() || null,
        partyRole: form.partyRole,
      }),
    onSuccess: (updated) => {
      refresh(updated)
    },
  })

  const statusMutation = useMutation({
    mutationFn: () =>
      procurementService.changeSupplierStatus(supplier.id, statusTarget, statusReason.trim() || undefined),
    onSuccess: (updated) => {
      refresh(updated)
      setStatusTarget('')
      setStatusReason('')
    },
  })

  const statusNeedsReason = SENSITIVE.has(statusTarget) || supplier.status === 'ARCHIVED'

  return (
    <Modal open title={`${form.legalName || 'Proveedor / contratista'}`} onClose={onClose}>
      <p style={{ marginBottom: 12 }}>
        Estado:{' '}
        <Badge tone={STATUS_TONE[supplier.status] ?? 'neutral'}>
          {supplierStatusLabel(supplier.status)}
        </Badge>{' '}
        · {SUPPLIER_PARTY_ROLE_LABELS[supplier.partyRole] ?? supplier.partyRole}
      </p>

      <form
        onSubmit={(event) => {
          event.preventDefault()
          if (form.legalName.trim()) updateMutation.mutate()
        }}
      >
        <p className="nx-field__label">Datos generales</p>
        <Input label="Razón social" value={form.legalName} onChange={(e) => setForm({ ...form, legalName: e.target.value })} required />
        <Input label="Nombre comercial" value={form.tradeName} onChange={(e) => setForm({ ...form, tradeName: e.target.value })} />
        <Input label="RTN / identificación" value={form.taxId} onChange={(e) => setForm({ ...form, taxId: e.target.value })} />
        <Select
          label="Tipo de tercero"
          value={form.partyRole}
          onChange={(e) => setForm({ ...form, partyRole: e.target.value as Supplier['partyRole'] })}
        >
          {(Object.keys(SUPPLIER_PARTY_ROLE_LABELS)).map((r) => (
            <option key={r} value={r}>{SUPPLIER_PARTY_ROLE_LABELS[r]}</option>
          ))}
        </Select>
        <p className="nx-field__label">Contacto</p>
        <Input label="Contacto" value={form.contactName} onChange={(e) => setForm({ ...form, contactName: e.target.value })} />
        <Input label="Correo" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        <Input label="Teléfono" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
        <p className="nx-field__label">Dirección</p>
        <Input label="Dirección" value={form.addressLine1} onChange={(e) => setForm({ ...form, addressLine1: e.target.value })} />
        <Input label="Ciudad" value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} />
        <Input label="Departamento / Estado" value={form.stateDepartment} onChange={(e) => setForm({ ...form, stateDepartment: e.target.value })} />
        <Input label="País (ISO-2)" value={form.country} maxLength={2} onChange={(e) => setForm({ ...form, country: e.target.value.toUpperCase() })} />
        <Button type="submit" loading={updateMutation.isPending} disabled={!form.legalName.trim()}>
          Guardar cambios
        </Button>
        {updateMutation.isSuccess ? <p className="nx-field__hint" role="status">Guardado.</p> : null}
        {updateMutation.isError ? <p className="nx-field__error" role="alert">{(updateMutation.error as Error).message}</p> : null}
      </form>

      <hr />
      <p className="nx-field__label">Cambiar estado</p>
      <form
        onSubmit={(event) => {
          event.preventDefault()
          if (!statusTarget) return
          if (statusNeedsReason && statusReason.trim().length < 10) return
          statusMutation.mutate()
        }}
      >
        <Select label="Nuevo estado" value={statusTarget} onChange={(e) => setStatusTarget(e.target.value)}>
          <option value="">Selecciona…</option>
          {(NEXT_STATUS[supplier.status] ?? []).map((s) => (
            <option key={s} value={s}>{SUPPLIER_STATUS_LABELS[s]}</option>
          ))}
        </Select>
        {statusTarget && statusNeedsReason ? (
          <Textarea
            label="Motivo (mínimo 10 caracteres, queda en auditoría)"
            value={statusReason}
            onChange={(e) => setStatusReason(e.target.value)}
            required
          />
        ) : null}
        <Button
          type="submit"
          variant="secondary"
          loading={statusMutation.isPending}
          disabled={!statusTarget || (statusNeedsReason && statusReason.trim().length < 10)}
        >
          Aplicar estado
        </Button>
        {statusMutation.isError ? <p className="nx-field__error" role="alert">{(statusMutation.error as Error).message}</p> : null}
      </form>
    </Modal>
  )
}
