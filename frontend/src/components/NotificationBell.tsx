import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Badge, IconButton } from '../design-system'
import { notificationService } from '../services/notificationService'
import './NotificationBell.css'

const POLL_INTERVAL_MS = 30000

export function NotificationBell() {
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)
  const queryClient = useQueryClient()

  // Se consulta la lista completa (no solo unreadOnly) para poder mostrar
  // notificaciones recientes ya leídas en el dropdown; el badge de conteo
  // se calcula filtrando localmente por `readAt == null` sobre la misma
  // respuesta -- una sola query real, sin duplicar el polling.
  const notificationsQuery = useQuery({
    queryKey: ['notifications'],
    queryFn: () => notificationService.list(),
    refetchInterval: POLL_INTERVAL_MS,
  })

  const markReadMutation = useMutation({
    mutationFn: (notificationId: string) => notificationService.markRead(notificationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
    },
  })

  useEffect(() => {
    function onClickOutside(event: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) {
        setOpen(false)
      }
    }
    function onEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onClickOutside)
    document.addEventListener('keydown', onEscape)
    return () => {
      document.removeEventListener('mousedown', onClickOutside)
      document.removeEventListener('keydown', onEscape)
    }
  }, [])

  // Defensivo: en producción la API siempre responde con un array (ver
  // app/api/routes/notifications.py::list_my_notifications), pero algunos
  // tests de otras páginas usan un stub de fetch genérico que no conoce
  // esta ruta y cae en su fallback `{}` -- no se debe romper toda la app
  // por eso.
  const notifications = Array.isArray(notificationsQuery.data) ? notificationsQuery.data : []
  const unreadCount = notifications.filter((note) => note.readAt === null).length

  return (
    <div className="nx-notification-bell" ref={rootRef}>
      <div className="nx-notification-bell__trigger-wrap">
        <IconButton
          label={unreadCount > 0 ? `Notificaciones (${unreadCount} sin leer)` : 'Notificaciones'}
          icon="🔔"
          active={open}
          onClick={() => setOpen((current) => !current)}
        />
        {unreadCount > 0 ? (
          <span className="nx-notification-bell__badge" aria-hidden="true">
            <Badge tone="danger">{unreadCount > 9 ? '9+' : unreadCount}</Badge>
          </span>
        ) : null}
      </div>

      {open ? (
        <div className="nx-notification-bell__panel" role="dialog" aria-label="Notificaciones">
          <div className="nx-notification-bell__panel-header">Notificaciones</div>
          {notificationsQuery.isLoading ? (
            <div className="nx-notification-bell__empty">Cargando…</div>
          ) : notifications.length === 0 ? (
            <div className="nx-notification-bell__empty">No tienes notificaciones todavía.</div>
          ) : (
            <ul className="nx-notification-bell__list">
              {notifications.map((note) => (
                <li
                  key={note.id}
                  className={
                    note.readAt === null
                      ? 'nx-notification-bell__item nx-notification-bell__item--unread'
                      : 'nx-notification-bell__item'
                  }
                >
                  <div className="nx-notification-bell__item-title">{note.title}</div>
                  <div className="nx-notification-bell__item-body">{note.body}</div>
                  <div className="nx-notification-bell__item-footer">
                    <span className="nx-notification-bell__item-date">
                      {new Date(note.createdAt).toLocaleString('es-HN')}
                    </span>
                    {note.readAt === null ? (
                      <button
                        type="button"
                        className="nx-notification-bell__mark-read"
                        disabled={markReadMutation.isPending}
                        onClick={() => markReadMutation.mutate(note.id)}
                      >
                        Marcar como leída
                      </button>
                    ) : null}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
    </div>
  )
}
