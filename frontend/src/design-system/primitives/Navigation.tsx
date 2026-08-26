import { useState, type ReactNode } from 'react'
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
}

export function Tabs({ items, defaultKey }: { items: TabItem[]; defaultKey?: string }) {
  const [active, setActive] = useState(defaultKey ?? items[0]?.key)
  const activeItem = items.find((item) => item.key === active)
  return (
    <div className="nx-tabs">
      <div role="tablist" className="nx-tabs__list">
        {items.map((item) => (
          <button
            key={item.key}
            role="tab"
            type="button"
            aria-selected={active === item.key}
            className={['nx-tabs__tab', active === item.key ? 'nx-tabs__tab--active' : '']
              .filter(Boolean)
              .join(' ')}
            onClick={() => setActive(item.key)}
          >
            {item.label}
          </button>
        ))}
      </div>
      <div className="nx-tabs__panel" role="tabpanel">
        {activeItem?.content}
      </div>
    </div>
  )
}
