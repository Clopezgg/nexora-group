import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { statusLabel } from '../src/utils/statusLabels'

// Vitest may execute this suite with an http import URL; resolve from the
// frontend package instead of requiring a file:// import URL.
const AP = readFileSync(resolve(process.cwd(), 'src/features/treasury/AccountsPayablePage.tsx'), 'utf8')
const AR = readFileSync(resolve(process.cwd(), 'src/features/treasury/AccountsReceivablePage.tsx'), 'utf8')

describe('financial status humanization', () => {
  it.each([
    ['DRAFT', 'Borrador'],
    ['REVIEW', 'En revisión'],
    ['APPROVED', 'Aprobado'],
    ['SCHEDULED', 'Programado'],
    ['PARTIALLY_PAID', 'Pagado parcialmente'],
    ['PAID', 'Pagado'],
    ['PARTIALLY_COLLECTED', 'Cobrado parcialmente'],
    ['COLLECTED', 'Cobrado'],
    ['CANCELLED', 'Cancelado'],
  ])('maps %s to a human label', (raw, expected) => {
    expect(statusLabel(raw)).toBe(expected)
  })

  it('does not render raw AP/AR row.status as the primary table text', () => {
    expect(AP).not.toMatch(/render:\s*\(row\)\s*=>\s*row\.status/)
    expect(AR).not.toMatch(/render:\s*\(row\)\s*=>\s*row\.status/)
  })
})
