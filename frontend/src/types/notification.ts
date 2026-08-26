export interface NotificationEntry {
  id: string
  recipientUserId: string
  type: string
  title: string
  body: string
  entityType: string | null
  entityId: string | null
  readAt: string | null
  createdAt: string
}
