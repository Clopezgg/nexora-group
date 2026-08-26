import type { ButtonHTMLAttributes, ReactNode } from 'react'
import './Button.css'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  loading?: boolean
  children: ReactNode
}

export function Button({
  variant = 'primary',
  loading = false,
  disabled,
  children,
  className,
  ...rest
}: ButtonProps) {
  return (
    <button
      className={['nx-button', `nx-button--${variant}`, className].filter(Boolean).join(' ')}
      disabled={disabled || loading}
      aria-busy={loading}
      {...rest}
    >
      {loading ? <span className="nx-button__spinner" aria-hidden="true" /> : null}
      <span className="nx-button__label">{children}</span>
    </button>
  )
}
