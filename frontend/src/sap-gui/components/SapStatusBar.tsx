import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '../../features/auth/auth-context'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { useActiveContext } from '../../features/context/useActiveContext'
import { fiscalService } from '../../services/fiscalService'
import { editAccessService } from '../../services/editAccessService'

const PERIOD_STATUS_LABEL: Record<string, string> = {
  OPEN: 'Abierto',
  SOFT_CLOSED: 'Cierre preliminar',
  CLOSED: 'Cerrado',
}

/**
 * Status bar enriquecida con contexto REAL: estado listo, compañía, proyecto
 * o vista empresa, período fiscal + estado del período, Protected Edit y
 * usuario. Nunca muestra información inventada; no muta nada.
 */
export function SapStatusBar() {
  const { user } = useAuth()
  const { activeCompany, activeCompanyId } = useActiveCompany()
  const { context } = useActiveContext()
  const [unlocked, setUnlocked] = useState(() => editAccessService.isUnlocked())

  useEffect(() => {
    const refresh = () => setUnlocked(editAccessService.isUnlocked())
    window.addEventListener('nexora:edit-access-changed', refresh)
    return () => window.removeEventListener('nexora:edit-access-changed', refresh)
  }, [])

  const fiscalQuery = useQuery({
    queryKey: ['fiscal', 'current', activeCompanyId],
    queryFn: () => fiscalService.getCurrent(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })
  const period = fiscalQuery.data?.period ?? null
  const fiscalYear = fiscalQuery.data?.fiscalYear ?? null
  const periodText = period
    ? `Período ${fiscalYear?.code ?? period.startDate.slice(0, 4)} · P${String(period.periodNumber).padStart(2, '0')} · ${PERIOD_STATUS_LABEL[period.status] ?? period.status}`
    : 'Período no configurado'

  return (
    <div className="nx-sap-statusbar" role="status" aria-label="Contexto SAP GUI" aria-live="polite">
      <span className="nx-sap-statusbar__ready" aria-label="Estado del sistema">Listo</span>
      <span>{activeCompany?.name ?? 'Empresa no seleccionada'}</span>
      <span>{context.activeProjectId ? 'Proyecto activo' : 'Vista empresa · sin proyecto'}</span>
      <span>{periodText}</span>
      <span>{unlocked ? 'Edición desbloqueada' : 'Edición bloqueada'}</span>
      <span>{user?.fullName ?? user?.email ?? 'Usuario'}</span>
    </div>
  )
}
