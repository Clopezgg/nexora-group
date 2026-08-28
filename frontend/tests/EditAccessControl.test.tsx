import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { EditAccessControl } from '../src/components/EditAccessControl'

const unlock = vi.fn()
const lock = vi.fn()
const isUnlocked = vi.fn()

vi.mock('../src/services/editAccessService', () => ({
  editAccessService: {
    unlock,
    lock,
    isUnlocked,
  },
}))

describe('EditAccessControl', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    isUnlocked.mockReturnValue(false)
    unlock.mockResolvedValue({ capability: 'signed-test-capability', expiresAt: 9999999999 })
  })

  it('starts protected and asks for the token without exposing its value', async () => {
    const user = userEvent.setup()
    render(<EditAccessControl />)

    await user.click(screen.getByRole('button', { name: 'Edición protegida' }))
    expect(screen.getByRole('dialog', { name: 'Desbloquear edición' })).toBeInTheDocument()
    const input = screen.getByLabelText('Token de seguridad')
    expect(input).toHaveProperty('type', 'password')
    expect(input).toHaveValue('')
  })

  it('unlocks through the service and never stores a plaintext token in the component', async () => {
    const user = userEvent.setup()
    render(<EditAccessControl />)

    await user.click(screen.getByRole('button', { name: 'Edición protegida' }))
    await user.type(screen.getByLabelText('Token de seguridad'), '246810')
    await user.click(screen.getByRole('button', { name: 'Desbloquear' }))

    expect(unlock).toHaveBeenCalledWith('246810')
    expect(await screen.findByRole('button', { name: 'Edición habilitada' })).toBeInTheDocument()
    expect(screen.queryByDisplayValue('246810')).not.toBeInTheDocument()
  })
})
