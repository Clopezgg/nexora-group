/**
 * Tipos compartidos de la workstation SAP GUI.
 * La workstation es COMPOSICIÓN DE PRESENTACIÓN: reutiliza Outlet, rutas,
 * permisos, compañía/proyecto activos, período fiscal, Protected Edit,
 * usuario, notifications, command palette y globalSearch. No duplica
 * Router, auth, permisos ni lógica de negocio (ORDEN MAESTRA §9).
 */
import type { NavGroup } from '../../app/navigation'
import type { CommandItem } from '../../design-system'

export interface SapWorkstationProps {
  onOpenNav: () => void
}

export interface SapTreeProps {
  /** 'sidebar' = árbol completo desktop; 'drawer' = variante drawer móvil. */
  variant?: 'sidebar' | 'drawer'
  onNavigate?: () => void
}

export interface SapCommandBarProps {
  items: CommandItem[]
  searchRemote?: (query: string) => Promise<CommandItem[]>
}

export interface SapMenuBarProps {
  groups: NavGroup[]
  onOpenSearch: () => void
  onOpenNav: () => void
}

export interface SapScreenFrameProps {
  groups: NavGroup[]
}

export type { NavGroup, CommandItem }
