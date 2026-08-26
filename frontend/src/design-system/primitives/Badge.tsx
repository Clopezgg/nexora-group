import type { ReactNode } from 'react'

type Tone = 'neutral' | 'success' | 'warning' | 'danger' | 'info'

export function Badge({ tone = 'neutral', children }: { tone?: Tone; children: ReactNode }) {
  return <span className={`nx-badge nx-badge--${tone}`}>{children}</span>
}
