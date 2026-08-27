import type { RoleName } from '../../types/auth'

export type HomeKey = 'finance' | 'project' | 'procurement' | 'warehouse' | 'auditor' | 'default'

export interface HomeSection {
  title: string
  description: string
  path: string
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
      { title: 'Aprobaciones pendientes', description: 'Revisa y resuelve solicitudes según tus permisos.', path: '/inicio/aprobaciones' },
      { title: 'Cuentas por pagar', description: 'Consulta facturas, vencimientos y pagos a proveedores.', path: '/finanzas/cuentas-por-pagar' },
      { title: 'Reportes financieros', description: 'Consulta balances, resultados, flujo de efectivo y libro mayor.', path: '/control/reportes' },
    ],
  },
  project: {
    key: 'project',
    title: 'Inicio — Proyectos',
    subtitle: 'Presupuesto, compromisos, avance y abastecimiento de tus proyectos.',
    showTreasurySummary: false,
    sections: [
      { title: 'Presupuesto vs. actual', description: 'Consulta presupuesto autorizado, ejecutado y disponible.', path: '/proyectos/presupuestos' },
      { title: 'Compromisos y órdenes de compra', description: 'Gestiona órdenes y compromisos reales del proyecto.', path: '/abastecimiento/ordenes-de-compra' },
      { title: 'Avance de obra', description: 'Registra y consulta avance planeado frente al real.', path: '/proyectos/avances' },
      { title: 'RFI / Submittals abiertos', description: 'Gestiona consultas técnicas y entregables del proyecto.', path: '/proyectos/rfi-submittals' },
    ],
  },
  procurement: {
    key: 'procurement',
    title: 'Inicio — Abastecimiento',
    subtitle: 'Solicitudes, RFQ, órdenes de compra y proveedores.',
    showTreasurySummary: false,
    sections: [
      { title: 'Solicitudes de compra pendientes', description: 'Gestiona solicitudes de compra reales.', path: '/abastecimiento/solicitudes' },
      { title: 'RFQ activas', description: 'Compara ofertas de proveedores registradas.', path: '/abastecimiento/comparativos' },
      { title: 'Órdenes de compra en curso', description: 'Consulta y gestiona órdenes de compra.', path: '/abastecimiento/ordenes-de-compra' },
      { title: 'Estado de proveedores', description: 'Consulta el desempeño calculado de proveedores.', path: '/control/reportes' },
    ],
  },
  warehouse: {
    key: 'warehouse',
    title: 'Inicio — Almacén',
    subtitle: 'Existencias, recepciones, salidas y conteos.',
    showTreasurySummary: false,
    sections: [
      { title: 'Existencias por almacén', description: 'Consulta existencias y movimientos registrados.', path: '/abastecimiento/inventario' },
      { title: 'Recepciones pendientes', description: 'Registra y consulta recepciones de compra.', path: '/abastecimiento/recepciones' },
      { title: 'Alertas de stock bajo', description: 'Administra inventario y almacenes.', path: '/abastecimiento/almacenes' },
    ],
  },
  auditor: {
    key: 'auditor',
    title: 'Inicio — Auditoría',
    subtitle: 'Trazabilidad, excepciones y reversos.',
    showTreasurySummary: false,
    sections: [
      { title: 'Excepciones recientes', description: 'Consulta el historial inmutable de auditoría.', path: '/control/auditoria' },
      { title: 'Correcciones y anulaciones', description: 'Revisa movimientos contables y sus reversos.', path: '/control/reportes' },
      { title: 'Aprobaciones y segregación de funciones', description: 'Revisa aprobaciones y controles de segregación.', path: '/inicio/aprobaciones' },
    ],
  },
  default: {
    key: 'default',
    title: 'Inicio',
    subtitle: 'Resumen general de Nexora Group.',
    showTreasurySummary: false,
    sections: [
      { title: 'Indicadores de tu rol', description: 'Accede a los módulos habilitados para tu perfil.', path: '/inicio' },
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
