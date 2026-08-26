import { apiFetch } from './httpClient'
import type { Equipment, FuelLog, MaintenanceOrder, MaintenancePlan } from '../types/equipment'

export const equipmentService = {
  list: (companyId: string) => apiFetch<Equipment[]>(`/equipment?companyId=${companyId}`),
  create: (payload: { companyId: string; equipmentType: string; name: string; serialNumber?: string; plateNumber?: string }) =>
    apiFetch<Equipment>('/equipment', { method: 'POST', body: JSON.stringify(payload) }),
  changeStatus: (equipmentId: string, status: Equipment['status']) =>
    apiFetch<Equipment>(`/equipment/${equipmentId}/status`, { method: 'POST', body: JSON.stringify({ status }) }),

  listFuelLogs: (equipmentId: string) => apiFetch<FuelLog[]>(`/equipment/${equipmentId}/fuel-logs`),
  recordFuelLog: (payload: {
    companyId: string
    equipmentId?: string
    logDate: string
    quantity: string
    unitCost: string
    scope: 'GENERAL' | 'PROJECT'
    projectId?: string
  }) => apiFetch<FuelLog>('/equipment/fuel-logs', { method: 'POST', body: JSON.stringify(payload) }),

  listMaintenancePlans: (equipmentId: string) =>
    apiFetch<MaintenancePlan[]>(`/equipment/${equipmentId}/maintenance-plans`),
  createMaintenancePlan: (
    equipmentId: string,
    payload: { name: string; triggerType: 'DATE' | 'HOURS' | 'ODOMETER'; triggerValue: string; description?: string },
  ) =>
    apiFetch<MaintenancePlan>(`/equipment/${equipmentId}/maintenance-plans`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  listMaintenanceOrders: (equipmentId: string) =>
    apiFetch<MaintenanceOrder[]>(`/equipment/${equipmentId}/maintenance-orders`),
  createMaintenanceOrder: (
    equipmentId: string,
    payload: { orderType: 'PREVENTIVE' | 'CORRECTIVE'; openedAt: string; description?: string },
  ) =>
    apiFetch<MaintenanceOrder>(`/equipment/${equipmentId}/maintenance-orders`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateMaintenanceOrder: (
    orderId: string,
    payload: Partial<{
      status: MaintenanceOrder['status']
      partsCost: string
      laborCost: string
      downtimeHours: string
      description: string
    }>,
  ) =>
    apiFetch<MaintenanceOrder>(`/equipment/maintenance-orders/${orderId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
}
