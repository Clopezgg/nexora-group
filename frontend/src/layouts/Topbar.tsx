import { useNavigate } from 'react-router-dom'
import { useAuth } from '../features/auth/auth-context'
import { useActiveContext } from '../features/context/useActiveContext'
import { Badge, Icon, IconButton, Select, Tooltip } from '../design-system'
import { NotificationBell } from '../components/NotificationBell'

interface TopbarProps {
  onOpenNav: () => void
}

export function Topbar({ onOpenNav }: TopbarProps) {
  const { user, logout } = useAuth()
  const { context, isLoading, setActiveProject } = useActiveContext()
  const navigate = useNavigate()
  const primaryRole = user?.roles?.[0]

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
          <span className="nx-topbar__company-name">Nexora Group</span>
        </div>
        <div className="nx-topbar__context">
          <span className="nx-topbar__context-label">Proyecto activo</span>
          <Select
            aria-label="Proyecto activo"
            value={context.activeProjectId ?? ''}
            disabled={isLoading}
            onChange={(event) => setActiveProject(event.target.value || null)}
          >
            <option value="">Vista general (sin proyecto)</option>
            {context.activeProjectId && context.activeProjectName ? (
              <option value={context.activeProjectId}>{context.activeProjectName}</option>
            ) : null}
          </Select>
        </div>
        <Tooltip label="El período fiscal no está configurado para esta instancia">
          <Badge tone="neutral">Período: no configurado</Badge>
        </Tooltip>
      </div>

      <div className="nx-topbar__right">
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
          <button className="nx-topbar__logout" onClick={logout}>
            Cerrar sesión
          </button>
        </div>
      </div>
    </header>
  )
}
