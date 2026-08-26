import type { ReactNode } from 'react'

interface CardProps {
  title?: string
  value?: ReactNode
  children?: ReactNode
  className?: string
}

export function Card({ title, value, children, className }: CardProps) {
  return (
    <div className={['nx-card', className].filter(Boolean).join(' ')}>
      {title ? <p className="nx-card__title">{title}</p> : null}
      {value !== undefined ? <p className="nx-card__value">{value}</p> : null}
      {children}
    </div>
  )
}
