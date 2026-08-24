import type { RoleName } from '../../types/auth'

export type HomeKey = 'finance' | 'project' | 'procurement' | 'warehouse' | 'auditor' | 'default'

export interface HomeSection {
  title: string
  description: string
}

export interface HomeConfig {
  key: HomeKey
  title: string
  subtitle: string
  showTreasurySummary: boolean
  sections: HomeSection[]
}

const homeConfigs: Record<HomeKey, HomeConfig> = {
  finance: {
    key: 'finance',
    title: 'Inicio — Finanzas',
    subtitle: 'Caja, contabilidad y cuentas por pagar/cobrar.',
    showTreasurySummary: true,
    sections: [
      { title: 'Aprobaciones pendientes', description: 'Se conectará cuando el motor de workflow (NXR-REQ-0087/0088) esté disponible.' },
      { title: 'Cuentas por pagar próximas a vencer', description: 'Se conectará cuando el módulo de Cuentas por Pagar (NXR-REQ-0023) esté disponible.' },
      { title: 'Conciliación bancaria', description: 'Se conectará cuando la conciliación bancaria (NXR-REQ-0021) esté disponible.' },
    ],
  },
  project: {
    key: 'project',
    title: 'Inicio — Proyectos',
    subtitle: 'Presupuesto, compromisos, avance y abastecimiento de tus proyectos.',
    showTreasurySummary: false,
    sections: [
      { title: 'Presupuesto vs. actual', description: 'Se conectará cuando Budget/Controlling (NXR-REQ-0031) esté disponible.' },
      { title: 'Compromisos y órdenes de compra', description: 'Se conectará cuando Procurement (NXR-REQ-0040-0048) esté disponible.' },
      { title: 'Avance de obra', description: 'Se conectará cuando Progress (NXR-REQ-0039) esté disponible.' },
      { title: 'RFI / Submittals abiertos', description: 'Se conectará cuando RFI/Submittals (NXR-REQ-0085/0086) esté disponible.' },
    ],
  },
  procurement: {
    key: 'procurement',
    title: 'Inicio — Abastecimiento',
    subtitle: 'Solicitudes, RFQ, órdenes de compra y proveedores.',
    showTreasurySummary: false,
    sections: [
      { title: 'Solicitudes de compra pendientes', description: 'Se conectará cuando Purchase Requisition (NXR-REQ-0040) esté disponible.' },
      { title: 'RFQ activas', description: 'Se conectará cuando RFQ (NXR-REQ-0042) esté disponible.' },
      { title: 'Órdenes de compra en curso', description: 'Se conectará cuando Purchase Order (NXR-REQ-0045) esté disponible.' },
      { title: 'Estado de proveedores', description: 'Se conectará cuando Supplier Performance (NXR-REQ-0058) esté disponible.' },
    ],
  },
  warehouse: {
    key: 'warehouse',
    title: 'Inicio — Almacén',
    subtitle: 'Existencias, recepciones, salidas y conteos.',
    showTreasurySummary: false,
    sections: [
      { title: 'Existencias por almacén', description: 'Se conectará cuando Stock Ledger (NXR-REQ-0051) esté disponible.' },
      { title: 'Recepciones pendientes', description: 'Se conectará cuando Goods Receipt (NXR-REQ-0046) esté disponible.' },
      { title: 'Alertas de stock bajo', description: 'Se conectará cuando Inventory (NXR-REQ-0049-0056) esté disponible.' },
    ],
  },
  auditor: {
    key: 'auditor',
    title: 'Inicio — Auditoría',
    subtitle: 'Trazabilidad, excepciones y reversos.',
    showTreasurySummary: false,
    sections: [
      { title: 'Excepciones recientes', description: 'Se conectará cuando Audit (NXR-REQ-0090) esté disponible.' },
      { title: 'Correcciones y anulaciones', description: 'Se conectará cuando Corrections/Annulments (NXR-REQ-0025/0026) esté disponible.' },
      { title: 'Aprobaciones y segregación de funciones', description: 'Se conectará cuando SoD (NXR-REQ-0089) esté disponible.' },
    ],
  },
  default: {
    key: 'default',
    title: 'Inicio',
    subtitle: 'Resumen general de Nexora Group.',
    showTreasurySummary: false,
    sections: [
      { title: 'Indicadores de tu rol', description: 'Aún no hay indicadores configurados para este rol.' },
    ],
  },
}

const roleToHome: Partial<Record<RoleName, HomeKey>> = {
  Administrator: 'finance',
  'Finance Manager': 'finance',
  'Treasury Manager': 'finance',
  Accountant: 'finance',
  'Project Manager': 'project',
  'Project Controller': 'project',
  'Procurement Manager': 'procurement',
  Buyer: 'procurement',
  'Warehouse Manager': 'warehouse',
  Auditor: 'auditor',
}

/** First matching role wins — a user with multiple roles sees the highest-priority relevant home. Priority order mirrors §93 of the master order. */
const priority: RoleName[] = [
  'Administrator',
  'Finance Manager',
  'Treasury Manager',
  'Accountant',
  'Auditor',
  'Project Manager',
  'Project Controller',
  'Procurement Manager',
  'Buyer',
  'Warehouse Manager',
]

export function resolveHomeConfig(roles: RoleName[]): HomeConfig {
  const matchedRole = priority.find((role) => roles.includes(role))
  const key = matchedRole ? roleToHome[matchedRole] : undefined
  return homeConfigs[key ?? 'default']
}
