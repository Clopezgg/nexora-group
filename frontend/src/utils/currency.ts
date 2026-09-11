const symbolCache = new Map<string, string>()

function normalizeCurrency(currency: string): string {
  const key = currency.trim().toUpperCase()
  if (!/^[A-Z]{3}$/.test(key)) {
    throw new Error('Se requiere un código de moneda ISO explícito para formatear importes.')
  }
  return key
}

function currencySymbol(currency: string): string {
  const key = normalizeCurrency(currency)
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
 * La moneda es obligatoria: ningún flujo financiero puede caer silenciosamente
 * a una divisa predeterminada.
 */
export function formatMoney(value: number | string, currency: string): string {
  const raw = typeof value === 'number'
    ? (Number.isFinite(value) ? value.toFixed(2) : '0')
    : String(value).trim()
  const match = raw.match(/^([+-]?)(\d+)(?:\.(\d+))?$/)
  const separator = '\u00a0'
  const symbol = currencySymbol(currency)
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
export function formatMoneyCompact(value: number | string, currency: string): string {
  const amount = Number(value)
  if (!Number.isFinite(amount)) return formatMoney(0, currency)
  const symbol = currencySymbol(currency)
  const sign = amount < 0 ? '-' : ''
  const abs = Math.abs(amount)
  if (abs >= 1_000_000) return `${sign}${symbol} ${(abs / 1_000_000).toFixed(abs >= 10_000_000 ? 0 : 1)}M`
  if (abs >= 1_000) return `${sign}${symbol} ${(abs / 1_000).toFixed(abs >= 100_000 ? 0 : 1)}K`
  return `${sign}${symbol} ${abs.toFixed(0)}`
}
