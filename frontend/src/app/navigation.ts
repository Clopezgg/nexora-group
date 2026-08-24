export interface NavItem {
  path: string
  label: string
  icon: string
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
      { path: '/inicio', label: 'Inicio', icon: '🏠' },
      { path: '/inicio/mis-tareas', label: 'Mis tareas', icon: '✅' },
      { path: '/inicio/aprobaciones', label: 'Aprobaciones', icon: '📥' },
    ],
  },
  {
    key: 'finanzas',
    label: 'Finanzas',
    items: [
      { path: '/finanzas/contabilidad', label: 'Contabilidad', icon: '📗' },
      { path: '/finanzas/tesoreria', label: 'Tesorería', icon: '🏦' },
      { path: '/finanzas/cuentas-por-pagar', label: 'Cuentas por pagar', icon: '💳' },
      { path: '/finanzas/cuentas-por-cobrar', label: 'Cuentas por cobrar', icon: '🧾' },
      { path: '/finanzas/conciliacion', label: 'Conciliación', icon: '🔁' },
      { path: '/finanzas/activos', label: 'Activos', icon: '🏷️' },
    ],
  },
  {
    key: 'proyectos',
    label: 'Proyectos',
    items: [
      { path: '/proyectos', label: 'Proyectos', icon: '🏗️' },
      { path: '/proyectos/wbs', label: 'WBS', icon: '🧩' },
      { path: '/proyectos/presupuestos', label: 'Presupuestos', icon: '📐' },
      { path: '/proyectos/planeacion', label: 'Planeación', icon: '🗓️' },
      { path: '/proyectos/avances', label: 'Avances', icon: '📈' },
      { path: '/proyectos/ordenes-de-cambio', label: 'Órdenes de cambio', icon: '🔀' },
      { path: '/proyectos/diario-de-obra', label: 'Diario de obra', icon: '📔' },
      { path: '/proyectos/calidad', label: 'Calidad', icon: '🛡️' },
      { path: '/proyectos/rfi-submittals', label: 'RFI / Submittals', icon: '📝' },
    ],
  },
  {
    key: 'abastecimiento',
    label: 'Abastecimiento',
    items: [
      { path: '/abastecimiento/solicitudes', label: 'Solicitudes', icon: '🧾' },
      { path: '/abastecimiento/rfq', label: 'RFQ', icon: '📨' },
      { path: '/abastecimiento/cotizaciones', label: 'Cotizaciones', icon: '💬' },
      { path: '/abastecimiento/comparativos', label: 'Comparativos', icon: '⚖️' },
      { path: '/abastecimiento/ordenes-de-compra', label: 'Órdenes de compra', icon: '📦' },
      { path: '/abastecimiento/recepciones', label: 'Recepciones', icon: '🚚' },
      { path: '/abastecimiento/inventario', label: 'Inventario', icon: '📊' },
      { path: '/abastecimiento/almacenes', label: 'Almacenes', icon: '🏭' },
      { path: '/abastecimiento/proveedores', label: 'Proveedores', icon: '🤝' },
      { path: '/abastecimiento/contratos', label: 'Contratos', icon: '📃' },
    ],
  },
  {
    key: 'comercial',
    label: 'Comercial',
    items: [
      { path: '/comercial/leads', label: 'Leads', icon: '🎯' },
      { path: '/comercial/oportunidades', label: 'Oportunidades', icon: '💼' },
      { path: '/comercial/clientes', label: 'Clientes', icon: '👥' },
      { path: '/comercial/cotizaciones', label: 'Cotizaciones', icon: '📄' },
      { path: '/comercial/contratos', label: 'Contratos', icon: '✍️' },
      { path: '/comercial/facturacion', label: 'Facturación', icon: '🧮' },
      { path: '/comercial/cobros', label: 'Cobros', icon: '💰' },
    ],
  },
  {
    key: 'recursos',
    label: 'Recursos',
    items: [
      { path: '/recursos/personal', label: 'Personal', icon: '🧑‍💼' },
      { path: '/recursos/cuadrillas', label: 'Cuadrillas', icon: '👷' },
      { path: '/recursos/tiempo', label: 'Tiempo', icon: '⏱️' },
      { path: '/recursos/equipos', label: 'Equipos', icon: '🚜' },
      { path: '/recursos/combustible', label: 'Combustible', icon: '⛽' },
      { path: '/recursos/mantenimiento', label: 'Mantenimiento', icon: '🔧' },
    ],
  },
  {
    key: 'control',
    label: 'Control',
    items: [
      { path: '/control/documentos', label: 'Documentos', icon: '🗂️' },
      { path: '/control/evidencias', label: 'Evidencias', icon: '📸' },
      { path: '/control/reportes', label: 'Reportes', icon: '📑' },
      { path: '/control/auditoria', label: 'Auditoría', icon: '🔍' },
      { path: '/control/configuracion', label: 'Configuración', icon: '🛠️' },
    ],
  },
]

export const navItems: NavItem[] = navGroups.flatMap((group) => group.items)
