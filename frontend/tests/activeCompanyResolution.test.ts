import { describe, expect, it } from 'vitest'
import { resolveActiveCompanyId } from '../src/hooks/useActiveCompany'

describe('active company resolution', () => {
  const companies = [{ id: 'company-a' }, { id: 'company-b' }]

  it('does not silently authorize the first company when multiple are visible', () => {
    expect(resolveActiveCompanyId(null, companies)).toBeNull()
    expect(resolveActiveCompanyId('missing', companies)).toBeNull()
  })

  it('keeps an explicit valid selection and allows an unambiguous sole company', () => {
    expect(resolveActiveCompanyId('company-b', companies)).toBe('company-b')
    expect(resolveActiveCompanyId(null, [{ id: 'only-company' }])).toBe('only-company')
  })
})
