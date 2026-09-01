import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Badge,
  Button,
  Card,
  Combobox,
  EmptyState,
  ErrorState,
  Icon,
  Input,
  LoadingState,
  Select,
} from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { useMutationError } from '../../hooks/useMutationError'
import { documentService } from '../../services/documentService'
import { friendlyApiMessage } from '../../services/httpClient'
import { treasuryService } from '../../services/treasuryService'
import { voucherService } from '../../services/voucherService'
import type { Evidence } from '../../types/document'
import { statusLabel } from '../../utils/statusLabels'
import './TreasuryPage.css'

const METHODS_REQUIRING_EVIDENCE = new Set(['TRANSFER', 'DEPOSIT', 'CHECK'])

const EVIDENCE_ACCEPT =
  'application/pdf,image/jpeg,image/png,image/webp,image/heic,image/heif,.heic,.heif'

function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
  const value = bytes / 1024 ** exponent
  return `${value >= 10 || exponent === 0 ? Math.round(value) : value.toFixed(1)} ${units[exponent]}`
}

type EvidenceUiState = 'idle' | 'selected' | 'uploading' | 'uploaded' | 'failed'

interface PaymentEvidenceFieldProps {
  companyId: string
  documentId: string
  evidenceCount: number
  isBlocking: boolean
  onUploadingChange: (uploading: boolean) => void
}

/**
 * Enterprise mobile-friendly evidence uploader.
 *
 * The field is remounted (via a `key` on the parent) whenever the active
 * company or the selected accounting document changes, so a file picked for
 * document A can never leak into document B. The native input is never
 * cleared before the mutation resolves — the visible selection persists
 * through `selected -> uploading -> uploaded | failed`.
 */
function PaymentEvidenceField({
  companyId,
  documentId,
  evidenceCount,
  isBlocking,
  onUploadingChange,
}: PaymentEvidenceFieldProps) {
  const queryClient = useQueryClient()
  const evidenceKey = ['evidence', 'ACCOUNTING_DOCUMENT', documentId] as const
  const [file, setFile] = useState<File | null>(null)
  const [uiState, setUiState] = useState<EvidenceUiState>('idle')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const cameraInputRef = useRef<HTMLInputElement>(null)

  // On unmount (document or company changed — the parent remounts this field
  // via `key`) release any "uploading" lock held on the parent's PDF button.
  useEffect(() => () => onUploadingChange(false), [onUploadingChange])

  const upload = useMutation({
    mutationFn: (candidate: File) =>
      documentService.uploadEvidence(
        companyId,
        candidate,
        'PAYMENT_PROOF',
        'ACCOUNTING_DOCUMENT',
        documentId,
      ),
    onMutate: () => {
      setUiState('uploading')
      setErrorMessage(null)
      onUploadingChange(true)
    },
    onSuccess: (evidence: Evidence) => {
      // Optimistic cache write BEFORE invalidate: evidenceCount becomes > 0
      // immediately so "Generar PDF" enables without waiting for the refetch,
      // closing the race where the upload finished but the list still read 0.
      queryClient.setQueryData<Evidence[]>(evidenceKey, (previous) => {
        const list = Array.isArray(previous) ? previous : []
        return list.some((row) => row.id === evidence.id) ? list : [evidence, ...list]
      })
      queryClient.invalidateQueries({ queryKey: evidenceKey })
      setUiState('uploaded')
    },
    onError: (error: unknown) => {
      setErrorMessage(friendlyApiMessage(error))
      setUiState('failed')
    },
    onSettled: () => {
      onUploadingChange(false)
      // Safe to reset the native inputs now that the mutation resolved: the
      // filename/status stay visible from component state, and re-selecting
      // the same file will still fire onChange.
      if (fileInputRef.current) fileInputRef.current.value = ''
      if (cameraInputRef.current) cameraInputRef.current.value = ''
    },
  })

  function handlePicked(next: File | undefined | null) {
    if (!next) return
    setFile(next)
    setUiState('selected')
    setErrorMessage(null)
    upload.mutate(next)
  }

  const hasConfirmedEvidence = evidenceCount > 0
  const labelSuffix = hasConfirmedEvidence
    ? `· ${evidenceCount} adjunta(s)`
    : isBlocking
      ? '· obligatoria'
      : ''

  return (
    <div className="nx-evidence">
      <span className="nx-field__label">Evidencia del pago {labelSuffix}</span>

      <input
        ref={cameraInputRef}
        id="voucher-evidence-camera"
        type="file"
        accept={EVIDENCE_ACCEPT}
        capture="environment"
        hidden
        onChange={(event) => handlePicked(event.target.files?.[0])}
      />
      <input
        ref={fileInputRef}
        id="voucher-evidence-file"
        type="file"
        accept={EVIDENCE_ACCEPT}
        hidden
        onChange={(event) => handlePicked(event.target.files?.[0])}
      />

      <div className="nx-evidence__actions">
        <Button
          type="button"
          variant="secondary"
          disabled={uiState === 'uploading'}
          onClick={() => cameraInputRef.current?.click()}
        >
          <Icon name="camera" size={16} /> Tomar fotografía
        </Button>
        <Button
          type="button"
          variant="ghost"
          disabled={uiState === 'uploading'}
          onClick={() => fileInputRef.current?.click()}
        >
          <Icon name="file" size={16} /> Seleccionar archivo
        </Button>
      </div>

      {file ? (
        <div className="nx-evidence__file">
          <Icon name="file" size={16} />
          <span className="nx-evidence__filename">{file.name}</span>
          <span className="nx-evidence__meta">
            {file.type || 'tipo desconocido'} · {formatBytes(file.size)}
          </span>
        </div>
      ) : null}

      {uiState === 'uploading' ? (
        <p className="nx-field__hint" role="status">
          <Icon name="refresh" size={14} /> Subiendo evidencia…
        </p>
      ) : null}

      {uiState === 'uploaded' ? (
        <p className="nx-evidence__ok" role="status">
          <Icon name="check" size={14} /> Evidencia cargada correctamente
        </p>
      ) : null}

      {uiState === 'failed' ? (
        <div className="nx-field__error" role="alert">
          <p>
            <Icon name="warning" size={14} /> {errorMessage ?? 'No se pudo cargar la evidencia.'}
          </p>
          <Button
            type="button"
            variant="secondary"
            disabled={!file || upload.isPending}
            onClick={() => file && upload.mutate(file)}
          >
            <Icon name="refresh" size={16} /> Reintentar
          </Button>
        </div>
      ) : null}

      {isBlocking && !hasConfirmedEvidence && uiState !== 'uploading' ? (
        <p className="nx-field__error" role="alert">
          Adjunta el comprobante de transferencia para continuar.
        </p>
      ) : (
        <p className="nx-field__hint">
          Transferencia, depósito y cheque exigen adjuntar el comprobante del pago antes de emitir el PDF.
        </p>
      )}
    </div>
  )
}

// El comprobante de pago documenta un EGRESO de tesorería. "Remesa" es un
// INGRESO (TreasuryDirection INFLOW) y por eso ya no es un método de pago de
// comprobante — la sigue registrando Tesorería y aparece en el Flujo de Caja
// Real, pero nunca genera un Payment Voucher.
const PAYMENT_METHOD_LABELS: Record<string, string> = {
  TRANSFER: 'Transferencia',
  DEPOSIT: 'Depósito',
  CHECK: 'Cheque',
  CASH: 'Efectivo',
  OTHER: 'Otro',
}

/** Enmascara una cuenta bancaria dejando visibles sólo los últimos 4
 * dígitos (§52/§53). Nunca se imprime el número completo. */
function maskAccountReference(reference: string | null): string | null {
  if (!reference) return null
  const trimmed = reference.trim()
  if (trimmed.length <= 4) return `••••${trimmed}`
  return `••••${trimmed.slice(-4)}`
}

export function VouchersPage() {
  const handleMutationError = useMutationError()
  const { companies, activeCompanyId, setActiveCompanyId, isLoading, isError, refetch } = useActiveCompany()
  const activeCompany = companies.find((company) => company.id === activeCompanyId) ?? null
  const [documentId, setDocumentId] = useState('')
  const [beneficiaryKey, setBeneficiaryKey] = useState<string | null>(null)
  const [paymentMethod, setPaymentMethod] = useState('TRANSFER')
  const [approvedBy, setApprovedBy] = useState('')
  const [treasuryAccountId, setTreasuryAccountId] = useState('')
  const [evidenceUploading, setEvidenceUploading] = useState(false)

  const documentsQuery = useQuery({
    queryKey: ['accounting', 'journal-documents', activeCompanyId],
    queryFn: () => voucherService.listDocuments(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  const beneficiariesQuery = useQuery({
    queryKey: ['treasury', 'beneficiaries', activeCompanyId],
    queryFn: () => voucherService.listBeneficiaries(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  const accountsQuery = useQuery({
    queryKey: ['treasury', 'accounts', activeCompanyId],
    queryFn: () => treasuryService.listAccounts(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  const selectedBeneficiary = (beneficiariesQuery.data ?? []).find(
    (row) => `${row.beneficiaryType}:${row.id}` === beneficiaryKey,
  )

  const evidenceQuery = useQuery({
    queryKey: ['evidence', 'ACCOUNTING_DOCUMENT', documentId],
    queryFn: () =>
      documentService.listEvidence(activeCompanyId as string, 'ACCOUNTING_DOCUMENT', documentId),
    enabled: Boolean(activeCompanyId && documentId),
  })
  const evidenceCount = evidenceQuery.data?.length ?? 0
  const needsEvidence = METHODS_REQUIRING_EVIDENCE.has(paymentMethod)
  const evidenceMissing = needsEvidence && evidenceCount === 0

  const download = useMutation({
    mutationFn: () => voucherService.download(documentId, {
      beneficiaryType: selectedBeneficiary?.beneficiaryType,
      beneficiaryId: selectedBeneficiary?.id,
      paymentMethod,
      approvedBy: approvedBy.trim() || activeCompany?.voucherApproverName || undefined,
      treasuryAccountId: treasuryAccountId || undefined,
    }),
    onSuccess: (blob) => {
      const document = (documentsQuery.data ?? []).find((row) => row.id === documentId)
      const url = URL.createObjectURL(blob)
      const anchor = window.document.createElement('a')
      anchor.href = url
      anchor.download = `NEXORA-${document?.documentNumber ?? 'comprobante'}.pdf`
      anchor.rel = 'noopener'
      window.document.body.appendChild(anchor)
      anchor.click()
      // Safari/iOS: the download is still resolving when click() returns.
      // Revoking the object URL or yanking the anchor synchronously aborts it,
      // so defer both well past the navigation.
      window.setTimeout(() => {
        anchor.remove()
        URL.revokeObjectURL(url)
      }, 60_000)
    },
    onError: (error) => handleMutationError(error, 'Generar comprobante'),
  })

  if (isLoading) return <LoadingState label="Cargando comprobantes…" />
  if (isError) return <ErrorState description="No se pudieron cargar las compañías." onRetry={() => refetch()} />
  if (companies.length === 0) {
    return <EmptyState icon="receipt" title="No hay compañía configurada" description="Configura una compañía antes de generar comprobantes." />
  }

  const documents = documentsQuery.data ?? []
  const selected = documents.find((row) => row.id === documentId)
  const selectedAccount = (accountsQuery.data ?? []).find((row) => row.id === treasuryAccountId) ?? null
  const resolvedPayer = activeCompany?.voucherPayerName || activeCompany?.name || '—'
  const resolvedApprover = approvedBy.trim() || activeCompany?.voucherApproverName || '—'
  const canGenerate =
    Boolean(documentId && selectedBeneficiary && paymentMethod) && !evidenceMissing && !evidenceUploading

  return (
    <div className="nx-treasury">
      <header className="nx-treasury__header">
        <div>
          <p className="nx-page__eyebrow">Tesorería</p>
          <h1 className="nx-dashboard__title">Comprobantes / Vouchers</h1>
          <p className="nx-field__hint">Genera el PDF oficial desde un documento contable real. El identificador se resuelve por selector; no se capturan UUID manualmente.</p>
        </div>
        <Select value={activeCompanyId ?? ''} onChange={(event) => { setActiveCompanyId(event.target.value); setDocumentId('') }} aria-label="Compañía">
          {companies.map((company) => <option key={company.id} value={company.id}>{company.name}</option>)}
        </Select>
      </header>

      <Card title="Documento contable">
        {documentsQuery.isLoading ? <LoadingState label="Cargando documentos…" /> : documentsQuery.isError ? (
          <ErrorState description="No se pudieron cargar los documentos contables." onRetry={() => documentsQuery.refetch()} />
        ) : documents.length === 0 ? (
          <EmptyState
            icon="receipt"
            title="No hay egresos para documentar"
            description="El comprobante de pago solo se emite para un egreso de tesorería (pago a proveedor, gasto, activo). Los ingresos como las remesas se registran en Tesorería pero no generan comprobante."
          />
        ) : (
          <div className="nx-treasury__form">
            <p className="nx-field__hint">
              Solo se listan egresos de tesorería. Un ingreso (remesa, aporte, financiamiento) o una
              transferencia interna nunca genera comprobante de pago.
            </p>
            <Select label="Asiento / documento" value={documentId} onChange={(event) => setDocumentId(event.target.value)}>
              <option value="">Selecciona un documento…</option>
              {documents.map((document) => (
                <option key={document.id} value={document.id}>
                  {document.documentNumber} — {document.description ?? document.scope} — {statusLabel(document.status)}
                </option>
              ))}
            </Select>
            {selected ? (
              <div className="nx-treasury__actions">
                <Badge>{statusLabel(selected.status)}</Badge>
                <span>{selected.documentNumber}</span>
                <span>{selected.currencyCode}</span>
              </div>
            ) : null}
          </div>
        )}
      </Card>

      <Card title="Datos impresos en el comprobante">
        <div className="nx-treasury__form">
          <div>
            <Combobox
              label="Beneficiario"
              placeholder="Buscar proveedor, trabajador o cliente…"
              options={(beneficiariesQuery.data ?? []).map((row) => ({
                value: `${row.beneficiaryType}:${row.id}`,
                label: row.reference ? `${row.name} · ${row.reference}` : row.name,
              }))}
              value={beneficiaryKey}
              onChange={setBeneficiaryKey}
              emptyMessage={beneficiariesQuery.isLoading ? 'Cargando…' : 'Sin beneficiarios registrados.'}
            />
            <p className="nx-field__hint">El beneficiario se toma del registro real (Proveedores, Personal o Comercial). No se captura texto libre.</p>
          </div>
          <div>
            <Input
              label="Pagador"
              value={activeCompany?.voucherPayerName ?? 'No configurado — se usará el nombre de la compañía'}
              readOnly
              disabled
            />
            <p className="nx-field__hint">El pagador es un dato fijo de la compañía. Se define en Configuración → Perfil de la compañía.</p>
          </div>
          <Select label="Método de pago" value={paymentMethod} onChange={(event) => setPaymentMethod(event.target.value)}>
            <option value="TRANSFER">Transferencia</option>
            <option value="DEPOSIT">Depósito</option>
            <option value="CHECK">Cheque</option>
            <option value="CASH">Efectivo</option>
            <option value="OTHER">Otro</option>
          </Select>
          <Select
            label="Cuenta de tesorería (banco)"
            value={treasuryAccountId}
            onChange={(event) => setTreasuryAccountId(event.target.value)}
          >
            <option value="">Sin especificar</option>
            {(accountsQuery.data ?? []).map((account) => (
              <option key={account.id} value={account.id}>
                {account.institution ? `${account.institution} · ` : ''}{account.name}
              </option>
            ))}
          </Select>
          {selectedAccount ? (
            <div className="nx-bank-identity" aria-label="Identidad de la cuenta bancaria">
              <span className="nx-bank-identity__icon" aria-hidden="true">
                <Icon name="bank" />
              </span>
              <div className="nx-bank-identity__body">
                <span className="nx-bank-identity__name">
                  {selectedAccount.institution ?? selectedAccount.name}
                </span>
                <span className="nx-bank-identity__meta">
                  {maskAccountReference(selectedAccount.accountReference) ?? 'Sin número de cuenta'} ·{' '}
                  {selectedAccount.currencyCode}
                </span>
              </div>
            </div>
          ) : null}
          {documentId && needsEvidence && activeCompanyId ? (
            <PaymentEvidenceField
              key={`${activeCompanyId}:${documentId}`}
              companyId={activeCompanyId}
              documentId={documentId}
              evidenceCount={evidenceCount}
              isBlocking={evidenceMissing}
              onUploadingChange={setEvidenceUploading}
            />
          ) : null}
          <div>
            <Input
              label="Aprobado por"
              value={approvedBy}
              onChange={(event) => setApprovedBy(event.target.value)}
              placeholder={activeCompany?.voucherApproverName ?? 'Sin aprobador configurado'}
            />
            {activeCompany?.voucherApproverName ? (
              <p className="nx-field__hint">Si lo dejas vacío se usa el aprobador configurado: {activeCompany.voucherApproverName}</p>
            ) : null}
          </div>
        </div>
      </Card>

      <Card title="Vista previa del comprobante">
        <dl className="nx-voucher-preview">
          <div><dt>Documento</dt><dd>{selected?.documentNumber ?? '—'}</dd></div>
          <div><dt>Estado</dt><dd>{selected ? statusLabel(selected.status) : '—'}</dd></div>
          <div><dt>Moneda</dt><dd>{selected?.currencyCode ?? '—'}</dd></div>
          <div><dt>Ámbito</dt><dd>{selected?.scope ?? '—'}</dd></div>
          <div><dt>Beneficiario</dt><dd>{selectedBeneficiary?.name ?? '—'}</dd></div>
          <div><dt>Pagador</dt><dd>{resolvedPayer}</dd></div>
          <div><dt>Aprobado por</dt><dd>{resolvedApprover}</dd></div>
          <div><dt>Método de pago</dt><dd>{PAYMENT_METHOD_LABELS[paymentMethod] ?? paymentMethod}</dd></div>
          <div>
            <dt>Banco / cuenta</dt>
            <dd>
              {selectedAccount
                ? `${selectedAccount.institution ?? selectedAccount.name} · ${
                    maskAccountReference(selectedAccount.accountReference) ?? 'sin número'
                  }`
                : 'No especificado'}
            </dd>
          </div>
          <div>
            <dt>Evidencia</dt>
            <dd>{needsEvidence ? `${evidenceCount} adjunta(s)` : 'No requerida para este método'}</dd>
          </div>
        </dl>
        <p className="nx-field__hint">
          El monto y el detalle de débitos/créditos se toman del asiento contable; el PDF no
          puede alterarlos.
        </p>
        {evidenceMissing ? (
          <p className="nx-field__error" role="alert">
            Falta adjuntar el comprobante del pago (obligatorio para este método).
          </p>
        ) : null}
        <div className="nx-voucher-preview__actions">
          <Button
            loading={download.isPending}
            disabled={!canGenerate}
            onClick={() => download.mutate()}
          >
            Generar PDF
          </Button>
        </div>
      </Card>
    </div>
  )
}
