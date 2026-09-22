import fs from 'node:fs/promises'
import path from 'node:path'
import { chromium } from '@playwright/test'

function required(name) {
  const value = process.env[name]
  if (!value) throw new Error(`Missing required environment variable: ${name}`)
  return value
}

const baseUrl = required('PRODUCTION_BASE_URL').replace(/\/$/, '')
const email = required('PRODUCTION_ADMIN_EMAIL')
const password = required('PRODUCTION_ADMIN_PASSWORD')
const outputDir = process.env.PRODUCTION_VISUAL_DIR ?? 'production-visual'

const viewports = [
  { name: '1920', width: 1920, height: 1080 },
  { name: '1440', width: 1440, height: 900 },
  { name: '1366', width: 1366, height: 900 },
  { name: '1280', width: 1280, height: 900 },
  { name: '1024', width: 1024, height: 900 },
  { name: '768', width: 768, height: 1024 },
  { name: '430', width: 430, height: 932 },
  { name: '390', width: 390, height: 844 },
  { name: '360', width: 360, height: 800 },
]

const routes = [
  ['/inicio', 'inicio'],
  ['/finanzas/contabilidad', 'contabilidad'],
  ['/finanzas/tesoreria', 'tesoreria'],
  ['/finanzas/cuentas-por-pagar', 'cuentas-por-pagar'],
  ['/finanzas/cuentas-por-cobrar', 'cuentas-por-cobrar'],
  ['/proyectos', 'proyectos'],
  ['/proyectos/cockpit', 'project-cockpit'],
  ['/abastecimiento/solicitudes', 'solicitudes'],
  ['/abastecimiento/inventario', 'inventario'],
  ['/comercial/clientes', 'clientes'],
  ['/control/documentos', 'documentos'],
  ['/control/reportes', 'reportes'],
  ['/control/configuracion', 'configuracion'],
]

await fs.mkdir(outputDir, { recursive: true })

const browser = await chromium.launch({ headless: true })
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } })
const page = await context.newPage()
const failures = []

try {
  await page.goto(`${baseUrl}/login`, { waitUntil: 'domcontentloaded', timeout: 45_000 })
  await page.getByLabel('Correo electrónico').fill(email)
  await page.getByLabel('Contraseña').fill(password)
  await page.getByRole('button', { name: /iniciar sesión/i }).click()
  await page.waitForURL(/\/inicio(?:$|[/?#])/, { timeout: 30_000 })

  for (const viewport of viewports) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height })

    for (const [route, name] of routes) {
      const consoleErrors = []
      const serverErrors = []
      const onConsole = (message) => {
        if (message.type() === 'error') consoleErrors.push(message.text())
      }
      const onPageError = (error) => consoleErrors.push(`pageerror: ${error.message}`)
      const onResponse = (response) => {
        if (response.status() >= 500) serverErrors.push(`${response.status()} ${response.url()}`)
      }

      page.on('console', onConsole)
      page.on('pageerror', onPageError)
      page.on('response', onResponse)

      try {
        const response = await page.goto(`${baseUrl}${route}`, {
          waitUntil: 'domcontentloaded',
          timeout: 45_000,
        })
        if (!response || response.status() >= 500) {
          failures.push(`${viewport.name} ${route}: HTTP ${response?.status() ?? 'no response'}`)
        }

        await page.locator('main').waitFor({ state: 'visible', timeout: 20_000 })
        await page.waitForTimeout(500)

        const sapIconLeaks = await page.locator('.nx-sap-tree__link-icon:visible').evaluateAll((icons) =>
          icons.flatMap((icon) => {
            const text = (icon.textContent ?? '').trim()
            return icon.querySelector('svg.nx-icon') && !text ? [] : [text || 'missing SVG']
          }),
        )
        if (sapIconLeaks.length) {
          failures.push(`${viewport.name} ${route}: SAP IconName leakage ${sapIconLeaks.join(', ')}`)
        }

        const bodyText = await page.locator('body').innerText()
        if (bodyText.includes('Application error')) {
          failures.push(`${viewport.name} ${route}: Application error visible`)
        }

        const overflow = await page.evaluate(() => ({
          scrollWidth: document.documentElement.scrollWidth,
          clientWidth: document.documentElement.clientWidth,
        }))
        if (overflow.scrollWidth > overflow.clientWidth + 1) {
          failures.push(
            `${viewport.name} ${route}: document overflow ${overflow.scrollWidth} > ${overflow.clientWidth}`,
          )
        }

        await page.screenshot({
          path: path.join(outputDir, `${name}--${viewport.name}.png`),
          fullPage: true,
        })

        for (const error of consoleErrors) {
          failures.push(`${viewport.name} ${route}: console ${error}`)
        }
        for (const error of serverErrors) {
          failures.push(`${viewport.name} ${route}: ${error}`)
        }
      } catch (error) {
        failures.push(`${viewport.name} ${route}: ${error instanceof Error ? error.message : String(error)}`)
        await page
          .screenshot({
            path: path.join(outputDir, `${name}--${viewport.name}--failed.png`),
            fullPage: true,
          })
          .catch(() => {})
      } finally {
        page.off('console', onConsole)
        page.off('pageerror', onPageError)
        page.off('response', onResponse)
      }
    }
  }
} finally {
  await browser.close()
}

if (failures.length) {
  console.error('Production visual smoke failures:')
  for (const failure of failures) console.error(`- ${failure}`)
  process.exit(1)
}

console.log(`Production visual smoke passed: ${routes.length} routes × ${viewports.length} viewports`)
