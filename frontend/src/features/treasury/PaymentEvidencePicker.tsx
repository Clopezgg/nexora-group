import { useRef, useState } from 'react'
import { Button, Icon } from '../../design-system'
import { documentService } from '../../services/documentService'
import { friendlyApiMessage } from '../../services/httpClient'

const EVIDENCE_ACCEPT =
  'application/pdf,image/jpeg,image/png,image/webp,image/heic,image/heif,.heic,.heif'

export function PaymentEvidencePicker({
  companyId,
  invoiceId,
  required,
  disabled,
  onChange,
}: {
  companyId: string
  invoiceId: string
  required: boolean
  disabled?: boolean
  onChange: (evidenceIds: string[], uploading: boolean) => void
}) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const cameraInputRef = useRef<HTMLInputElement>(null)
  const [evidenceIds, setEvidenceIds] = useState<string[]>([])
  const [filenames, setFilenames] = useState<string[]>([])
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function upload(file: File | undefined | null) {
    if (!file) return
    setUploading(true)
    setError(null)
    onChange(evidenceIds, true)
    try {
      const evidence = await documentService.uploadEvidence(
        companyId,
        file,
        'PAYMENT_PROOF',
        'SUPPLIER_PAYMENT_STAGED',
        invoiceId,
      )
      const nextIds = evidenceIds.includes(evidence.id) ? evidenceIds : [...evidenceIds, evidence.id]
      setEvidenceIds(nextIds)
      setFilenames((rows) => (rows.includes(file.name) ? rows : [...rows, file.name]))
      onChange(nextIds, false)
    } catch (cause) {
      setError(friendlyApiMessage(cause))
      onChange(evidenceIds, false)
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
      if (cameraInputRef.current) cameraInputRef.current.value = ''
    }
  }

  return (
    <div className="nx-evidence">
      <span className="nx-field__label">
        Evidencia del pago {required ? '· obligatoria antes de contabilizar' : '· opcional'}
      </span>
      <input
        ref={cameraInputRef}
        type="file"
        accept={EVIDENCE_ACCEPT}
        capture="environment"
        hidden
        onChange={(event) => void upload(event.target.files?.[0])}
      />
      <input
        ref={fileInputRef}
        type="file"
        accept={EVIDENCE_ACCEPT}
        hidden
        onChange={(event) => void upload(event.target.files?.[0])}
      />
      <div className="nx-evidence__actions">
        <Button type="button" variant="secondary" disabled={disabled || uploading} onClick={() => cameraInputRef.current?.click()}>
          <Icon name="camera" size={16} /> Tomar fotografía
        </Button>
        <Button type="button" variant="ghost" disabled={disabled || uploading} onClick={() => fileInputRef.current?.click()}>
          <Icon name="file" size={16} /> Seleccionar archivo
        </Button>
      </div>
      {uploading ? <p className="nx-field__hint" role="status">Subiendo evidencia…</p> : null}
      {filenames.length > 0 ? (
        <p className="nx-evidence__ok" role="status">
          <Icon name="check" size={14} /> {filenames.length} evidencia(s) preparada(s): {filenames.join(', ')}
        </p>
      ) : null}
      {error ? <p className="nx-field__error" role="alert">{error}</p> : null}
      {required && evidenceIds.length === 0 && !uploading ? (
        <p className="nx-field__error" role="alert">
          Adjunta el comprobante antes de confirmar el pago. El dinero no se contabiliza sin evidencia.
        </p>
      ) : null}
    </div>
  )
}
