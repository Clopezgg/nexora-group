const BUSINESS_TIME_ZONE = 'America/Tegucigalpa'

/** Fecha civil del negocio (YYYY-MM-DD), independiente del UTC del navegador. */
export function businessTodayIso(now = new Date()): string {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: BUSINESS_TIME_ZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(now)
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]))
  return `${values.year}-${values.month}-${values.day}`
}
