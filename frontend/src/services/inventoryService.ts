import { apiFetch } from './httpClient'
import type { Item, StockPosition, Warehouse } from '../types/inventory'

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
    apiFetch('/inventory/stock/receive', { method: 'POST', body: JSON.stringify(payload) }),
}
