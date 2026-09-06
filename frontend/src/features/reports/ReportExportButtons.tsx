import { useMutation } from '@tanstack/react-query'
import { Button } from '../../design-system'

export type ReportFormat = 'xlsx' | 'pdf'
export type BlobDownload = { blob: Blob; filename?: string | null }

function download({ blob, filename }: BlobDownload, fallback: string) {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename || fallback
  anchor.rel = 'noopener'
  document.body.appendChild(anchor)
  anchor.click()
  window.setTimeout(() => {
    anchor.remove()
    URL.revokeObjectURL(url)
  }, 60_000)
}

export function ReportExportButtons({
  disabled = false,
  basename,
  exportFile,
}: {
  disabled?: boolean
  basename: string
  exportFile: (format: ReportFormat) => Promise<BlobDownload>
}) {
  const mutation = useMutation({
    mutationFn: async (format: ReportFormat) => ({ format, file: await exportFile(format) }),
    onSuccess: ({ format, file }) => download(file, `${basename}.${format}`),
  })

  return (
    <>
      <Button
        variant="secondary"
        disabled={disabled || mutation.isPending}
        loading={mutation.isPending && mutation.variables === 'xlsx'}
        onClick={() => mutation.mutate('xlsx')}
      >
        Exportar XLSX
      </Button>
      <Button
        variant="secondary"
        disabled={disabled || mutation.isPending}
        loading={mutation.isPending && mutation.variables === 'pdf'}
        onClick={() => mutation.mutate('pdf')}
      >
        Exportar PDF
      </Button>
      {mutation.isError ? (
        <span className="nx-field__error" role="alert">No se pudo generar el archivo.</span>
      ) : null}
    </>
  )
}
