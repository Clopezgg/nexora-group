import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { SapToolbar } from '../../sap-gui/components/SapToolbar'

afterEach(cleanup)

describe('SapToolbar keyboard', () => {
  it('uses one tab stop and moves focus without executing actions', () => {
    const onOpenNav = vi.fn()
    render(
      <MemoryRouter>
        <SapToolbar onOpenNav={onOpenNav} />
      </MemoryRouter>,
    )
    const buttons = screen.getAllByRole('button')
    expect(buttons.map((button) => button.tabIndex)).toEqual([0, -1, -1, -1, -1])
    buttons[0].focus()
    fireEvent.keyDown(buttons[0], { key: 'ArrowLeft' })
    expect(document.activeElement).toBe(buttons[4])
    fireEvent.keyDown(buttons[4], { key: 'ArrowRight' })
    expect(document.activeElement).toBe(buttons[0])
    fireEvent.keyDown(buttons[0], { key: 'End' })
    expect(document.activeElement).toBe(buttons[4])
    fireEvent.keyDown(buttons[4], { key: 'Home' })
    expect(document.activeElement).toBe(buttons[0])
    expect(onOpenNav).not.toHaveBeenCalled()
    fireEvent.click(buttons[4])
    expect(onOpenNav).toHaveBeenCalledOnce()
  })
  it('remembers the focused control for reentry and uses existing SVG icons', () => {
    render(
      <MemoryRouter>
        <SapToolbar onOpenNav={vi.fn()} />
      </MemoryRouter>,
    )
    const search = screen.getByRole('button', { name: 'Búsqueda global' })
    fireEvent.focus(search)
    expect(search.tabIndex).toBe(0)
    expect(screen.getByRole('button', { name: 'Atrás' }).tabIndex).toBe(-1)
    for (const label of ['Inicio', 'Búsqueda global', 'Abrir navegación']) {
      expect(screen.getByRole('button', { name: label }).querySelector('svg')).not.toBeNull()
    }
  })
})
