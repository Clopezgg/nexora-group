import type { ReactNode } from 'react'

interface ModalProps {
  open: boolean
  title: string
  onClose: () => void
  children: ReactNode
  /** `wide` da más ancho para tablas financieras (§44). */
  size?: 'default' | 'wide'
}

export function Modal({ open, title, onClose, children, size = 'default' }: ModalProps) {
  if (!open) return null
  return (
    <div
      className="nx-modal__overlay"
      role="presentation"
      onClick={onClose}
      style={{ padding: '16px', overflowY: 'auto', boxSizing: 'border-box' }}
    >
      <div
        className="nx-modal"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(event) => event.stopPropagation()}
        style={{
          maxHeight: 'calc(100dvh - 32px)',
          overflowY: 'auto',
          boxSizing: 'border-box',
          ...(size === 'wide' ? { width: 'min(1040px, 100%)', maxWidth: 'min(1040px, 100%)' } : {}),
        }}
      >
        <div className="nx-modal__header">
          <h2 className="nx-modal__title">{title}</h2>
          <button className="nx-modal__close" onClick={onClose} aria-label="Cerrar">
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}
