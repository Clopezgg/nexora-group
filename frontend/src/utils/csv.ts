/**
 * Utilidad compartida de exportación CSV (NXR-REQ-0094). Alcance
 * deliberado: solo CSV -- XLSX/PDF quedan fuera de esta fase, ver
 * docs/superpowers/specs/2026-08-25-reports-search-analytics-design.md.
 */
export function toCsv<T extends Record<string, unknown>>(
  rows: T[],
  columns: { key: keyof T; label: string }[],
): string {
  const header = columns.map((c) => `"${c.label}"`).join(',')
  const body = rows
    .map((row) =>
      columns.map((c) => `"${String(row[c.key] ?? '').replace(/"/g, '""')}"`).join(','),
    )
    .join('\n')
  return `${header}\n${body}`
}

export function downloadCsv(filename: string, csv: string): void {
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}
