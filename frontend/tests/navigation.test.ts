import { describe, expect, it } from 'vitest'
import { filterNavGroups } from '../src/app/navigation'

describe('filterNavGroups', () => {
  it('keeps the public home but removes unauthorized entries and empty groups', () => {
    const groups = filterNavGroups([])
    expect(groups).toHaveLength(1)
    expect(groups[0]).toMatchObject({ key: 'inicio', items: [{ path: '/inicio' }] })
  })

  it('shows planning only to a user with its declared read permission', () => {
    const groups = filterNavGroups(['project.planning:read'])
    const projects = groups.find((group) => group.key === 'proyectos')
    expect(projects?.items).toEqual([{ path: '/proyectos/planeacion', label: 'Planeación', icon: 'chart', requiredAny: ['project.planning:read'] }])
  })
})
