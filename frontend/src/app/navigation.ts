import type { IconName } from '../design-system'

export interface NavItem {
  path: string
  label: string
  icon: IconName
}

export interface NavGroup {
  key: string
  label: string
  items: NavItem[]
}

export const navGroups: NavGroup[] = [
  {
    key: 'inicio',
    label: 'Inicio',
    items: [
      { path: '/inicio', label: 'Inicio', icon: 'home' },
      { path: '/inicio/mis-tareas', label: 'Mis tareas', icon: 'check' },
      { path: '/inicio/aprobaciones', label: 'Aprobaciones', icon: 'inbox' },
    ],
  },
  {
    key: 'finanzas',
    label: 'Finanzas',
    items: [
      { path: '/finanzas/contabilidad', label: 'Contabilidad', icon: 'book' },
      { path: '/finanzas/tesoreria', label: 'Tesorería', icon: 'bank' },
      { path: '/finanzas/cuentas-por-pagar', label: 'Cuentas por pagar', icon: 'card' },
      { path: '/finanzas/cuentas-por-cobrar', label: 'Cuentas por cobrar', icon: 'receipt' },
      { path: '/finanzas/conciliacion', label: 'Conciliación', icon: 'refresh' },
      { path: '/finanzas/activos', label: 'Activos', icon: 'tag' },
    ],
  },
  {
    key: 'proyectos',
    label: 'Proyectos',
    items: [
      { path: '/proyectos', label: 'Proyectos', icon: 'project' },
      { path: '/proyectos/wbs', label: 'WBS', icon: 'grid' },
      { path: '/proyectos/presupuestos', label: 'Presupuestos', icon: 'ruler' },
      { path: '/proyectos/planeacion', label: 'Planeación', icon: 'calendar' },
      { path: '/proyectos/avances', label: 'Avances', icon: 'chart' },
      { path: '/proyectos/ordenes-de-cambio', label: 'Órdenes de cambio', icon: 'shuffle' },
      { path: '/proyectos/diario-de-obra', label: 'Diario de obra', icon: 'notebook' },
      { path: '/proyectos/calidad', label: 'Calidad', icon: 'shield' },
      { path: '/proyectos/seguridad', label: 'Seguridad', icon: 'shield' },
      { path: '/proyectos/rfi-submittals', label: 'RFI / Submittals', icon: 'file' },
    ],
  },
  {
    key: 'abastecimiento',
    label: 'Abastecimiento',
    items: [
      { path: '/abastecimiento/solicitudes', label: 'Solicitudes', icon: 'receipt' },
      { path: '/abastecimiento/rfq', label: 'RFQ', icon: 'send' },
      { path: '/abastecimiento/cotizaciones', label: 'Cotizaciones', icon: 'message' },
      { path: '/abastecimiento/comparativos', label: 'Comparativos', icon: 'scale' },
      { path: '/abastecimiento/ordenes-de-compra', label: 'Órdenes de compra', icon: 'package' },
      { path: '/abastecimiento/recepciones', label: 'Recepciones', icon: 'truck' },
      { path: '/abastecimiento/inventario', label: 'Inventario', icon: 'grid' },
      { path: '/abastecimiento/almacenes', label: 'Almacenes', icon: 'warehouse' },
      { path: '/abastecimiento/proveedores', label: 'Proveedores', icon: 'users' },
      { path: '/abastecimiento/contratos', label: 'Contratos', icon: 'file' },
    ],
  },
  {
    key: 'comercial',
    label: 'Comercial',
    items: [
      { path: '/comercial/leads', label: 'Leads', icon: 'target' },
      { path: '/comercial/oportunidades', label: 'Oportunidades', icon: 'briefcase' },
      { path: '/comercial/clientes', label: 'Clientes', icon: 'users' },
      { path: '/comercial/cotizaciones', label: 'Cotizaciones', icon: 'file' },
      { path: '/comercial/contratos', label: 'Contratos', icon: 'file' },
      { path: '/comercial/facturacion', label: 'Facturación', icon: 'receipt' },
      { path: '/comercial/cobros', label: 'Cobros', icon: 'bank' },
    ],
  },
  {
    key: 'recursos',
    label: 'Recursos',
    items: [
      { path: '/recursos/personal', label: 'Personal', icon: 'users' },
      { path: '/recursos/cuadrillas', label: 'Cuadrillas', icon: 'users' },
      { path: '/recursos/tiempo', label: 'Tiempo', icon: 'clock' },
      { path: '/recursos/equipos', label: 'Equipos', icon: 'equipment' },
      { path: '/recursos/combustible', label: 'Combustible', icon: 'fuel' },
      { path: '/recursos/mantenimiento', label: 'Mantenimiento', icon: 'tool' },
    ],
  },
  {
    key: 'control',
    label: 'Control',
    items: [
      { path: '/control/documentos', label: 'Documentos', icon: 'folder' },
      { path: '/control/evidencias', label: 'Evidencias', icon: 'camera' },
      { path: '/control/reportes', label: 'Reportes', icon: 'file' },
      { path: '/control/auditoria', label: 'Auditoría', icon: 'search' },
      { path: '/control/configuracion', label: 'Configuración', icon: 'settings' },
    ],
  },
]

export const navItems: NavItem[] = navGroups.flatMap((group) => group.items)
