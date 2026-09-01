/**
 * Etiquetas de calendario reales para el flujo de caja (ORDEN MAESTRA §5/§7/§10).
 *
 * NUNCA "S1", "S2", "S3" como lenguaje principal para el usuario. Tanto el modo
 * REALIZADO como el modo PROYECTADO usan fechas de calendario reales derivadas
 * del inicio/fin de cada período.
 */

const MONTHS_SHORT = [
  'ene', 'feb', 'mar', 'abr', 'may', 'jun',
  'jul', 'ago', 'sep', 'oct', 'nov', 'dic',
]
const MONTHS_FULL = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
]

/** Parse a `yyyy-mm-dd` string as a local calendar date (no timezone shift). */
function parseIso(value: string): Date {
  const [y, m, d] = value.split('-').map(Number)
  return new Date(y, (m || 1) - 1, d || 1)
}

function isLastDayOfMonth(date: Date): boolean {
  const next = new Date(date.getFullYear(), date.getMonth(), date.getDate() + 1)
  return next.getMonth() !== date.getMonth()
}

/**
 * Human calendar label for a period spanning [startIso, endIso].
 * - single day        → "13 sep"
 * - full month        → "Septiembre 2026"
 * - within one month   → "1–7 sep"
 * - spanning months    → "28 ago – 3 sep"
 */
export function formatPeriodLabel(startIso: string, endIso: string): string {
  const start = parseIso(startIso)
  const end = parseIso(endIso)

  if (startIso === endIso) {
    return `${start.getDate()} ${MONTHS_SHORT[start.getMonth()]}`
  }

  const spansFullMonth =
    start.getDate() === 1 &&
    isLastDayOfMonth(end) &&
    start.getFullYear() === end.getFullYear() &&
    start.getMonth() === end.getMonth()
  if (spansFullMonth) {
    return `${MONTHS_FULL[start.getMonth()]} ${start.getFullYear()}`
  }

  if (start.getMonth() === end.getMonth() && start.getFullYear() === end.getFullYear()) {
    return `${start.getDate()}–${end.getDate()} ${MONTHS_SHORT[start.getMonth()]}`
  }

  return `${start.getDate()} ${MONTHS_SHORT[start.getMonth()]} – ${end.getDate()} ${MONTHS_SHORT[end.getMonth()]}`
}
