import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  Input,
  LoadingState,
  Select,
} from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { useMutationError } from '../../hooks/useMutationError'
import { accessManagementService } from '../../services/accessManagementService'
import { masterDataService } from '../../services/masterDataService'

const ROLE_NAMES = [
  'Administrator',
  'Finance Manager',
  'Treasury Manager',
  'Accountant',
  'Project Manager',
  'Project Controller',
  'Procurement Manager',
  'Buyer',
  'Warehouse Manager',
  'Operations User',
  'Sales Manager',
  'Equipment Manager',
  'Auditor',
  'Viewer',
] as const

export function AccessManagementSettings() {
  const queryClient = useQueryClient()
  const handleMutationError = useMutationError()
  const { companies, activeCompanyId } = useActiveCompany()
  const [selectedUserId, setSelectedUserId] = useState('')
  const [form, setForm] = useState({ email: '', fullName: '', password: '', roleName: 'Viewer' })

  const usersQuery = useQuery({
    queryKey: ['master-data', 'users', activeCompanyId],
    queryFn: () => masterDataService.listUsers(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })
  const accessQuery = useQuery({
    queryKey: ['access-management', selectedUserId, activeCompanyId],
    queryFn: () => accessManagementService.getUserAccess(selectedUserId, activeCompanyId ?? undefined),
    enabled: Boolean(selectedUserId && activeCompanyId),
  })

  const createUser = useMutation({
    mutationFn: () => masterDataService.createUser({
      companyId: activeCompanyId as string,
      email: form.email.trim(),
      fullName: form.fullName.trim(),
      password: form.password,
      roleName: form.roleName,
    }),
    onSuccess: (user) => {
      setSelectedUserId(user.id)
      setForm({ email: '', fullName: '', password: '', roleName: 'Viewer' })
      queryClient.invalidateQueries({ queryKey: ['master-data', 'users', activeCompanyId] })
    },
    onError: (error) => handleMutationError(error, 'Crear usuario'),
  })

  const mutateAccess = useMutation({
    mutationFn: async ({ kind, id, assigned }: { kind: 'role' | 'company' | 'project'; id: string; assigned: boolean }) => {
      if (kind === 'role') {
        return assigned
          ? accessManagementService.revokeRole(selectedUserId, id)
          : accessManagementService.grantRole(selectedUserId, id)
      }
      if (kind === 'company') {
        return assigned
          ? accessManagementService.revokeCompany(selectedUserId, id)
          : accessManagementService.grantCompany(selectedUserId, id)
      }
      return assigned
        ? accessManagementService.revokeProject(selectedUserId, id)
        : accessManagementService.grantProject(selectedUserId, id)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['access-management', selectedUserId] })
      queryClient.invalidateQueries({ queryKey: ['master-data', 'users'] })
    },
    onError: (error) => handleMutationError(error, 'Modificar acceso'),
  })

  if (!activeCompanyId || companies.length === 0) {
    return (
      <Card title="Usuarios · Roles · Accesos">
        <EmptyState icon="users" title="Selecciona una compañía" description="La gestión de accesos requiere una compañía activa." />
      </Card>
    )
  }

  const users = usersQuery.data ?? []
  const access = accessQuery.data

  return (
    <section aria-labelledby="access-management-title">
      <header className="nx-page__header">
        <div>
          <p className="nx-page__eyebrow">Seguridad y aislamiento</p>
          <h2 id="access-management-title" className="nx-dashboard__title">Usuarios · Roles · Accesos</h2>
          <p className="nx-field__hint">
            El backend sigue siendo la autoridad. Los cambios de roles, compañías y proyectos requieren Protected Edit y quedan auditados.
          </p>
        </div>
      </header>

      <Card title="Crear usuario">
        <div className="nx-dashboard__kpi-grid">
          <Input label="Nombre completo" value={form.fullName} onChange={(event) => setForm({ ...form, fullName: event.target.value })} />
          <Input label="Correo" type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} />
          <Input label="Contraseña inicial" type="password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} />
          <Select label="Rol inicial" value={form.roleName} onChange={(event) => setForm({ ...form, roleName: event.target.value })}>
            {ROLE_NAMES.map((role) => <option key={role} value={role}>{role}</option>)}
          </Select>
        </div>
        <Button
          loading={createUser.isPending}
          disabled={!form.fullName.trim() || !form.email.trim() || form.password.length < 8}
          onClick={() => createUser.mutate()}
        >
          Crear usuario y asignar compañía
        </Button>
      </Card>

      <Card title="Administrar usuario existente">
        {usersQuery.isLoading ? <LoadingState label="Cargando usuarios…" /> : usersQuery.isError ? (
          <ErrorState description="No se pudo cargar el directorio de usuarios." onRetry={() => usersQuery.refetch()} />
        ) : (
          <Select label="Usuario" value={selectedUserId} onChange={(event) => setSelectedUserId(event.target.value)}>
            <option value="">Selecciona un usuario…</option>
            {users.map((user) => (
              <option key={user.id} value={user.id}>{user.fullName} — {user.email}</option>
            ))}
          </Select>
        )}
      </Card>

      {selectedUserId ? (
        accessQuery.isLoading ? <LoadingState label="Cargando roles y scopes…" /> : accessQuery.isError ? (
          <ErrorState description="No se pudieron cargar los accesos del usuario. Solo Administrator puede administrar scopes." onRetry={() => accessQuery.refetch()} />
        ) : access ? (
          <div className="nx-dashboard__kpi-grid">
            <AccessCard
              title="Roles"
              rows={access.roles.map((row) => ({ id: row.id, label: row.name, assigned: row.assigned }))}
              busy={mutateAccess.isPending}
              onToggle={(id, assigned) => mutateAccess.mutate({ kind: 'role', id, assigned })}
            />
            <AccessCard
              title="Compañías"
              rows={access.companies.map((row) => ({ id: row.id, label: row.name, assigned: row.assigned }))}
              busy={mutateAccess.isPending}
              onToggle={(id, assigned) => mutateAccess.mutate({ kind: 'company', id, assigned })}
            />
            <AccessCard
              title="Proyectos de la compañía activa"
              rows={access.projects.map((row) => ({
                id: row.id,
                label: `${row.code ? `${row.code} · ` : ''}${row.name}`,
                assigned: row.assigned,
              }))}
              busy={mutateAccess.isPending}
              empty="No hay proyectos reales en esta compañía."
              onToggle={(id, assigned) => mutateAccess.mutate({ kind: 'project', id, assigned })}
            />
          </div>
        ) : null
      ) : null}
    </section>
  )
}

function AccessCard({
  title,
  rows,
  busy,
  empty = 'No hay elementos disponibles.',
  onToggle,
}: {
  title: string
  rows: Array<{ id: string; label: string; assigned: boolean }>
  busy: boolean
  empty?: string
  onToggle: (id: string, assigned: boolean) => void
}) {
  return (
    <Card title={title}>
      {rows.length === 0 ? <p className="nx-field__hint">{empty}</p> : rows.map((row) => (
        <div key={row.id} className="nx-treasury__actions">
          <span>{row.label}</span>
          <Badge tone={row.assigned ? 'success' : 'neutral'}>{row.assigned ? 'Asignado' : 'Sin acceso'}</Badge>
          <Button variant="secondary" disabled={busy} onClick={() => onToggle(row.id, row.assigned)}>
            {row.assigned ? 'Retirar' : 'Asignar'}
          </Button>
        </div>
      ))}
    </Card>
  )
}