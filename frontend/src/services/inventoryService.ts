import { apiFetch } from './httpClient'
import type { Item, PhysicalCount, StockLedgerEntry, StockPosition, Warehouse } from '../types/inventory'

export const inventoryService = {
  listItems: (companyId: string) => apiFetch<Item[]>(`/inventory/items?company_id=${companyId}`),
  createItem: (payload: { companyId: string; sku: string; name: string; uom?: string }) =>
    apiFetch<Item>('/inventory/items', { method: 'POST', body: JSON.stringify(payload) }),

  listWarehouses: (companyId: string) =>
    apiFetch<Warehouse[]>(`/inventory/warehouses?company_id=${companyId}`),
  createWarehouse: (payload: { companyId: string; code: string; name: string }) =>
    apiFetch<Warehouse>('/inventory/warehouses', { method: 'POST', body: JSON.stringify(payload) }),

  getStockPosition: (itemId: string, warehouseId: string) =>
    apiFetch<StockPosition>(`/inventory/stock/position?item_id=${itemId}&warehouse_id=${warehouseId}`),
  receiveStock: (payload: { companyId: string; itemId: string; warehouseId: string; quantity: string; unitCost: string }) =>
    apiFetch<StockLedgerEntry>('/inventory/stock/receive', { method: 'POST', body: JSON.stringify(payload) }),
  issueToProject: (payload: { companyId: string; itemId: string; warehouseId: string; projectId: string; quantity: string; effectiveDate: string; costOfGoodsAccountId: string; inventoryAccountId: string }) =>
    apiFetch<StockLedgerEntry>('/inventory/stock/issue-to-project', { method: 'POST', body: JSON.stringify(payload) }),
  transferStock: (payload: { companyId: string; itemId: string; fromWarehouseId: string; toWarehouseId: string; quantity: string }) =>
    apiFetch<StockLedgerEntry[]>('/inventory/stock/transfer', { method: 'POST', body: JSON.stringify(payload) }),
  returnToSupplier: (payload: { companyId: string; itemId: string; warehouseId: string; supplierId: string; quantity: string; notes?: string }) =>
    apiFetch<StockLedgerEntry>('/inventory/stock/return-to-supplier', { method: 'POST', body: JSON.stringify(payload) }),
  createPhysicalCount: (payload: { companyId: string; warehouseId: string; countDate: string; lines: { itemId: string; expectedQuantity: string; countedQuantity: string }[] }) =>
    apiFetch<PhysicalCount>('/inventory/physical-counts', { method: 'POST', body: JSON.stringify(payload) }),
  approvePhysicalCount: (physicalCountId: string) =>
    apiFetch<PhysicalCount>(`/inventory/physical-counts/${physicalCountId}/approve`, { method: 'POST' }),
}
