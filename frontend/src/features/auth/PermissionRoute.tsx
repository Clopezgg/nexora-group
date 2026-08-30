import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from './auth-context'

export function PermissionRoute({ requiredAny }: { requiredAny: string[] }) {
  const { user } = useAuth()
  const permissions = new Set(user?.permissions ?? [])

  // Administrator is the canonical all-access role in the backend. Keep the
  // route guard aligned with that contract even while the permission list is
  // being refreshed or an older authenticated session has no expanded grants.
  if (user?.roles.includes('Administrator')) {
    return <Outlet />
  }

  if (!requiredAny.some((permission) => permissions.has(permission))) {
    return <Navigate to="/inicio" replace />
  }

  return <Outlet />
}
