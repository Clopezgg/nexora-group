import type { ReactNode } from 'react'

interface ModalProps {
  open: boolean
  title: string
  onClose: () => void
  children: ReactNode
}

export function Modal({ open, title, onClose, children }: ModalProps) {
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
