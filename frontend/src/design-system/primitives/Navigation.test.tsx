import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Tabs } from './Navigation'

const items = [
  { key: 'first', label: 'Resumen', content: 'Resumen financiero' },
  { key: 'second', label: 'Movimientos', content: 'Movimientos financieros' },
  { key: 'third', label: 'Documentos', content: 'Documentos adjuntos' },
]
afterEach(cleanup)

describe('Tabs workstation keyboard', () => {
  it('links the selected tab and panel and exposes only one tab stop', () => {
    render(<Tabs items={items} />)
    const tabs = screen.getAllByRole('tab')
    const panel = screen.getByRole('tabpanel')
    expect(tabs.map((tab) => tab.tabIndex)).toEqual([0, -1, -1])
    expect(tabs[0].getAttribute('aria-controls')).toBe(panel.id)
    expect(panel.getAttribute('aria-labelledby')).toBe(tabs[0].id)
    expect(panel.tabIndex).toBe(0)
  })
  it('moves selection and focus with arrows, Home and End, wrapping at boundaries', () => {
    render(<Tabs items={items} />)
    const tabs = screen.getAllByRole('tab')
    tabs[0].focus()
    fireEvent.keyDown(tabs[0], { key: 'ArrowLeft' })
    expect(document.activeElement).toBe(tabs[2])
    expect(screen.getByRole('tabpanel').textContent).toBe('Documentos adjuntos')
    fireEvent.keyDown(tabs[2], { key: 'ArrowRight' })
    expect(document.activeElement).toBe(tabs[0])
    fireEvent.keyDown(tabs[0], { key: 'End' })
    expect(document.activeElement).toBe(tabs[2])
    fireEvent.keyDown(tabs[2], { key: 'Home' })
    expect(document.activeElement).toBe(tabs[0])
  })
  it('skips disabled tabs and selects an enabled default', () => {
    render(<Tabs items={items.map((item, index) => ({ ...item, disabled: index === 0 }))} />)
    const tabs = screen.getAllByRole('tab')
    expect((tabs[0] as HTMLButtonElement).disabled).toBe(true)
    expect(tabs.map((tab) => tab.tabIndex)).toEqual([-1, 0, -1])
    fireEvent.keyDown(tabs[1], { key: 'ArrowLeft' })
    expect(document.activeElement).toBe(tabs[2])
    fireEvent.keyDown(tabs[2], { key: 'Home' })
    expect(document.activeElement).toBe(tabs[1])
  })
  it('requests controlled selection without changing its panel itself', () => {
    const onChange = vi.fn()
    const { rerender } = render(<Tabs items={items} activeKey="first" onChange={onChange} />)
    fireEvent.keyDown(screen.getAllByRole('tab')[0], { key: 'ArrowRight' })
    expect(onChange).toHaveBeenCalledWith('second')
    expect(screen.getByRole('tabpanel').textContent).toBe('Resumen financiero')
    rerender(<Tabs items={items} activeKey="second" onChange={onChange} />)
    expect(screen.getByRole('tabpanel').textContent).toBe('Movimientos financieros')
  })
})
