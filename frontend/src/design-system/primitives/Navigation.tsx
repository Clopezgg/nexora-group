import { useId, useRef, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'

export interface BreadcrumbItem {
  label: string
  to?: string
}

export function Breadcrumb({ items }: { items: BreadcrumbItem[] }) {
  return (
    <nav aria-label="Breadcrumb" className="nx-breadcrumb">
      <ol>
        {items.map((item, index) => {
          const isLast = index === items.length - 1
          return (
            <li key={`${item.label}-${index}`}>
              {item.to && !isLast ? (
                <Link to={item.to}>{item.label}</Link>
              ) : (
                <span aria-current={isLast ? 'page' : undefined}>{item.label}</span>
              )}
              {!isLast ? (
                <span className="nx-breadcrumb__sep" aria-hidden="true">
                  /
                </span>
              ) : null}
            </li>
          )
        })}
      </ol>
    </nav>
  )
}

export interface StepperStep {
  label: string
  status: 'complete' | 'current' | 'upcoming'
}

export function Stepper({ steps }: { steps: StepperStep[] }) {
  return (
    <ol className="nx-stepper">
      {steps.map((step, index) => (
        <li key={step.label} className={`nx-stepper__step nx-stepper__step--${step.status}`}>
          <span className="nx-stepper__index" aria-hidden="true">
            {step.status === 'complete' ? '✓' : index + 1}
          </span>
          <span className="nx-stepper__label">{step.label}</span>
        </li>
      ))}
    </ol>
  )
}

export interface TimelineEvent {
  id: string
  title: string
  timestamp: string
  description?: string
  actor?: string
}

export function Timeline({ events }: { events: TimelineEvent[] }) {
  if (events.length === 0) {
    return <p className="nx-field__label">Sin actividad registrada todavía.</p>
  }
  return (
    <ol className="nx-timeline">
      {events.map((event) => (
        <li key={event.id} className="nx-timeline__item">
          <span className="nx-timeline__dot" aria-hidden="true" />
          <div>
            <p className="nx-timeline__title">{event.title}</p>
            <p className="nx-timeline__meta">
              {event.timestamp}
              {event.actor ? ` · ${event.actor}` : ''}
            </p>
            {event.description ? <p className="nx-timeline__description">{event.description}</p> : null}
          </div>
        </li>
      ))}
    </ol>
  )
}

export interface TabItem {
  key: string
  label: string
  content: ReactNode
  disabled?: boolean
}

export function Tabs({
  items,
  defaultKey,
  activeKey,
  onChange,
}: {
  items: TabItem[]
  defaultKey?: string
  /** Modo controlado: si se pasa, `Tabs` no guarda estado propio. */
  activeKey?: string
  onChange?: (key: string) => void
}) {
  const instanceId = useId()
  const tabRefs = useRef(new Map<string, HTMLButtonElement>())
  const enabledItems = items.filter((item) => !item.disabled)
  const [internalActive, setInternalActive] = useState(defaultKey ?? enabledItems[0]?.key)
  const requestedActive = activeKey ?? internalActive
  const active = enabledItems.some((item) => item.key === requestedActive)
    ? requestedActive
    : enabledItems[0]?.key
  const tabId = (key: string) => `${instanceId}-tab-${key}`
  const setActive = (key: string) => {
    if (activeKey === undefined) setInternalActive(key)
    onChange?.(key)
  }
  const activeItem = items.find((item) => item.key === active)
  return (
    <div className="nx-tabs" style={{ minWidth: 0, maxWidth: '100%' }}>
      <div
        role="tablist"
        className="nx-tabs__list"
        style={{ overflowX: 'auto', maxWidth: '100%', scrollbarWidth: 'thin' }}
      >
        {items.map((item) => (
          <button
            key={item.key}
            role="tab"
            id={tabId(item.key)}
            ref={(node) => {
              if (node) tabRefs.current.set(item.key, node)
              else tabRefs.current.delete(item.key)
            }}
            aria-controls={`${instanceId}-panel`}
            tabIndex={active === item.key ? 0 : -1}
            disabled={item.disabled}
            type="button"
            aria-selected={active === item.key}
            className={['nx-tabs__tab', active === item.key ? 'nx-tabs__tab--active' : '']
              .filter(Boolean)
              .join(' ')}
            style={{ flex: '0 0 auto', whiteSpace: 'nowrap' }}
            onClick={() => setActive(item.key)}
            onKeyDown={(event) => {
              const index = enabledItems.findIndex((tab) => tab.key === item.key)
              let nextIndex: number
              switch (event.key) {
                case 'ArrowRight':
                  nextIndex = (index + 1) % enabledItems.length
                  break
                case 'ArrowLeft':
                  nextIndex = (index - 1 + enabledItems.length) % enabledItems.length
                  break
                case 'Home':
                  nextIndex = 0
                  break
                case 'End':
                  nextIndex = enabledItems.length - 1
                  break
                default:
                  return
              }
              event.preventDefault()
              const next = enabledItems[nextIndex]
              if (next) {
                setActive(next.key)
                tabRefs.current.get(next.key)?.focus()
              }
            }}
          >
            {item.label}
          </button>
        ))}
      </div>
      <div
        className="nx-tabs__panel"
        role="tabpanel"
        id={`${instanceId}-panel`}
        aria-labelledby={active ? tabId(active) : undefined}
        tabIndex={0}
        style={{ minWidth: 0, maxWidth: '100%' }}
      >
        {activeItem?.content}
      </div>
    </div>
  )
}
