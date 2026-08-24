interface SkeletonProps {
  width?: string
  height?: string
  radius?: 'sm' | 'md' | 'lg' | 'full'
  className?: string
}

export function Skeleton({ width = '100%', height = '16px', radius = 'sm', className }: SkeletonProps) {
  return (
    <span
      className={['nx-skeleton', `nx-skeleton--${radius}`, className].filter(Boolean).join(' ')}
      style={{ width, height }}
      aria-hidden="true"
    />
  )
}
