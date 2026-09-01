import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  FilterBar,
  Input,
  LoadingState,
  Modal,
  Select,
  Table,
} from '../../design-system'
import type { TableColumn } from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { useMutationError } from '../../hooks/useMutationError'
import { procurementService } from '../../services/procurementService'
import type { Supplier, SupplierPartyRole } from '../../types/procurement'
import {
  SUPPLIER_PARTY_ROLE_LABELS,
  supplierPartyRoleLabel,
  supplierStatusLabel,
} from '../../utils/statusLabels'
import { SupplierDrawer } from './SupplierDrawer'

const STATUS_TONE: Record<string, 'neutral' | 'warning' | 'danger' | 'success'> = {
  ACTIVE: 'success',
  INACTIVE: 'neutral',
  BLOCKED: 'danger',
  ARCHIVED: 'neutral',
}

export function SuppliersPage() {
  const { activeCompanyId, isLoading: loadingCompanies } = useActiveCompany()
  const handleMutationError = useMutationError()
  const [modalOpen, setModalOpen] = useState(false)
  const [selected, setSelected] = useState<Supplier | null>(null)
  const [filterRole, setFilterRole] = useState('')
  const [showArchived, setShowArchived] = useState(false)
  const [form, setForm] = useState({
    legalName: '',
    tradeName: '',
    taxId: '',
    contactName: '',
    phone: '',
    addressLine1: '',
    city: '',
    stateDepartment: '',
    country: '',
    partyRole: 'SUPPLIER' as SupplierPartyRole,
  })
  const queryClient = useQueryClient()

  const suppliersQuery = useQuery({
    queryKey: ['procurement', 'suppliers', activeCompanyId],
    queryFn: () => procurementService.listSuppliers(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  const createMutation = useMutation({
    mutationFn: () =>
      procurementService.createSupplier({
        companyId: activeCompanyId as string,
        legalName: form.legalName,
        tradeName: form.tradeName || undefined,
        taxId: form.taxId || undefined,
        contactName: form.contactName || undefined,
        phone: form.phone || undefined,
        addressLine1: form.addressLine1 || undefined,
        city: form.city || undefined,
        stateDepartment: form.stateDepartment || undefined,
        country: form.country || undefined,
        partyRole: form.partyRole,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['procurement', 'suppliers'] })
      setModalOpen(false)
      setForm({
        legalName: '', tradeName: '', taxId: '', contactName: '', phone: '',
        addressLine1: '', city: '', stateDepartment: '', country: '', partyRole: 'SUPPLIER',
      })
    },
    onError: (error) => handleMutationError(error, 'Crear proveedor / contratista'),
  })

  const rows = useMemo(() => {
    let list = suppliersQuery.data ?? []
    if (!showArchived) list = list.filter((s) => s.status !== 'ARCHIVED')
    if (filterRole) list = list.filter((s) => s.partyRole === filterRole || s.partyRole === 'BOTH')
    return list
  }, [suppliersQuery.data, showArchived, filterRole])

  const columns: TableColumn<Supplier>[] = [
    { key: 'legalName', header: 'Razón social / Nombre', render: (row) => row.legalName },
    { key: 'tradeName', header: 'Nombre comercial', render: (row) => row.tradeName ?? '—' },
    { key: 'partyRole', header: 'Tipo', render: (row) => <Badge tone="neutral">{supplierPartyRoleLabel(row.partyRole)}</Badge> },
    { key: 'taxId', header: 'RTN / ID', render: (row) => row.taxId ?? '—' },
    { key: 'contact', header: 'Contacto', render: (row) => row.contactName ?? '—' },
    { key: 'phone', header: 'Teléfono', render: (row) => row.phone ?? '—' },
    {
      key: 'address',
      header: 'Dirección',
      render: (row) =>
        [row.addressLine1, row.city, row.stateDepartment, row.country].filter(Boolean).join(', ') || row.address || '—',
    },
    {
      key: 'status',
      header: 'Estado',
      render: (row) => <Badge tone={STATUS_TONE[row.status] ?? 'neutral'}>{supplierStatusLabel(row.status)}</Badge>,
    },
    {
      key: 'actions',
      header: 'Acciones',
      render: (row) => (
        <Button variant="secondary" onClick={() => setSelected(row)}>
          Ver / editar
        </Button>
      ),
    },
  ]

  if (loadingCompanies) return <LoadingState label="Cargando compañías…" />
  if (!activeCompanyId) {
    return <EmptyState title="Configura una compañía primero" description="No hay compañías registradas todavía." />
  }

  return (
    <div>
      <header className="nx-page__header">
        <h1 className="nx-dashboard__title">Proveedores y Contratistas</h1>
        <Button onClick={() => setModalOpen(true)}>+ Nuevo proveedor / contratista</Button>
      </header>

      <FilterBar onClear={() => { setFilterRole(''); setShowArchived(false) }}>
        <Select label="Tipo" value={filterRole} onChange={(e) => setFilterRole(e.target.value)}>
          <option value="">Todos</option>
          {(Object.keys(SUPPLIER_PARTY_ROLE_LABELS)).map((r) => (
            <option key={r} value={r}>{SUPPLIER_PARTY_ROLE_LABELS[r]}</option>
          ))}
        </Select>
        <div className="nx-field">
          <span className="nx-field__label">Archivados</span>
          <Button variant={showArchived ? 'secondary' : 'ghost'} onClick={() => setShowArchived((v) => !v)}>
            {showArchived ? 'Ocultar archivados' : 'Mostrar archivados'}
          </Button>
        </div>
      </FilterBar>

      <Card>
        {suppliersQuery.isLoading ? (
          <LoadingState label="Cargando…" />
        ) : suppliersQuery.isError ? (
          <ErrorState onRetry={() => suppliersQuery.refetch()} />
        ) : (
          <Table
            columns={columns}
            rows={rows}
            getRowKey={(row) => row.id}
            emptyMessage="Aún no hay proveedores ni contratistas registrados."
          />
        )}
      </Card>

      <Modal open={modalOpen} title="Nuevo proveedor / contratista" onClose={() => setModalOpen(false)}>
        <form
          onSubmit={(event) => {
            event.preventDefault()
            if (form.legalName.trim()) createMutation.mutate()
          }}
        >
          <Input label="Razón social / Nombre" value={form.legalName} onChange={(e) => setForm({ ...form, legalName: e.target.value })} required />
          <Input label="Nombre comercial" value={form.tradeName} onChange={(e) => setForm({ ...form, tradeName: e.target.value })} />
          <Select
            label="Tipo de tercero"
            value={form.partyRole}
            onChange={(e) => setForm({ ...form, partyRole: e.target.value as SupplierPartyRole })}
          >
            {(Object.keys(SUPPLIER_PARTY_ROLE_LABELS)).map((r) => (
              <option key={r} value={r}>{SUPPLIER_PARTY_ROLE_LABELS[r]}</option>
            ))}
          </Select>
          <Input label="RTN / identificación" value={form.taxId} onChange={(e) => setForm({ ...form, taxId: e.target.value })} />
          <Input label="Contacto" value={form.contactName} onChange={(e) => setForm({ ...form, contactName: e.target.value })} />
          <Input label="Teléfono" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
          <Input label="Dirección" value={form.addressLine1} onChange={(e) => setForm({ ...form, addressLine1: e.target.value })} />
          <Input label="Ciudad" value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} />
          <Input label="Departamento / Estado" value={form.stateDepartment} onChange={(e) => setForm({ ...form, stateDepartment: e.target.value })} />
          <Input label="País (ISO-2)" value={form.country} maxLength={2} onChange={(e) => setForm({ ...form, country: e.target.value.toUpperCase() })} />
          <Button type="submit" loading={createMutation.isPending} disabled={!form.legalName.trim()}>
            Guardar
          </Button>
        </form>
      </Modal>

      {selected ? <SupplierDrawer supplier={selected} onClose={() => setSelected(null)} /> : null}
    </div>
  )
}
