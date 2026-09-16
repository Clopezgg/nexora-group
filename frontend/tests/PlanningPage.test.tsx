import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

describe('PlanningPage', () => {
  it('lists and creates tasks with an existing dependency and milestones through the real API contract', async () => {
    const tasks = [{ id: 't1', projectId: 'p1', wbsNodeId: null, name: 'Preparación', owner: 'Ana', plannedStart: '2026-09-01', plannedEnd: '2026-09-02', dependsOnTaskId: null, status: 'PLANNED' }]
    const milestones: unknown[] = []
    vi.stubGlobal('fetch', vi.fn().mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.includes('/auth/me')) return Promise.resolve({ ok: true, status: 200, json: async () => ({ id: 'u1', email: 'pm@nexora.group', fullName: 'PM', roles: ['Project Manager'], permissions: ['project.planning:read'] }) } as Response)
      if (url.includes('/master-data/companies')) return Promise.resolve({ ok: true, status: 200, json: async () => ([{ id: 'c1', name: 'Nexora', code: null, legalName: null, functionalCurrencyCode: 'HNL' }]) } as Response)
      if (url.includes('/projects?')) return Promise.resolve({ ok: true, status: 200, json: async () => ([{ id: 'p1', companyId: 'c1', name: 'Torre Norte' }]) } as Response)
      if (url.endsWith('/projects/p1/tasks') && init?.method === 'POST') {
        const body = JSON.parse(String(init.body))
        tasks.push({ id: 't2', projectId: 'p1', wbsNodeId: null, status: 'PLANNED', ...body })
        return Promise.resolve({ ok: true, status: 201, json: async () => tasks[1] } as Response)
      }
      if (url.endsWith('/projects/p1/tasks')) return Promise.resolve({ ok: true, status: 200, json: async () => tasks } as Response)
      if (url.endsWith('/projects/p1/milestones') && init?.method === 'POST') {
        const body = JSON.parse(String(init.body)); milestones.push({ id: 'm1', projectId: 'p1', wbsNodeId: null, status: 'PLANNED', achievedDate: null, ...body })
        return Promise.resolve({ ok: true, status: 201, json: async () => milestones[0] } as Response)
      }
      if (url.endsWith('/projects/p1/milestones')) return Promise.resolve({ ok: true, status: 200, json: async () => milestones } as Response)
      return Promise.resolve({ ok: true, status: 200, json: async () => ({}) } as Response)
    }))

    render(renderApp('/proyectos/planeacion'))
    fireEvent.change(await screen.findByLabelText('Proyecto'), { target: { value: 'p1' } })
    expect(await screen.findByText('Preparación')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Nueva tarea' }))
    fireEvent.change(screen.getByLabelText('Nombre'), { target: { value: 'Cimentación' } })
    fireEvent.change(screen.getByLabelText('Depende de'), { target: { value: 't1' } })
    fireEvent.click(screen.getByRole('button', { name: 'Guardar tarea' }))
    expect(await screen.findByText('Cimentación')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Nuevo hito' }))
    fireEvent.change(screen.getByLabelText('Nombre'), { target: { value: 'Inicio de obra' } })
    fireEvent.change(screen.getByLabelText('Fecha objetivo'), { target: { value: '2026-10-01' } })
    fireEvent.click(screen.getByRole('button', { name: 'Guardar hito' }))
    expect(await screen.findByText('Inicio de obra')).toBeInTheDocument()
  })
})
