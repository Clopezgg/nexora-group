import type { ReactNode } from 'react'
import { EmptyState } from '../../design-system'
import { useActiveContext } from '../context/useActiveContext'

interface RequiresActiveProjectProps {
  children: (activeProjectId: string) => ReactNode
}

/** Todas las pantallas de Project Control (WBS/Budget/ChangeOrders/Progress)
 * operan sobre el Active Project (ActiveUIContext) -- nunca sobre
 * OperationScope, que es un concepto de backend/dominio distinto (ver
 * CLAUDE.md §7). Si el usuario no tiene un proyecto activo seleccionado,
 * se le pide honestamente que vaya a elegir uno, sin datos fabricados. */
export function RequiresActiveProject({ children }: RequiresActiveProjectProps) {
  const { context, isLoading } = useActiveContext()

  if (isLoading) return null

  if (!context.activeProjectId) {
    return (
      <EmptyState
        icon="🏗️"
        title="Selecciona un proyecto activo"
        description="Ve a Proyectos y marca uno como activo para ver esta información."
      />
    )
  }

  return <>{children(context.activeProjectId)}</>
}
