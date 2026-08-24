import { useAuth } from '../features/auth/auth-context'
import { useActiveContext } from '../features/context/useActiveContext'
import { Select } from '../design-system'

export function Topbar() {
  const { user, logout } = useAuth()
  const { context, isLoading, setActiveProject } = useActiveContext()

  return (
    <header className="nx-topbar">
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
      <div className="nx-topbar__user">
        <span className="nx-topbar__user-name">{user?.fullName ?? user?.email}</span>
        <button className="nx-topbar__logout" onClick={logout}>
          Cerrar sesión
        </button>
      </div>
    </header>
  )
}
