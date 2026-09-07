import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Badge, Button, Card } from '../../design-system'
import { documentService } from '../../services/documentService'
import { masterDataService } from '../../services/masterDataService'

function BrandingAsset({
  companyId,
  kind,
  configured,
}: {
  companyId: string
  kind: 'logo' | 'signature'
  configured: boolean
}) {
  const queryClient = useQueryClient()
  const [file, setFile] = useState<File | null>(null)
  const label = kind === 'logo' ? 'Logo de la compañía' : 'Firma gráfica del aprobador'

  const upload = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error('Selecciona una imagen')
      const evidence = await documentService.uploadEvidence(
        companyId,
        file,
        kind === 'logo' ? 'COMPANY_LOGO' : 'COMPANY_SIGNATURE',
      )
      return masterDataService.updateCompany(companyId, kind === 'logo'
        ? { logoEvidenceId: evidence.id }
        : { signatureEvidenceId: evidence.id })
    },
    onSuccess: () => {
      setFile(null)
      queryClient.invalidateQueries({ queryKey: ['master-data', 'companies'] })
    },
  })

  return (
    <div className="nx-field">
      <div className="nx-treasury__actions">
        <strong>{label}</strong>
        <Badge tone={configured ? 'success' : 'neutral'}>
          {configured ? 'Configurado' : 'Sin configurar'}
        </Badge>
      </div>
      <input
        aria-label={label}
        type="file"
        accept="image/png,image/jpeg,image/webp,image/heic,image/heif"
        onChange={(event) => setFile(event.target.files?.[0] ?? null)}
      />
      <p className="nx-field__hint">
        Se guarda como evidencia privada. El comprobante congela la referencia en su primera emisión para que una reimpresión histórica no cambie.
      </p>
      <Button
        type="button"
        variant="secondary"
        loading={upload.isPending}
        disabled={!file}
        onClick={() => upload.mutate()}
      >
        {configured ? 'Reemplazar para comprobantes futuros' : 'Subir y configurar'}
      </Button>
      {upload.isSuccess ? <p className="nx-field__hint" role="status">Identidad documental actualizada.</p> : null}
      {upload.isError ? <p className="nx-field__error" role="alert">{(upload.error as Error).message}</p> : null}
    </div>
  )
}

export function CompanyBrandingCard({ companyId }: { companyId: string }) {
  const companiesQuery = useQuery({
    queryKey: ['master-data', 'companies'],
    queryFn: masterDataService.listCompanies,
  })
  const company = (companiesQuery.data ?? []).find((item) => item.id === companyId)

  return (
    <Card title="Identidad de comprobantes">
      <p className="nx-field__hint">
        Logo y firma se almacenan en Evidence privado; NEXORA nunca guarda una URL pública de Blob. Solo afectan comprobantes nuevos: los ya emitidos conservan su snapshot.
      </p>
      <BrandingAsset companyId={companyId} kind="logo" configured={Boolean(company?.logoEvidenceId)} />
      <BrandingAsset companyId={companyId} kind="signature" configured={Boolean(company?.signatureEvidenceId)} />
    </Card>
  )
}
