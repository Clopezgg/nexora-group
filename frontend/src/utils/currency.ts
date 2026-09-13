const symbolCache = new Map<string, string>()

function normalizeCurrency(currency?: string | null): string | null {
  const key = currency?.trim().toUpperCase() ?? ''
  return /^[A-Z]{3}$/.test(key) ? key : null
}

function currencySymbol(currency?: string | null): string | null {
  const key = normalizeCurrency(currency)
  if (!key) return null
  let symbol = symbolCache.get(key)
  if (!symbol) {
    try {
      const parts = new Intl.NumberFormat('es-HN', {
        style: 'currency',
        currency: key,
        currencyDisplay: 'narrowSymbol',
      }).formatToParts(1)
      symbol = parts.find((part) => part.type === 'currency')?.value ?? key
    } catch {
      symbol = key
    }
    symbolCache.set(key, symbol)
  }
  return symbol
}

/**
 * Formatea dinero sin convertir strings Decimal del backend a IEEE-754.
 * La representación financiera autoritativa viaja como string; aquí se
 * normaliza a centavos con BigInt y redondeo decimal exacto. Los `number`
 * siguen aceptándose para inputs/UI no autoritativos por compatibilidad.
 *
 * No existe moneda implícita: si el llamador no aporta un código ISO válido,
 * el formatter falla cerrado visualmente con `—` en vez de inventar HNL u
 * otra divisa. Los flujos de creación/posting deben además bloquear antes de
 * llegar a esta capa de presentación.
 */
export function formatMoney(value: number | string, currency?: string | null): string {
  const symbol = currencySymbol(currency)
  if (!symbol) return '—'

  const raw =
    typeof value === 'number'
      ? Number.isFinite(value)
        ? value.toFixed(2)
        : '0'
      : String(value).trim()
  const match = raw.match(/^([+-]?)(\d+)(?:\.(\d+))?$/)
  const separator = '\u00a0'
  if (!match) return `${symbol}${separator}0.00`

  const negative = match[1] === '-'
  const integer = BigInt(match[2])
  const fraction = (match[3] ?? '').padEnd(3, '0')
  let cents = integer * 100n + BigInt(fraction.slice(0, 2) || '0')
  if (Number(fraction[2] ?? '0') >= 5) cents += 1n

  const whole = cents / 100n
  const decimal = String(cents % 100n).padStart(2, '0')
  const grouped = whole.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',')
  const sign = negative && cents !== 0n ? '-' : ''
  return `${sign}${symbol}${separator}${grouped}.${decimal}`
}

/** Abbreviated money is deliberately presentational (axes/sparklines), never
 * used as an accounting value or request payload. */
export function formatMoneyCompact(
  value: number | string,
  currency?: string | null,
): string {
  const symbol = currencySymbol(currency)
  if (!symbol) return '—'
  const amount = Number(value)
  if (!Number.isFinite(amount)) return formatMoney(0, currency)
  const sign = amount < 0 ? '-' : ''
  const abs = Math.abs(amount)
  if (abs >= 1_000_000) {
    return `${sign}${symbol} ${(abs / 1_000_000).toFixed(abs >= 10_000_000 ? 0 : 1)}M`
  }
  if (abs >= 1_000) {
    return `${sign}${symbol} ${(abs / 1_000).toFixed(abs >= 100_000 ? 0 : 1)}K`
  }
  return `${sign}${symbol} ${abs.toFixed(0)}`
}
