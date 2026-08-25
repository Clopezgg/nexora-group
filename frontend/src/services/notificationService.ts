import { apiFetch } from './httpClient'
import type { NotificationEntry } from '../types/notification'

export const notificationService = {
  list: (params: { unreadOnly?: boolean } = {}) => {
    const query = new URLSearchParams()
    if (params.unreadOnly) query.set('unreadOnly', 'true')
    const qs = query.toString()
    return apiFetch<NotificationEntry[]>(`/notifications${qs ? `?${qs}` : ''}`)
  },
  markRead: (notificationId: string) =>
    apiFetch<NotificationEntry>(`/notifications/${notificationId}/read`, {
      method: 'POST',
    }),
}
