import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent, type ReactNode } from 'react'
import { Badge, Button, Card, DatePicker, EmptyState, ErrorState, Input, LoadingState, Select, Table, Tabs } from '../../design-system'
import type { TableColumn } from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { useMutationError } from '../../hooks/useMutationError'
import { inventoryService } from '../../services/inventoryService'
import { masterDataService } from '../../services/masterDataService'
import { procurementService } from '../../services/procurementService'
import { projectService } from '../../services/projectService'
import type { Account } from '../../types/masterData'
import type { Item, Warehouse } from '../../types/inventory'
import { businessTodayIso } from '../../utils/businessDate'

type Resources = { companyId: string; items: Item[]; warehouses: Warehouse[] }

function ResourceSelects({ resources, itemId, setItemId, warehouseId, setWarehouseId }: { resources: Resources; itemId: string; setItemId: (v: string) => void; warehouseId: string; setWarehouseId: (v: string) => void }) {
  return <>
    <Select label="Ítem" value={itemId} onChange={(e) => setItemId(e.target.value)} required><option value="">Selecciona un ítem…</option>{resources.items.map((item) => <option key={item.id} value={item.id}>{item.sku} — {item.name}</option>)}</Select>
    <Select label="Almacén" value={warehouseId} onChange={(e) => setWarehouseId(e.target.value)} required><option value="">Selecciona un almacén…</option>{resources.warehouses.map((warehouse) => <option key={warehouse.id} value={warehouse.id}>{warehouse.code} — {warehouse.name}</option>)}</Select>
  </>
}

function OperationForm({ title, children, onSubmit, pending, disabled, action }: { title: string; children: ReactNode; onSubmit: (event: FormEvent) => void; pending: boolean; disabled: boolean; action: string }) {
  return <Card title={title}><form className="nx-form-grid" onSubmit={onSubmit}>{children}<Button type="submit" loading={pending} disabled={disabled}>{action}</Button></form></Card>
}

function InventoryOperations({ resources, accounts }: { resources: Resources; accounts: Account[] }) {
  const handleError = useMutationError()
  const queryClient = useQueryClient()
  const [itemId, setItemId] = useState('')
  const [warehouseId, setWarehouseId] = useState('')
  const [quantity, setQuantity] = useState('')
  const [unitCost, setUnitCost] = useState('')
  const [projectId, setProjectId] = useState('')
  const [destinationId, setDestinationId] = useState('')
  const [supplierId, setSupplierId] = useState('')
  const [notes, setNotes] = useState('')
  const [countedQuantity, setCountedQuantity] = useState('')
  const [effectiveDate, setEffectiveDate] = useState(businessTodayIso())
  const [inventoryAccountId, setInventoryAccountId] = useState('')
  const [costAccountId, setCostAccountId] = useState('')
  const projects = useQuery({ queryKey: ['projects', resources.companyId], queryFn: () => projectService.list(resources.companyId) })
  const suppliers = useQuery({ queryKey: ['suppliers', resources.companyId], queryFn: () => procurementService.listSuppliers(resources.companyId) })
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['inventory'] })
  const receive = useMutation({ mutationFn: () => inventoryService.receiveStock({ companyId: resources.companyId, itemId, warehouseId, quantity, unitCost }), onSuccess: invalidate, onError: (e) => handleError(e, 'Recibir inventario') })
  const issue = useMutation({ mutationFn: () => inventoryService.issueToProject({ companyId: resources.companyId, itemId, warehouseId, projectId, quantity, effectiveDate, costOfGoodsAccountId: costAccountId, inventoryAccountId }), onSuccess: invalidate, onError: (e) => handleError(e, 'Emitir inventario') })
  const transfer = useMutation({ mutationFn: () => inventoryService.transferStock({ companyId: resources.companyId, itemId, fromWarehouseId: warehouseId, toWarehouseId: destinationId, quantity }), onSuccess: invalidate, onError: (e) => handleError(e, 'Transferir inventario') })
  const supplierReturn = useMutation({ mutationFn: () => inventoryService.returnToSupplier({ companyId: resources.companyId, itemId, warehouseId, supplierId, quantity, notes: notes || undefined }), onSuccess: invalidate, onError: (e) => handleError(e, 'Devolver inventario') })
  const count = useMutation({ mutationFn: async () => { const created = await inventoryService.createPhysicalCount({ companyId: resources.companyId, warehouseId, countDate: effectiveDate, lines: [{ itemId, expectedQuantity: '0', countedQuantity }] }); return inventoryService.approvePhysicalCount(created.id) }, onSuccess: invalidate, onError: (e) => handleError(e, 'Aprobar conteo físico') })
  const common = <ResourceSelects resources={resources} itemId={itemId} setItemId={setItemId} warehouseId={warehouseId} setWarehouseId={setWarehouseId} />
  const assetAccounts = accounts.filter((a) => a.accountType === 'ASSET')
  const expenseAccounts = accounts.filter((a) => a.accountType === 'EXPENSE')
  const submit = (mutation: { mutate: () => void }) => (event: FormEvent) => { event.preventDefault(); mutation.mutate() }
  const quantityField = <Input label="Cantidad" type="number" min="0.0001" step="0.0001" value={quantity} onChange={(e) => setQuantity(e.target.value)} required />

  return <Tabs items={[
    { key: 'receive', label: 'Recibir', content: <OperationForm title="Entrada manual" onSubmit={submit(receive)} pending={receive.isPending} disabled={!itemId || !warehouseId || !quantity || !unitCost} action="Registrar entrada">{common}{quantityField}<Input label="Costo unitario" type="number" min="0" step="0.0001" value={unitCost} onChange={(e) => setUnitCost(e.target.value)} required /></OperationForm> },
    { key: 'issue', label: 'Emitir a proyecto', content: <OperationForm title="Consumo imputado a proyecto" onSubmit={submit(issue)} pending={issue.isPending} disabled={!itemId || !warehouseId || !projectId || !quantity || !effectiveDate || !costAccountId || !inventoryAccountId} action="Emitir material">{common}<Select label="Proyecto" value={projectId} onChange={(e) => setProjectId(e.target.value)} required><option value="">Selecciona…</option>{(projects.data ?? []).map((p) => <option key={p.id} value={p.id}>{p.code ? `${p.code} — ` : ''}{p.name}</option>)}</Select>{quantityField}<DatePicker label="Fecha efectiva" value={effectiveDate} onChange={(e) => setEffectiveDate(e.target.value)} required /><Select label="Cuenta de costo" value={costAccountId} onChange={(e) => setCostAccountId(e.target.value)} required><option value="">Selecciona…</option>{expenseAccounts.map((a) => <option key={a.id} value={a.id}>{a.code} — {a.name}</option>)}</Select><Select label="Cuenta de inventario" value={inventoryAccountId} onChange={(e) => setInventoryAccountId(e.target.value)} required><option value="">Selecciona…</option>{assetAccounts.map((a) => <option key={a.id} value={a.id}>{a.code} — {a.name}</option>)}</Select></OperationForm> },
    { key: 'transfer', label: 'Transferir', content: <OperationForm title="Transferencia entre almacenes" onSubmit={submit(transfer)} pending={transfer.isPending} disabled={!itemId || !warehouseId || !destinationId || destinationId === warehouseId || !quantity} action="Transferir stock">{common}<Select label="Almacén destino" value={destinationId} onChange={(e) => setDestinationId(e.target.value)} required><option value="">Selecciona…</option>{resources.warehouses.map((w) => <option key={w.id} value={w.id}>{w.code} — {w.name}</option>)}</Select>{quantityField}</OperationForm> },
    { key: 'return', label: 'Devolver a proveedor', content: <OperationForm title="Devolución a proveedor" onSubmit={submit(supplierReturn)} pending={supplierReturn.isPending} disabled={!itemId || !warehouseId || !supplierId || !quantity} action="Registrar devolución">{common}<Select label="Proveedor" value={supplierId} onChange={(e) => setSupplierId(e.target.value)} required><option value="">Selecciona…</option>{(suppliers.data ?? []).map((s) => <option key={s.id} value={s.id}>{s.legalName}</option>)}</Select>{quantityField}<Input label="Notas" value={notes} onChange={(e) => setNotes(e.target.value)} /></OperationForm> },
    { key: 'count', label: 'Conteo físico', content: <OperationForm title="Conteo y ajuste contable" onSubmit={submit(count)} pending={count.isPending} disabled={!itemId || !warehouseId || !countedQuantity || !effectiveDate} action="Crear y aprobar conteo">{common}<Input label="Cantidad contada" type="number" min="0" step="0.0001" value={countedQuantity} onChange={(e) => setCountedQuantity(e.target.value)} required /><DatePicker label="Fecha efectiva" value={effectiveDate} onChange={(e) => setEffectiveDate(e.target.value)} required /></OperationForm> },
  ]} />
}

export function InventoryPage() {
  const { activeCompanyId, activeCompany, isLoading } = useActiveCompany()
  const handleError = useMutationError()
  const queryClient = useQueryClient()
  const [sku, setSku] = useState('')
  const [name, setName] = useState('')
  const items = useQuery({ queryKey: ['inventory', 'items', activeCompanyId], queryFn: () => inventoryService.listItems(activeCompanyId as string), enabled: Boolean(activeCompanyId) })
  const warehouses = useQuery({ queryKey: ['inventory', 'warehouses', activeCompanyId], queryFn: () => inventoryService.listWarehouses(activeCompanyId as string), enabled: Boolean(activeCompanyId) })
  const accounts = useQuery({ queryKey: ['accounts', activeCompanyId], queryFn: () => masterDataService.listAccounts(activeCompanyId as string), enabled: Boolean(activeCompanyId) })
  const create = useMutation({ mutationFn: () => inventoryService.createItem({ companyId: activeCompanyId as string, sku, name }), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['inventory', 'items', activeCompanyId] }); setSku(''); setName('') }, onError: (e) => handleError(e, 'Crear ítem') })
  const columns: TableColumn<Item>[] = [{ key: 'sku', header: 'SKU', render: (r) => r.sku }, { key: 'name', header: 'Nombre', render: (r) => r.name }, { key: 'uom', header: 'Unidad', render: (r) => r.uom }, { key: 'active', header: 'Estado', render: (r) => <Badge>{r.active ? 'Activo' : 'Inactivo'}</Badge> }]
  if (isLoading) return <LoadingState label="Cargando compañías…" />
  if (!activeCompanyId) return <EmptyState title="Configura una compañía primero" description="Selecciona una compañía activa para operar inventario." />
  if (items.isLoading || warehouses.isLoading || accounts.isLoading) return <LoadingState label="Cargando inventario…" />
  if (items.isError || warehouses.isError || accounts.isError) return <ErrorState onRetry={() => { items.refetch(); warehouses.refetch(); accounts.refetch() }} />
  const ready = Boolean(activeCompany?.inventoryAccountId && activeCompany.inventoryAdjustmentGainAccountId && activeCompany.inventoryAdjustmentLossAccountId)
  return <div className="nx-stack"><header className="nx-page__header"><div><h1 className="nx-dashboard__title">Inventario</h1><p className="nx-page__subtitle">Movimientos y ajustes en {activeCompany?.functionalCurrencyCode ?? 'moneda funcional'}.</p></div></header><Card title="Configuración contable"><Badge tone={ready ? 'success' : 'warning'}>{ready ? 'Lista para conteos físicos' : 'Configura cuentas de inventario, ganancia y pérdida en Configuración'}</Badge></Card><InventoryOperations resources={{ companyId: activeCompanyId, items: items.data ?? [], warehouses: warehouses.data ?? [] }} accounts={accounts.data ?? []} /><Card title="Nuevo ítem"><form className="nx-form-grid" onSubmit={(e) => { e.preventDefault(); create.mutate() }}><Input label="SKU" value={sku} onChange={(e) => setSku(e.target.value)} required /><Input label="Nombre" value={name} onChange={(e) => setName(e.target.value)} required /><Button type="submit" loading={create.isPending} disabled={!sku || !name}>Crear ítem</Button></form></Card><Card title="Ítems"><Table columns={columns} rows={items.data ?? []} getRowKey={(r) => r.id} emptyMessage="Aún no hay ítems registrados." /></Card></div>
}
