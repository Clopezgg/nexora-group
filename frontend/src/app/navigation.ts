export interface NavItem {
  path: string
  label: string
  icon: string
}

export const navItems: NavItem[] = [
  { path: '/dashboard', label: 'Dashboard', icon: '📊' },
  { path: '/operaciones', label: 'Operaciones', icon: '⚙️' },
  { path: '/tesoreria-central', label: 'Tesorería Central', icon: '🏦' },
  { path: '/proyectos', label: 'Proyectos', icon: '🏗️' },
  { path: '/presupuestos', label: 'Presupuestos', icon: '📐' },
  { path: '/evidencias', label: 'Evidencias', icon: '🧾' },
  { path: '/avances', label: 'Avances', icon: '📈' },
  { path: '/proveedores', label: 'Proveedores', icon: '🤝' },
  { path: '/cuentas-por-pagar', label: 'Cuentas por pagar', icon: '💳' },
  { path: '/reportes', label: 'Reportes', icon: '📑' },
  { path: '/auditoria', label: 'Auditoría', icon: '🔍' },
  { path: '/configuracion', label: 'Configuración', icon: '🛠️' },
]
