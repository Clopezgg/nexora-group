import { useCallback, useMemo, useState, type ReactNode } from 'react'
import { ToastContext, type ToastItem, type ToastTone } from './toast-context'

const toneIcon: Record<ToastTone, string> = {
  success: '✓',
  warning: '!',
  danger: '✕',
  info: 'i',
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([])

  const push = useCallback((toast: Omit<ToastItem, 'id'>) => {
    const id = crypto.randomUUID()
    setToasts((current) => [...current, { ...toast, id }])
    window.setTimeout(() => {
      setToasts((current) => current.filter((item) => item.id !== id))
    }, 5000)
  }, [])

  const dismiss = (id: string) => setToasts((current) => current.filter((item) => item.id !== id))

  const value = useMemo(() => ({ push }), [push])

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="nx-toast-stack" role="region" aria-label="Notificaciones">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`nx-toast nx-toast--${toast.tone}`}
            role={toast.tone === 'danger' ? 'alert' : 'status'}
          >
            <span className="nx-toast__icon" aria-hidden="true">
              {toneIcon[toast.tone]}
            </span>
            <div className="nx-toast__body">
              <p className="nx-toast__title">{toast.title}</p>
              {toast.description ? <p className="nx-toast__description">{toast.description}</p> : null}
            </div>
            <button
              className="nx-toast__close"
              aria-label="Cerrar notificación"
              onClick={() => dismiss(toast.id)}
            >
              ✕
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

interface AlertProps {
  tone?: ToastTone
  title: string
  description?: string
  onDismiss?: () => void
}

export function Alert({ tone = 'info', title, description, onDismiss }: AlertProps) {
  return (
    <div className={`nx-alert nx-alert--${tone}`} role={tone === 'danger' ? 'alert' : 'status'}>
      <span className="nx-alert__icon" aria-hidden="true">
        {toneIcon[tone]}
      </span>
      <div className="nx-alert__body">
        <p className="nx-alert__title">{title}</p>
        {description ? <p className="nx-alert__description">{description}</p> : null}
      </div>
      {onDismiss ? (
        <button className="nx-toast__close" aria-label="Cerrar" onClick={onDismiss}>
          ✕
        </button>
      ) : null}
    </div>
  )
}
