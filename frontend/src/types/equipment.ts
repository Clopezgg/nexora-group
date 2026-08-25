export interface Equipment {
  id: string
  companyId: string
  assetId: string | null
  projectId: string | null
  equipmentType: string
  name: string
  serialNumber: string | null
  plateNumber: string | null
  operator: string | null
  hourMeter: string
  odometer: string
  status: 'AVAILABLE' | 'IN_USE' | 'UNDER_MAINTENANCE' | 'OUT_OF_SERVICE'
}

export interface FuelLog {
  id: string
  companyId: string
  equipmentId: string | null
  vehicleDescription: string | null
  logDate: string
  quantity: string
  unitCost: string
  totalCost: string
  scope: 'GENERAL' | 'PROJECT'
  projectId: string | null
}

export interface MaintenancePlan {
  id: string
  equipmentId: string
  name: string
  triggerType: 'DATE' | 'HOURS' | 'ODOMETER'
  triggerValue: string
  description: string | null
  active: boolean
}

export interface MaintenanceOrder {
  id: string
  equipmentId: string
  planId: string | null
  orderType: 'PREVENTIVE' | 'CORRECTIVE'
  status: 'OPEN' | 'IN_PROGRESS' | 'CLOSED' | 'CANCELLED'
  openedAt: string
  closedAt: string | null
  supplierRef: string | null
  partsCost: string
  laborCost: string
  downtimeHours: string
  description: string | null
}
