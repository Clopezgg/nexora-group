import { type FormEvent, useEffect, useState } from 'react'
import { Badge, Button, Input, Modal } from '../design-system'
import { editAccessService } from '../services/editAccessService'
import { ApiError } from '../services/httpClient'
import './EditAccessControl.css'

export function EditAccessControl() {
  const [open, setOpen] = useState(false)
  const [token, setToken] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [unlocked, setUnlocked] = useState(() => editAccessService.isUnlocked())

  useEffect(() => {
    const requireAccess = () => setOpen(true)
    const refresh = () => setUnlocked(editAccessService.isUnlocked())
    window.addEventListener('nexora:edit-access-required', requireAccess)
    window.addEventListener('nexora:edit-access-changed', refresh)
    return () => {
      window.removeEventListener('nexora:edit-access-required', requireAccess)
      window.removeEventListener('nexora:edit-access-changed', refresh)
    }
  }, [])

  const unlock = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await editAccessService.unlock(token)
      setToken('')
      setUnlocked(true)
      setOpen(false)
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'No se pudo validar el token de edición.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <button
        type="button"
        className={`nx-edit-access ${unlocked ? 'nx-edit-access--unlocked' : ''}`}
        onClick={() => {
          if (unlocked) {
            editAccessService.lock()
            setUnlocked(false)
          } else {
            setOpen(true)
          }
        }}
        title={unlocked ? 'Bloquear edición' : 'Desbloquear modificación de datos existentes'}
      >
        <span className="nx-edit-access__dot" aria-hidden="true" />
        {unlocked ? 'Edición habilitada' : 'Edición protegida'}
      </button>

      <Modal open={open} title="Desbloquear edición" onClose={() => setOpen(false)}>
        <form className="nx-edit-access__form" onSubmit={unlock}>
          <p>
            Para modificar o eliminar información ya guardada, ingresa el token de seguridad.
            El desbloqueo es temporal y no sustituye tus permisos de usuario.
          </p>
          <Input
            label="Token de seguridad"
            type="password"
            inputMode="numeric"
            autoComplete="off"
            value={token}
            onChange={(event) => setToken(event.target.value)}
          />
          {error ? <p className="nx-edit-access__error" role="alert">{error}</p> : null}
          <div className="nx-edit-access__actions">
            <Badge tone="neutral">Acceso temporal</Badge>
            <Button type="submit" loading={loading}>Desbloquear</Button>
          </div>
        </form>
      </Modal>
    </>
  )
}
