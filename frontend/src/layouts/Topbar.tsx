import { useEffect, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../features/auth/auth-context'
import { useActiveContext } from '../features/context/useActiveContext'
import { Badge, Icon, IconButton, Select, Tooltip } from '../design-system'
import { EditAccessControl } from '../components/EditAccessControl'
import { NotificationBell } from '../components/NotificationBell'
import { useActiveCompany } from '../hooks/useActiveCompany'
import { projectService } from '../services/projectService'
import { fiscalService } from '../services/fiscalService'

interface TopbarProps {
  onOpenNav: () => void
}

const PERIOD_STATUS_LABEL: Record<string, string> = {
  OPEN: 'Abierto',
  SOFT_CLOSED: 'Cierre preliminar',
  CLOSED: 'Cerrado',
}

export function Topbar({ onOpenNav }: TopbarProps) {
  const { user, logout } = useAuth()
  const { context, isLoading: contextLoading, setActiveProject } = useActiveContext()
  const { companies, activeCompany, activeCompanyId, setActiveCompanyId, isLoading: companyLoading } = useActiveCompany()
  const navigate = useNavigate()
  const primaryRole = user?.roles?.[0]

  const projectsQuery = useQuery({
    queryKey: ['projects', activeCompanyId],
    queryFn: () => projectService.list(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })
  const fiscalQuery = useQuery({
    queryKey: ['fiscal', 'current', activeCompanyId],
    queryFn: () => fiscalService.getCurrent(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  const projects = useMemo(
    () => (Array.isArray(projectsQuery.data) ? projectsQuery.data : []),
    [projectsQuery.data],
  )
  useEffect(() => {
    if (!projectsQuery.isSuccess || !context.activeProjectId) return
    if (!projects.some((project) => project.id === context.activeProjectId)) {
      setActiveProject(null)
    }
  }, [context.activeProjectId, projects, projectsQuery.isSuccess, setActiveProject])

  const currentPeriod = fiscalQuery.data?.period ?? null
  const fiscalYear = fiscalQuery.data?.fiscalYear ?? null
  const periodText = currentPeriod
    ? `${fiscalYear?.code ?? currentPeriod.startDate.slice(0, 4)} · P${String(currentPeriod.periodNumber).padStart(2, '0')} · ${PERIOD_STATUS_LABEL[currentPeriod.status] ?? currentPeriod.status}`
    : 'Período no configurado'

  return (
    <header className="nx-topbar">
      <div className="nx-topbar__left">
        <IconButton
          label="Abrir navegación"
          icon={<Icon name="menu" />}
          className="nx-topbar__nav-toggle"
          onClick={onOpenNav}
        />
        <div className="nx-topbar__company" title="Empresa activa">
          {companies.length > 1 ? (
            <Select
              aria-label="Empresa activa"
              value={activeCompanyId ?? ''}
              disabled={companyLoading}
              onChange={(event) => setActiveCompanyId(event.target.value || null)}
            >
              {companies.map((company) => (
                <option key={company.id} value={company.id}>
                  {company.name}
                </option>
              ))}
            </Select>
          ) : (
            <span className="nx-topbar__company-name">{activeCompany?.name ?? 'NEXORA GROUP'}</span>
          )}
        </div>
        <div className="nx-topbar__context">
          <span className="nx-topbar__context-label">Proyecto activo</span>
          <Select
            aria-label="Proyecto seleccionado"
            value={context.activeProjectId ?? ''}
            disabled={contextLoading || projectsQuery.isLoading || !activeCompanyId}
            onChange={(event) => setActiveProject(event.target.value || null)}
          >
            <option value="">Vista empresa · sin proyecto</option>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.code ? `${project.code} · ` : ''}{project.name}
              </option>
            ))}
          </Select>
        </div>
        <Tooltip
          label={
            currentPeriod
              ? `${currentPeriod.startDate} → ${currentPeriod.endDate}`
              : 'Configura un año y sus períodos fiscales en Configuración.'
          }
        >
          <Badge tone={currentPeriod?.status === 'CLOSED' ? 'warning' : 'neutral'}>{periodText}</Badge>
        </Tooltip>
      </div>

      <div className="nx-topbar__right">
        <EditAccessControl />
        <Tooltip label="Búsqueda global (Cmd/Ctrl + K)">
          <IconButton
            label="Búsqueda global"
            icon={<Icon name="search" />}
            onClick={() => {
              document.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', metaKey: true }))
            }}
          />
        </Tooltip>
        <Tooltip label="Abrir aprobaciones pendientes">
          <IconButton
            label="Aprobaciones"
            icon={<Icon name="inbox" />}
            onClick={() => navigate('/inicio/aprobaciones')}
          />
        </Tooltip>
        <NotificationBell />
        <div className="nx-topbar__user">
          <div className="nx-topbar__user-info">
            <span className="nx-topbar__user-name">{user?.fullName ?? user?.email}</span>
            {primaryRole ? <span className="nx-topbar__user-role">{primaryRole}</span> : null}
          </div>
          <button className="nx-topbar__logout" aria-label="Cerrar sesión" onClick={logout}>
            Salir
          </button>
        </div>
      </div>
    </header>
  )
}
