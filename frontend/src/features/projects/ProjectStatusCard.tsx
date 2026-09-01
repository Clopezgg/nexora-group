import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Badge, Button, Card, LoadingState, Textarea } from '../../design-system'
import { projectService } from '../../services/projectService'
import type { Project, ProjectAllowedTransition, ProjectStatus } from '../../types/project'
import { projectStatusLabel } from '../../utils/statusLabels'

const TONE: Record<string, 'neutral' | 'info' | 'warning' | 'danger' | 'success'> = {
  PLANNING: 'neutral',
  ACTIVE: 'success',
  ON_HOLD: 'warning',
  COMPLETED: 'info',
  CLOSED: 'neutral',
  CANCELLED: 'danger',
  ARCHIVED: 'neutral',
}

const ACTION_VERB: Partial<Record<ProjectStatus, string>> = {
  ACTIVE: 'Activar / Reanudar',
  ON_HOLD: 'Pausar',
  COMPLETED: 'Completar',
  CLOSED: 'Cerrar administrativamente',
  CANCELLED: 'Cancelar proyecto',
  ARCHIVED: 'Archivar / Eliminar',
  PLANNING: 'Devolver a planificación',
}

/**
 * Sección "Estado del proyecto" del Project Cockpit (CORRECTIVA §5/§6/§27).
 * Las acciones vienen del backend (`GET /projects/{id}/lifecycle`) — este
 * componente NO tiene su propio grafo de transiciones. Tras una transición
 * exitosa reemplaza el proyecto en caché de inmediato: nunca quedan botones del
 * estado viejo.
 */
export function ProjectStatusCard({
  project,
  onUpdated,
}: {
  project: Project
  onUpdated?: (updated: Project) => void
}) {
  const queryClient = useQueryClient()
  const [pendingTransition, setPendingTransition] = useState<ProjectAllowedTransition | null>(null)
  const [reason, setReason] = useState('')

  const lifecycleQuery = useQuery({
    queryKey: ['project', project.id, 'lifecycle'],
    queryFn: () => projectService.getLifecycle(project.id),
  })

  const mutation = useMutation({
    mutationFn: ({ status, reason: r }: { status: ProjectStatus; reason?: string }) =>
      projectService.transitionStatus(project.id, status, r),
    onSuccess: (updated) => {
      queryClient.setQueryData(['project', project.id], updated)
      queryClient.setQueriesData<Project[]>({ queryKey: ['projects'] }, (rows) =>
        Array.isArray(rows) ? rows.map((row) => (row.id === updated.id ? updated : row)) : rows,
      )
      queryClient.invalidateQueries({ queryKey: ['project', project.id, 'lifecycle'] })
      queryClient.invalidateQueries({ queryKey: ['project', project.id, 'financial-summary'] })
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard', 'summary'] })
      setPendingTransition(null)
      setReason('')
      onUpdated?.(updated)
    },
  })

  const lifecycle = lifecycleQuery.data
  const busy = mutation.isPending
  const currentLabel = lifecycle?.currentStatusLabel ?? projectStatusLabel(project.status)

  const run = (t: ProjectAllowedTransition) => {
    if (t.sensitive) {
      setPendingTransition(t)
      setReason('')
      return
    }
    mutation.mutate({ status: t.status })
  }

  return (
    <Card title="Estado del proyecto">
      <p className="nx-object-header__facts" style={{ marginBottom: 12 }}>
        <span>
          Estado actual:{' '}
          <Badge tone={TONE[project.status] ?? 'neutral'}>{currentLabel}</Badge>
        </span>
      </p>

      {lifecycle && (lifecycle.completedAt || lifecycle.closedAt || lifecycle.reopenedAt || lifecycle.archivedAt) ? (
        <dl className="nx-voucher-preview">
          {lifecycle.completedAt ? <div><dt>Completado</dt><dd>{lifecycle.completedAt}</dd></div> : null}
          {lifecycle.closedAt ? <div><dt>Cerrado</dt><dd>{lifecycle.closedAt}</dd></div> : null}
          {lifecycle.reopenedAt ? <div><dt>Reabierto</dt><dd>{lifecycle.reopenedAt}</dd></div> : null}
          {lifecycle.archivedAt ? <div><dt>Archivado</dt><dd>{lifecycle.archivedAt}</dd></div> : null}
        </dl>
      ) : null}

      {lifecycleQuery.isLoading ? (
        <LoadingState label="Cargando acciones…" />
      ) : (
        <>
          <p className="nx-field__label">Acciones permitidas</p>
          <div className="nx-treasury__actions">
            {(lifecycle?.allowedTransitions ?? []).map((t) => (
              <Button
                key={t.status}
                variant={t.status === 'CANCELLED' || t.status === 'ARCHIVED' ? 'ghost' : 'secondary'}
                loading={busy}
                disabled={busy}
                onClick={() => run(t)}
              >
                {ACTION_VERB[t.status] ?? `Pasar a ${t.label}`}
                {t.sensitive ? ' …' : ''}
              </Button>
            ))}
            {(lifecycle?.allowedTransitions ?? []).length === 0 ? (
              <span className="nx-field__hint">No hay acciones de ciclo de vida disponibles.</span>
            ) : null}
          </div>
        </>
      )}

      {mutation.isError && !pendingTransition ? (
        <p className="nx-field__error" role="alert">{(mutation.error as Error).message}</p>
      ) : null}

      {pendingTransition ? (
        <form
          className="nx-inline-form"
          onSubmit={(event) => {
            event.preventDefault()
            if (reason.trim().length >= 10) {
              mutation.mutate({ status: pendingTransition.status, reason: reason.trim() })
            }
          }}
        >
          <p className="nx-field__label">
            {ACTION_VERB[pendingTransition.status] ?? pendingTransition.label} — motivo obligatorio
          </p>
          <Textarea
            label="Motivo (mínimo 10 caracteres, queda en auditoría)"
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            required
          />
          <div className="nx-treasury__actions">
            <Button type="submit" loading={busy} disabled={busy || reason.trim().length < 10}>
              Confirmar
            </Button>
            <Button type="button" variant="ghost" onClick={() => { setPendingTransition(null); setReason('') }}>
              Cancelar
            </Button>
          </div>
          {mutation.isError ? (
            <p className="nx-field__error" role="alert">{(mutation.error as Error).message}</p>
          ) : null}
        </form>
      ) : null}
    </Card>
  )
}
