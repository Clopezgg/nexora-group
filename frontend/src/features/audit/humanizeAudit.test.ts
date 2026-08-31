import { describe, expect, it } from 'vitest'
import { auditActorLabel, humanizeAuditAction, redactSensitive } from './humanizeAudit'

describe('humanizeAuditAction', () => {
  it('maps module.entity.verb to Spanish', () => {
    expect(humanizeAuditAction('ap.supplier_invoice.approve')).toMatchObject({
      module: 'Cuentas por pagar',
      record: 'Factura de proveedor',
      event: 'Factura de proveedor · Aprobación',
      code: 'ap.supplier_invoice.approve',
    })
  })

  it('handles multi-token verbs and entities', () => {
    expect(humanizeAuditAction('asset.fixed_asset.status_change').event).toBe(
      'Activo fijo · Cambio de estado',
    )
    expect(humanizeAuditAction('core.user.company_access.grant')).toMatchObject({
      module: 'Configuración',
      record: 'Acceso a compañía',
      event: 'Acceso a compañía · Otorgamiento',
    })
  })

  it('maps the authorized project reset without leaking the raw code', () => {
    const h = humanizeAuditAction('project.reset.authorized')
    expect(h.event.toLowerCase()).toContain('restablecimiento')
    expect(h.event).not.toContain('project.reset')
    expect(h.code).toBe('project.reset.authorized')
  })

  it('falls back gracefully for an unknown action', () => {
    const h = humanizeAuditAction('newmodule.new_thing.frobnicate')
    expect(h.module).toBe('Newmodule')
    expect(h.record).toBe('New thing')
    expect(h.event).toContain('Frobnicate')
  })
})

describe('auditActorLabel', () => {
  it('prefers full name, then email, then Sistema', () => {
    expect(auditActorLabel({ actorFullName: 'Carlos López', actorEmail: 'c@x.com' })).toBe('Carlos López')
    expect(auditActorLabel({ actorFullName: null, actorEmail: 'c@x.com' })).toBe('c@x.com')
    expect(auditActorLabel({ actorFullName: null, actorEmail: null })).toBe('Sistema')
  })
})

describe('redactSensitive', () => {
  it('hides secret-looking keys at any depth', () => {
    const out = redactSensitive({
      status: 'APPROVED',
      meta: { password: 'p', token: 't', nested: { api_key: 'k', ok: 1 } },
      list: [{ secret: 's', keep: 2 }],
    }) as Record<string, unknown>
    expect(out.status).toBe('APPROVED')
    expect((out.meta as Record<string, unknown>).password).toBe('[oculto]')
    expect(((out.meta as Record<string, Record<string, unknown>>).nested).api_key).toBe('[oculto]')
    expect(((out.meta as Record<string, Record<string, unknown>>).nested).ok).toBe(1)
    expect((out.list as Array<Record<string, unknown>>)[0].secret).toBe('[oculto]')
    expect((out.list as Array<Record<string, unknown>>)[0].keep).toBe(2)
  })
})
