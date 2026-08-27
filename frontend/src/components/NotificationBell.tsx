import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Badge, Icon, IconButton } from '../design-system'
import { notificationService } from '../services/notificationService'
import './NotificationBell.css'

const IDLE_POLL_INTERVAL_MS = 60000
const OPEN_POLL_INTERVAL_MS = 15000

export function NotificationBell() {
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)
  const queryClient = useQueryClient()

  const notificationsQuery = useQuery({
    queryKey: ['notifications'],
    queryFn: () => notificationService.list(),
    // Poll less aggressively while the panel is closed so background traffic
    // does not compete with interactive finance/project requests. When the
    // user is actively viewing notifications, keep the panel fresher.
    refetchInterval: open ? OPEN_POLL_INTERVAL_MS : IDLE_POLL_INTERVAL_MS,
    refetchIntervalInBackground: false,
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

  const notifications = Array.isArray(notificationsQuery.data) ? notificationsQuery.data : []
  const unreadCount = notifications.filter((note) => note.readAt === null).length

  return (
    <div className="nx-notification-bell" ref={rootRef}>
      <div className="nx-notification-bell__trigger-wrap">
        <IconButton
          label={unreadCount > 0 ? `Notificaciones (${unreadCount} sin leer)` : 'Notificaciones'}
          icon={<Icon name="bell" />}
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
