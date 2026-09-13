import { expect, test, type Page } from '@playwright/test'

/**
 * P0 — Cuota contractual vencida debe mostrar Pagar/Liquidar en el Plan de pagos.
 *
 * Caso canónico:
 *   Contrato con plan de pagos mensual desde mes anterior (OVERDUE)
 *   Cuota actual: payableNow=true, botones Pagar y Liquidar visibles
 *   Cuotas futuras: payableNow=false, sin botones activos
 */

const ADMIN_EMAIL = 'admin@nexora.group'
const ADMIN_PASSWORD = 'NexoraAdmin123!'

async function login(page: Page) {
  await page.goto('/login')
  await page.getByLabel('Correo electrónico').fill(ADMIN_EMAIL)
  await page.getByLabel('Contraseña').fill(ADMIN_PASSWORD)
  await page.getByRole('button', { name: /iniciar sesión/i }).click()
  await expect(page).toHaveURL(/\/inicio/, { timeout: 15_000 })
}

async function unlockProtectedEdit(page: Page) {
  await page.getByRole('button', { name: 'Edición protegida' }).click()
  const dialog = page.getByRole('dialog', { name: 'Desbloquear edición' })
  await dialog.getByLabel('Token de seguridad').fill(process.env.E2E_EDIT_ACCESS_TOKEN!)
  await dialog.getByRole('button', { name: 'Desbloquear', exact: true }).click()
  await expect(dialog).not.toBeVisible()
}

async function ensureCompany(page: Page) {
  const capability = await page.evaluate(() =>
    window.sessionStorage.getItem('nexora.edit-access.capability'),
  )
  expect(capability).toBeTruthy()
  const created = await page.request.post('/api/master-data/companies', {
    headers: { 'X-Nexora-Edit-Access': capability! },
    data: { name: 'Compañía E2E Overdue', functionalCurrencyCode: 'HNL' },
  })
  expect(created.ok(), await created.text()).toBeTruthy()
  const company = (await created.json()) as { id: string }
  await page.evaluate((companyId) => {
    window.localStorage.setItem('nexora.activeCompanyId', companyId)
  }, company.id)
  await page.reload()
  await expect(page).toHaveURL(/\/inicio/)
  return { companyId: company.id, capability }
}

test('P0 — Cuota vencida: Pagar/Liquidar en Plan de pagos', async ({ page }) => {
  let companyId = ''
  let capability = ''
  let contractId = ''
  let scheduleId = ''

  await test.step('login + protected edit + company', async () => {
    await login(page)
    await unlockProtectedEdit(page)
    const result = await ensureCompany(page)
    companyId = result.companyId
    capability = result.capability
  })

  await test.step('crear proveedor, contrato y plan de pagos', async () => {
    // Crear proveedor
    const supplier = await page.request.post('/api/procurement/suppliers', {
      headers: { 'X-Nexora-Edit-Access': capability },
      data: { companyId, legalName: 'Proveedor E2E Overdue', taxId: 'OVD-001', supplierType: 'CONTRACTOR' },
    })
    expect(supplier.ok(), await supplier.text()).toBeTruthy()
    const supplierId = (await supplier.json()).id

    // Calcular primer período = mes anterior al actual (para que la 1a cuota sea OVERDUE)
    const today = new Date()
    const prevMonth = new Date(today.getFullYear(), today.getMonth() - 1, 1)
    const firstPeriod = prevMonth.toISOString().slice(0, 7) // YYYY-MM

    // Crear contrato con anticipo
    const contract = await page.request.post('/api/procurement/suppliers/contracts', {
      headers: { 'X-Nexora-Edit-Access': capability },
      data: {
        companyId,
        supplierId,
        contractNumber: 'OVD-10101960',
        contractCategory: 'OTHER',
        scopeDescription: 'Contrato E2E cuota vencida',
        value: '1500000.00',
        currencyCode: 'HNL',
        startDate: prevMonth.toISOString().slice(0, 10),
        advanceAmount: '50000.00',
        advanceDueDate: new Date(today.getFullYear(), today.getMonth() - 2, 1).toISOString().slice(0, 10),
        retentionPercentage: '10',
      },
    })
    expect(contract.ok(), await contract.text()).toBeTruthy()
    contractId = (await contract.json()).id

    // Crear plan de pagos canónico (anticipo + N mensualidades)
    const schedule = await page.request.post('/api/contract-payments/schedules', {
      headers: { 'X-Nexora-Edit-Access': capability },
      data: {
        companyId,
        supplierContractId: contractId,
        scheduleType: 'MONTHLY',
        regularMonths: 7,
        dueDay: 1,
        firstPeriod: `${firstPeriod}-01`,
        advanceAmount: '50000.00',
        advanceDueDate: new Date(today.getFullYear(), today.getMonth() - 2, 1).toISOString().slice(0, 10),
      },
    })
    expect(schedule.ok(), await schedule.text()).toBeTruthy()
    scheduleId = (await schedule.json()).id
  })

  await test.step('abrir Plan y obligaciones → cuota vencida muestra Pagar y Liquidar', async () => {
    await page.goto('/abastecimiento/contratos')
    await expect(page.getByText('OVD-10101960')).toBeVisible({ timeout: 15_000 })

    const row = page.locator('tr, [role="row"]').filter({ hasText: 'OVD-10101960' }).first()
    const planButton = row.getByRole('button', { name: /plan y obligaciones/i })
    await planButton.click()

    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible({ timeout: 8_000 })
    await expect(page.getByText(/Plan de pagos/)).toBeVisible()

    const table = dialog.locator('.nx-table, table').first()
    await expect(table).toBeVisible({ timeout: 10_000 })

    // Buscar la primera fila de cuota MENSUALIDAD (la 1a mensualidad debería ser OVERDUE)
    const mensualidadRows = table.locator('tr').filter({ hasText: /Mensualidad/i })
    const count = await mensualidadRows.count()
    expect(count).toBeGreaterThan(0)

    // Tomar la primera fila MENSUALIDAD y verificar que muestra botones Pagar/Liquidar
    const firstMensualidadRow = mensualidadRows.first()
    await expect(firstMensualidadRow).toBeVisible({ timeout: 5_000 })

    // Debe tener botones Pagar y Liquidar (porque payableNow=true para la 1a cuota vencida)
    await expect(firstMensualidadRow.getByRole('button', { name: /Pagar/i })).toBeVisible()
    await expect(firstMensualidadRow.getByRole('button', { name: /Liquidar/i })).toBeVisible()
  })

  await test.step('cuota UPCOMING no muestra Pagar ni Liquidar activos', async () => {
    await page.goto('/abastecimiento/contratos')
    await expect(page.getByText('OVD-10101960')).toBeVisible({ timeout: 15_000 })

    const row = page.locator('tr, [role="row"]').filter({ hasText: 'OVD-10101960' }).first()
    const planButton = row.getByRole('button', { name: /plan y obligaciones/i })
    await planButton.click()

    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible({ timeout: 8_000 })

    const table = dialog.locator('.nx-table, table').first()
    await expect(table).toBeVisible({ timeout: 10_000 })

    // Buscar filas MENSUALIDAD - la primera y segunda (Ago/Sep) están vencidas, la tercera (Oct) es UPCOMING
    const mensualidadRows = table.locator('tr').filter({ hasText: /Mensualidad/i })
    const count = await mensualidadRows.count()
    expect(count).toBeGreaterThan(2)

    // La tercera fila MENSUALIDAD (cuota #3, Octubre) debería ser UPCOMING y NO tener botones activos
    const thirdMensualidadRow = mensualidadRows.nth(2)
    await expect(thirdMensualidadRow).toBeVisible({ timeout: 5_000 })

    const payBtn = thirdMensualidadRow.getByRole('button', { name: /Pagar/i })
    const liquidarBtn = thirdMensualidadRow.getByRole('button', { name: /Liquidar/i })

    if (await payBtn.count() > 0) {
      await expect(payBtn).toBeDisabled()
    }
    if (await liquidarBtn.count() > 0) {
      await expect(liquidarBtn).toBeDisabled()
    }
    // O debe mostrar texto "Próxima" en lugar de botones
    const proximaText = thirdMensualidadRow.getByText(/Próxima/i)
    const hasProxima = await proximaText.count() > 0
    const hasDisabledPay = (await payBtn.count() > 0) && await payBtn.isDisabled()
    expect(hasProxima || hasDisabledPay).toBeTruthy()
  })

  await test.step('verificar via API que payableNow=true para OVERDUE y payableNow=false para UPCOMING', async () => {
    if (!scheduleId) {
      test.skip()
      return
    }
    const schedule = await page.request.get(`/api/contract-payments/by-contract/${contractId}`, {
      headers: { 'X-Nexora-Edit-Access': capability },
    })
    expect(schedule.ok(), await schedule.text()).toBeTruthy()
    const data = await schedule.json()
    const installments = data.installments ?? []

    // Cuotas OVERDUE/DUE deben ser payableNow=true
    const overdue = installments.filter((i: any) => i.status === 'OVERDUE' || i.status === 'DUE')
    for (const i of overdue) {
      expect(i.payableNow, `Installment ${i.installmentId} (${i.status}) must have payableNow=true`).toBe(true)
    }

    // Cuotas UPCOMING deben ser payableNow=false
    const upcoming = installments.filter((i: any) => i.status === 'UPCOMING')
    for (const i of upcoming) {
      expect(i.payableNow, `Installment ${i.installmentId} (UPCOMING) must have payableNow=false`).toBe(false)
    }
  })

  await test.step('resumen canónico — saldo acumulado refleja anticipo', async () => {
    if (!scheduleId) {
      test.skip()
      return
    }
    const summary = await page.request.get(`/api/contract-payments/schedules/${scheduleId}/summary`, {
      headers: { 'X-Nexora-Edit-Access': capability },
    })
    expect(summary.ok(), await summary.text()).toBeTruthy()
    const data = await summary.json()
    expect(Number(data.contractValue)).toBeCloseTo(1500000, 0)
    expect(Number(data.advanceScheduled)).toBeCloseTo(50000, 0)
  })
})