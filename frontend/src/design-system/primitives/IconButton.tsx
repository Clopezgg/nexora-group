import type { ButtonHTMLAttributes, ReactNode } from 'react'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger'

interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  label: string
  icon: ReactNode
  active?: boolean
}

export function IconButton({
  variant = 'ghost',
  label,
  icon,
  active = false,
  className,
  ...rest
}: IconButtonProps) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      className={[
        'nx-icon-button',
        `nx-icon-button--${variant}`,
        active ? 'nx-icon-button--active' : '',
        className,
      ]
        .filter(Boolean)
        .join(' ')}
      {...rest}
    >
      <span aria-hidden="true">{icon}</span>
    </button>
  )
}
