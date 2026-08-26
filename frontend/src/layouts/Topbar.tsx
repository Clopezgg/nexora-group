import { useAuth } from '../features/auth/auth-context'
import { useActiveContext } from '../features/context/useActiveContext'
import { Badge, IconButton, Select, Tooltip } from '../design-system'
import { NotificationBell } from '../components/NotificationBell'

interface TopbarProps {
  onOpenNav: () => void
}

export function Topbar({ onOpenNav }: TopbarProps) {
  const { user, logout } = useAuth()
  const { context, isLoading, setActiveProject } = useActiveContext()
  const primaryRole = user?.roles?.[0]

  return (
    <header className="nx-topbar">
      <div className="nx-topbar__left">
        <IconButton
          label="Abrir navegación"
          icon="☰"
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
        <Tooltip label="El periodo fiscal aún no está configurado (NXR-REQ-0004)">
          <Badge tone="neutral">Periodo: no configurado</Badge>
        </Tooltip>
      </div>

      <div className="nx-topbar__right">
        <Tooltip label="Búsqueda global (Cmd/Ctrl + K)">
          <IconButton
            label="Búsqueda global"
            icon="🔍"
            onClick={() => {
              document.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', metaKey: true }))
            }}
          />
        </Tooltip>
        <Tooltip label="Aprobaciones — se activará con el motor de workflow (NXR-REQ-0088)">
          <IconButton label="Aprobaciones" icon="📥" disabled />
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
