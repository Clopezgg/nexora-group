import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  Input,
  LoadingState,
  Modal,
  Select,
  Table,
  Tabs,
  type TableColumn,
} from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { equipmentService } from '../../services/equipmentService'
import { projectService } from '../../services/projectService'
import type { Equipment, FuelLog, MaintenanceOrder } from '../../types/equipment'

const EQUIPMENT_STATUS_TONE: Record<Equipment['status'], 'success' | 'warning' | 'neutral' | 'danger' | 'info'> = {
  AVAILABLE: 'success',
  IN_USE: 'info',
  UNDER_MAINTENANCE: 'warning',
  OUT_OF_SERVICE: 'danger',
}

const ORDER_STATUS_TONE: Record<MaintenanceOrder['status'], 'success' | 'warning' | 'neutral' | 'danger'> = {
  OPEN: 'warning',
  IN_PROGRESS: 'warning',
  CLOSED: 'success',
  CANCELLED: 'neutral',
}

export function EquipmentPage() {
  const { activeCompanyId, isLoading: loadingCompanies } = useActiveCompany()

  if (loadingCompanies) return <LoadingState label="Cargando compañías…" />
  if (!activeCompanyId) {
    return (
      <EmptyState icon="🚜" title="Configura una compañía primero" description="No hay compañías registradas todavía." />
    )
  }

  return (
    <div>
      <header className="nx-page__header">
        <h1 className="nx-dashboard__title">Equipos y mantenimiento</h1>
      </header>
      <Tabs
        items={[
          { key: 'equipos', label: 'Equipos', content: <EquipmentTab companyId={activeCompanyId} /> },
          { key: 'combustible', label: 'Combustible', content: <FuelTab companyId={activeCompanyId} /> },
          { key: 'mantenimiento', label: 'Mantenimiento', content: <MaintenanceTab companyId={activeCompanyId} /> },
        ]}
      />
    </div>
  )
}

function useEquipmentList(companyId: string) {
  return useQuery({
    queryKey: ['equipment', 'list', companyId],
    queryFn: () => equipmentService.list(companyId),
    enabled: Boolean(companyId),
  })
}

function EquipmentTab({ companyId }: { companyId: string }) {
  const queryClient = useQueryClient()
  const [modalOpen, setModalOpen] = useState(false)
  const [form, setForm] = useState({ equipmentType: '', name: '', plateNumber: '' })

  const equipmentQuery = useEquipmentList(companyId)

  const createMutation = useMutation({
    mutationFn: () =>
      equipmentService.create({
        companyId,
        equipmentType: form.equipmentType,
        name: form.name,
        plateNumber: form.plateNumber || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['equipment', 'list', companyId] })
      setModalOpen(false)
      setForm({ equipmentType: '', name: '', plateNumber: '' })
    },
  })

  const columns: TableColumn<Equipment>[] = [
    { key: 'name', header: 'Equipo', render: (row) => row.name },
    { key: 'equipmentType', header: 'Tipo', render: (row) => row.equipmentType },
    { key: 'plateNumber', header: 'Placa', render: (row) => row.plateNumber ?? '—' },
    { key: 'hourMeter', header: 'Horómetro', render: (row) => row.hourMeter },
    {
      key: 'status',
      header: 'Estado',
      render: (row) => <Badge tone={EQUIPMENT_STATUS_TONE[row.status]}>{row.status}</Badge>,
    },
  ]

  return (
    <Card>
      <div className="nx-page__header">
        <span />
        <Button onClick={() => setModalOpen(true)}>Nuevo equipo</Button>
      </div>
      {equipmentQuery.isLoading ? (
        <LoadingState label="Cargando equipos…" />
      ) : equipmentQuery.isError ? (
        <ErrorState onRetry={() => equipmentQuery.refetch()} />
      ) : (
        <Table columns={columns} rows={equipmentQuery.data ?? []} getRowKey={(row) => row.id} emptyMessage="Aún no hay equipos registrados." />
      )}

      <Modal open={modalOpen} title="Nuevo equipo" onClose={() => setModalOpen(false)}>
        <form
          onSubmit={(event) => {
            event.preventDefault()
            createMutation.mutate()
          }}
        >
          <Input label="Tipo" value={form.equipmentType} onChange={(e) => setForm({ ...form, equipmentType: e.target.value })} required />
          <Input label="Nombre" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          <Input label="Placa" value={form.plateNumber} onChange={(e) => setForm({ ...form, plateNumber: e.target.value })} />
          <Button type="submit" loading={createMutation.isPending}>
            Guardar
          </Button>
        </form>
      </Modal>
    </Card>
  )
}

function FuelTab({ companyId }: { companyId: string }) {
  const queryClient = useQueryClient()
  const equipmentQuery = useEquipmentList(companyId)
  const [selectedEquipmentId, setSelectedEquipmentId] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [form, setForm] = useState({ logDate: '', quantity: '', unitCost: '', scope: 'GENERAL' as 'GENERAL' | 'PROJECT', projectId: '' })

  const projectsQuery = useQuery({
    queryKey: ['projects', companyId],
    queryFn: () => projectService.list(companyId),
    enabled: Boolean(companyId),
  })

  const fuelLogsQuery = useQuery({
    queryKey: ['equipment', 'fuel-logs', selectedEquipmentId],
    queryFn: () => equipmentService.listFuelLogs(selectedEquipmentId),
    enabled: Boolean(selectedEquipmentId),
  })

  const createMutation = useMutation({
    mutationFn: () =>
      equipmentService.recordFuelLog({
        companyId,
        equipmentId: selectedEquipmentId,
        logDate: form.logDate,
        quantity: form.quantity,
        unitCost: form.unitCost,
        scope: form.scope,
        projectId: form.scope === 'PROJECT' ? form.projectId || undefined : undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['equipment', 'fuel-logs', selectedEquipmentId] })
      setModalOpen(false)
      setForm({ logDate: '', quantity: '', unitCost: '', scope: 'GENERAL', projectId: '' })
    },
  })

  const columns: TableColumn<FuelLog>[] = [
    { key: 'logDate', header: 'Fecha', render: (row) => row.logDate },
    { key: 'quantity', header: 'Cantidad', render: (row) => row.quantity },
    { key: 'unitCost', header: 'Costo unitario', render: (row) => row.unitCost },
    { key: 'totalCost', header: 'Total', render: (row) => row.totalCost },
  ]

  return (
    <Card>
      <div className="nx-page__header">
        <Select value={selectedEquipmentId} onChange={(e) => setSelectedEquipmentId(e.target.value)}>
          <option value="">Selecciona un equipo</option>
          {(equipmentQuery.data ?? []).map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </Select>
        <Button onClick={() => setModalOpen(true)} disabled={!selectedEquipmentId}>
          Registrar combustible
        </Button>
      </div>
      {!selectedEquipmentId ? (
        <EmptyState title="Selecciona un equipo" description="Elige un equipo para ver su historial de combustible." />
      ) : fuelLogsQuery.isLoading ? (
        <LoadingState label="Cargando…" />
      ) : (
        <Table columns={columns} rows={fuelLogsQuery.data ?? []} getRowKey={(row) => row.id} emptyMessage="Sin registros de combustible." />
      )}

      <Modal open={modalOpen} title="Registrar combustible" onClose={() => setModalOpen(false)}>
        <form
          onSubmit={(event) => {
            event.preventDefault()
            createMutation.mutate()
          }}
        >
          <Input label="Fecha" type="date" value={form.logDate} onChange={(e) => setForm({ ...form, logDate: e.target.value })} required />
          <Input label="Cantidad (galones)" value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })} required />
          <Input label="Costo unitario" value={form.unitCost} onChange={(e) => setForm({ ...form, unitCost: e.target.value })} required />
          <Select
            label="Ámbito"
            value={form.scope}
            onChange={(e) => setForm({ ...form, scope: e.target.value as 'GENERAL' | 'PROJECT', projectId: '' })}
          >
            <option value="GENERAL">General</option>
            <option value="PROJECT">Proyecto</option>
          </Select>
          {form.scope === 'PROJECT' ? (
            <Select
              label="Proyecto"
              value={form.projectId}
              onChange={(e) => setForm({ ...form, projectId: e.target.value })}
              required
            >
              <option value="">Selecciona un proyecto</option>
              {(projectsQuery.data ?? []).map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </Select>
          ) : null}
          <Button type="submit" loading={createMutation.isPending}>
            Guardar
          </Button>
        </form>
      </Modal>
    </Card>
  )
}

function MaintenanceTab({ companyId }: { companyId: string }) {
  const queryClient = useQueryClient()
  const equipmentQuery = useEquipmentList(companyId)
  const [selectedEquipmentId, setSelectedEquipmentId] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [form, setForm] = useState({ orderType: 'CORRECTIVE' as 'PREVENTIVE' | 'CORRECTIVE', openedAt: '', description: '' })

  const ordersQuery = useQuery({
    queryKey: ['equipment', 'maintenance-orders', selectedEquipmentId],
    queryFn: () => equipmentService.listMaintenanceOrders(selectedEquipmentId),
    enabled: Boolean(selectedEquipmentId),
  })

  const createMutation = useMutation({
    mutationFn: () =>
      equipmentService.createMaintenanceOrder(selectedEquipmentId, {
        orderType: form.orderType,
        openedAt: form.openedAt,
        description: form.description || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['equipment', 'maintenance-orders', selectedEquipmentId] })
      queryClient.invalidateQueries({ queryKey: ['equipment', 'list', companyId] })
      setModalOpen(false)
      setForm({ orderType: 'CORRECTIVE', openedAt: '', description: '' })
    },
  })

  const closeMutation = useMutation({
    mutationFn: (orderId: string) => equipmentService.updateMaintenanceOrder(orderId, { status: 'CLOSED' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['equipment', 'maintenance-orders', selectedEquipmentId] })
      queryClient.invalidateQueries({ queryKey: ['equipment', 'list', companyId] })
    },
  })

  const columns: TableColumn<MaintenanceOrder>[] = [
    { key: 'orderType', header: 'Tipo', render: (row) => row.orderType },
    { key: 'openedAt', header: 'Apertura', render: (row) => row.openedAt },
    { key: 'status', header: 'Estado', render: (row) => <Badge tone={ORDER_STATUS_TONE[row.status]}>{row.status}</Badge> },
    { key: 'partsCost', header: 'Repuestos', render: (row) => row.partsCost },
    { key: 'laborCost', header: 'Mano de obra', render: (row) => row.laborCost },
    {
      key: 'actions',
      header: '',
      render: (row) =>
        row.status === 'OPEN' || row.status === 'IN_PROGRESS' ? (
          <Button variant="secondary" onClick={() => closeMutation.mutate(row.id)}>
            Cerrar orden
          </Button>
        ) : null,
    },
  ]

  return (
    <Card>
      <div className="nx-page__header">
        <Select value={selectedEquipmentId} onChange={(e) => setSelectedEquipmentId(e.target.value)}>
          <option value="">Selecciona un equipo</option>
          {(equipmentQuery.data ?? []).map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </Select>
        <Button onClick={() => setModalOpen(true)} disabled={!selectedEquipmentId}>
          Nueva orden
        </Button>
      </div>
      {!selectedEquipmentId ? (
        <EmptyState title="Selecciona un equipo" description="Elige un equipo para ver sus órdenes de mantenimiento." />
      ) : ordersQuery.isLoading ? (
        <LoadingState label="Cargando…" />
      ) : (
        <Table columns={columns} rows={ordersQuery.data ?? []} getRowKey={(row) => row.id} emptyMessage="Sin órdenes de mantenimiento." />
      )}

      <Modal open={modalOpen} title="Nueva orden de mantenimiento" onClose={() => setModalOpen(false)}>
        <form
          onSubmit={(event) => {
            event.preventDefault()
            createMutation.mutate()
          }}
        >
          <Select
            label="Tipo"
            value={form.orderType}
            onChange={(e) => setForm({ ...form, orderType: e.target.value as 'PREVENTIVE' | 'CORRECTIVE' })}
          >
            <option value="CORRECTIVE">Correctivo</option>
            <option value="PREVENTIVE">Preventivo</option>
          </Select>
          <Input label="Fecha de apertura" type="date" value={form.openedAt} onChange={(e) => setForm({ ...form, openedAt: e.target.value })} required />
          <Input label="Descripción" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          <Button type="submit" loading={createMutation.isPending}>
            Guardar
          </Button>
        </form>
      </Modal>
    </Card>
  )
}
