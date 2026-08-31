import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Badge,
  Button,
  Card,
  Combobox,
  EmptyState,
  ErrorState,
  Input,
  LoadingState,
  Select,
} from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { useMutationError } from '../../hooks/useMutationError'
import { documentService } from '../../services/documentService'
import { voucherService } from '../../services/voucherService'
import { statusLabel } from '../../utils/statusLabels'
import './TreasuryPage.css'

const METHODS_REQUIRING_EVIDENCE = new Set(['TRANSFER', 'DEPOSIT', 'CHECK'])

export function VouchersPage() {
  const handleMutationError = useMutationError()
  const { companies, activeCompanyId, setActiveCompanyId, isLoading, isError, refetch } = useActiveCompany()
  const activeCompany = companies.find((company) => company.id === activeCompanyId) ?? null
  const [documentId, setDocumentId] = useState('')
  const [beneficiaryKey, setBeneficiaryKey] = useState<string | null>(null)
  const [paymentMethod, setPaymentMethod] = useState('TRANSFER')
  const [approvedBy, setApprovedBy] = useState('')

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

  const selectedBeneficiary = (beneficiariesQuery.data ?? []).find(
    (row) => `${row.beneficiaryType}:${row.id}` === beneficiaryKey,
  )

  const queryClient = useQueryClient()
  const evidenceQuery = useQuery({
    queryKey: ['evidence', 'ACCOUNTING_DOCUMENT', documentId],
    queryFn: () =>
      documentService.listEvidence(activeCompanyId as string, 'ACCOUNTING_DOCUMENT', documentId),
    enabled: Boolean(activeCompanyId && documentId),
  })
  const evidenceCount = evidenceQuery.data?.length ?? 0
  const needsEvidence = METHODS_REQUIRING_EVIDENCE.has(paymentMethod)
  const evidenceMissing = needsEvidence && evidenceCount === 0

  const uploadEvidence = useMutation({
    mutationFn: (file: File) =>
      documentService.uploadEvidence(
        activeCompanyId as string,
        file,
        'PAYMENT_PROOF',
        'ACCOUNTING_DOCUMENT',
        documentId,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['evidence', 'ACCOUNTING_DOCUMENT', documentId] })
    },
    onError: (error) => handleMutationError(error, 'Adjuntar evidencia'),
  })

  const download = useMutation({
    mutationFn: () => voucherService.download(documentId, {
      beneficiaryType: selectedBeneficiary?.beneficiaryType,
      beneficiaryId: selectedBeneficiary?.id,
      paymentMethod,
      approvedBy: approvedBy.trim() || activeCompany?.voucherApproverName || undefined,
    }),
    onSuccess: (blob) => {
      const document = (documentsQuery.data ?? []).find((row) => row.id === documentId)
      const url = URL.createObjectURL(blob)
      const anchor = window.document.createElement('a')
      anchor.href = url
      anchor.download = `NEXORA-${document?.documentNumber ?? 'comprobante'}.pdf`
      window.document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      URL.revokeObjectURL(url)
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
        ) : (
          <div className="nx-treasury__form">
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
            <option value="REMITTANCE">Remesa</option>
            <option value="OTHER">Otro</option>
          </Select>
          {documentId && needsEvidence ? (
            <div>
              <label className="nx-field__label" htmlFor="voucher-evidence">
                Evidencia del pago {evidenceMissing ? '· obligatoria' : `· ${evidenceCount} adjunta(s)`}
              </label>
              <input
                id="voucher-evidence"
                type="file"
                accept="application/pdf,image/jpeg,image/png,image/webp"
                disabled={uploadEvidence.isPending}
                onChange={(event) => {
                  const file = event.target.files?.[0]
                  if (file) uploadEvidence.mutate(file)
                  event.target.value = ''
                }}
              />
              <p className={evidenceMissing ? 'nx-field__error' : 'nx-field__hint'} role={evidenceMissing ? 'alert' : undefined}>
                Transferencia, depósito y cheque exigen adjuntar el comprobante del pago antes de emitir el PDF.
              </p>
            </div>
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
          <Button
            loading={download.isPending}
            disabled={!documentId || !selectedBeneficiary || !paymentMethod || evidenceMissing}
            onClick={() => download.mutate()}
          >
            Generar PDF
          </Button>
        </div>
      </Card>
    </div>
  )
}