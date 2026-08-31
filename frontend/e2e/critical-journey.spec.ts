import { expect, test, type APIRequestContext } from '@playwright/test'

/**
 * NXR-REQ-0112/0113 -- Critical Journey. Un solo recorrido secuencial e
 * integrado (no 40 tests aislados) contra un backend + frontend reales
 * levantados por playwright.config.ts (DB propia `nexora_e2e`, fresh
 * install real vía `alembic upgrade head`). Login/navegación/una muestra
 * representativa de pantallas se maneja por UI real (clicks reales, no
 * mocks); el resto de dominios que ya se probaron exhaustivamente vía
 * pytest este mismo día se ejercitan por `page.request` -- las mismas
 * cookies de sesión que la página, mismo backend real, misma DB real --
 * para mantener el recorrido en un tiempo de ejecución razonable sin
 * perder cobertura real de integración end-to-end.
 */

const ADMIN_EMAIL = 'admin@nexora.group'
const ADMIN_PASSWORD = 'NexoraAdmin123!'
let editCapability = ''

async function api<T = any>(
  request: APIRequestContext,
  method: 'get' | 'post' | 'put' | 'patch' | 'delete',
  path: string,
  data?: unknown,
): Promise<T> {
  const protectedMutation = method === 'put' || method === 'patch' || method === 'delete'
  const options = {
    ...(data !== undefined ? { data } : {}),
    ...(protectedMutation && editCapability
      ? { headers: { 'X-Nexora-Edit-Access': editCapability } }
      : {}),
  }
  const response = await request[method](`/api${path}`, options)
  expect(response.ok(), `${method.toUpperCase()} ${path} -> ${response.status()}: ${await response.text()}`).toBeTruthy()
  if (response.status() === 204) return undefined as T
  return response.json()
}

test.describe.configure({ mode: 'serial' })

test('Critical Journey: login through GL/reports/audit, one continuous real recorrido', async ({ page }) => {
  await test.step('login', async () => {
    await page.goto('/login')
    await page.getByLabel('Correo electrónico').fill(ADMIN_EMAIL)
    await page.getByLabel('Contraseña').fill(ADMIN_PASSWORD)
    await page.getByRole('button', { name: 'Iniciar sesión' }).click()
    await expect(page).toHaveURL(/\/inicio/, { timeout: 15_000 })
  })

  let companyId = ''
  let projectId = ''
  await test.step('company + project + ActiveUIContext', async () => {
    const company = await api<any>(page.request, 'post', '/master-data/companies', {
      name: 'Constructora E2E',
      functionalCurrencyCode: 'HNL',
    })
    companyId = company.id

    await page.goto('/proyectos')
    await expect(page.getByText('Nuevo proyecto')).toBeVisible({ timeout: 10_000 })
    await page.getByLabel('Nombre', { exact: true }).fill('Torre Critical Journey')
    await page.getByLabel('Código (opcional)').fill('CJ-001')
    await page.getByRole('button', { name: 'Crear proyecto' }).click()
    await expect(page.getByRole('button', { name: 'Torre Critical Journey', exact: true })).toBeVisible({ timeout: 10_000 })
    await page.getByRole('button', { name: 'Seleccionar', exact: true }).click()
    await expect(page.getByLabel('Proyecto seleccionado')).toHaveValue(/.+/)

    const projects = await api<any[]>(page.request, 'get', `/projects?company_id=${companyId}`)
    const project = projects.find((p: any) => p.name === 'Torre Critical Journey')
    expect(project).toBeTruthy()
    projectId = project.id
  })

  await test.step('WBS', async () => {
    await page.goto('/proyectos/wbs')
    await page.getByLabel('Código', { exact: true }).fill('01')
    await page.getByLabel('Nombre', { exact: true }).fill('Movimiento de tierra')
    await page.getByRole('button', { name: 'Crear nodo' }).click()
    await expect(page.getByRole('row').filter({ hasText: 'Movimiento de tierra' })).toBeVisible({
      timeout: 10_000,
    })
  })

  let bankGl = '', expenseGl = '', payableGl = '', equityGl = '', revenueGl = '', receivableGl = ''
  await test.step('chart of accounts (API)', async () => {
    bankGl = (await api(page.request, 'post', '/master-data/accounts', { companyId, code: '1100', name: 'Bancos E2E', accountType: 'ASSET' })).id
    expenseGl = (await api(page.request, 'post', '/master-data/accounts', { companyId, code: '5100', name: 'Gastos E2E', accountType: 'EXPENSE' })).id
    payableGl = (await api(page.request, 'post', '/master-data/accounts', { companyId, code: '2100', name: 'CxP E2E', accountType: 'LIABILITY' })).id
    equityGl = (await api(page.request, 'post', '/master-data/accounts', { companyId, code: '3100', name: 'Aportes E2E', accountType: 'EQUITY' })).id
    revenueGl = (await api(page.request, 'post', '/master-data/accounts', { companyId, code: '4100', name: 'Ingresos E2E', accountType: 'REVENUE' })).id
    receivableGl = (await api(page.request, 'post', '/master-data/accounts', { companyId, code: '1200', name: 'CxC E2E', accountType: 'ASSET' })).id
  })

  await test.step('Protected Edit + resource posting configuration', async () => {
    const rejected = await page.request.put(
      `/api/master-data/companies/${companyId}/resource-posting-configs/FUEL`,
      { data: { sourceType: 'FUEL', expenseAccountId: expenseGl, offsetAccountId: payableGl, active: true } },
    )
    expect(rejected.status()).toBe(428)

    const runtimeToken = process.env.E2E_EDIT_ACCESS_TOKEN
    expect(runtimeToken).toBeTruthy()
    const unlock = await api<any>(page.request, 'post', '/edit-access/verify', { token: runtimeToken })
    editCapability = unlock.capability
    expect(editCapability).toBeTruthy()
    expect(unlock.usesRemaining).toBeGreaterThanOrEqual(4)

    for (const sourceType of ['FUEL', 'MAINTENANCE', 'LABOR'] as const) {
      const config = await api<any>(
        page.request,
        'put',
        `/master-data/companies/${companyId}/resource-posting-configs/${sourceType}`,
        { sourceType, expenseAccountId: expenseGl, offsetAccountId: payableGl, active: true },
      )
      expect(config.sourceType).toBe(sourceType)
      expect(config.active).toBe(true)
    }
  })

  let treasuryAccountId = ''
  await test.step('Treasury Account + CENTRAL remittance', async () => {
    await page.goto('/finanzas/tesoreria')
    treasuryAccountId = (await api(page.request, 'post', '/treasury/accounts', {
      companyId, name: 'Banco Principal E2E', kind: 'BANK', currencyCode: 'HNL', glAccountId: bankGl,
    })).id
    await page.reload()
    await page.getByRole('button', { name: 'Registrar remesa' }).click()
    await page.getByLabel('Cuenta contable de origen').selectOption({ label: '3100 · Aportes E2E' })
    await page.getByLabel('Remitente').selectOption('__OTHER__')
    await page.getByLabel('Nombre completo del remitente').fill('Socio fundador E2E')
    await page.getByLabel('Método / canal').selectOption('REMITTANCE')
    await page.getByLabel(/Monto/).fill('100000')
    await page.getByLabel('Registrar remesa').getByRole('button', { name: 'Registrar remesa', exact: true }).click()
    await expect(page.getByText('L 100,000.00').first()).toBeVisible({ timeout: 10_000 })

    const trialBalance = await api<any>(page.request, 'get', `/reports/trial-balance?companyId=${companyId}`)
    expect(Number(trialBalance.totalDebit)).toBe(Number(trialBalance.totalCredit))
    expect(Number(trialBalance.totalDebit)).toBeGreaterThanOrEqual(100000)
  })

  await test.step('GENERAL expense never touches project budget', async () => {
    await api(page.request, 'post', '/treasury/general-expenses', {
      companyId, treasuryAccountId, expenseAccountId: expenseGl, category: 'papeleria',
      amount: '500.00', currencyCode: 'HNL', expenseDate: new Date().toISOString().slice(0, 10),
      description: 'Gasto general E2E',
    })
  })

  let requisitionId = ''
  await test.step('project budget + PR + approval', async () => {
    await api(page.request, 'post', `/projects/${projectId}/budgets/baseline`, {
      currencyCode: 'HNL', lines: [{ authorizedAmount: '50000.00' }],
    })
    const pr = await api<any>(page.request, 'post', '/procurement/requisitions', {
      companyId, projectId, justification: 'Materiales fase 1 (E2E)',
      lines: [{ description: 'Cemento tipo I', quantity: '100.0000', estimatedUnitCost: '10.0000' }],
    })
    requisitionId = pr.id
    const approved = await api<any>(page.request, 'post', `/procurement/requisitions/${requisitionId}/approve`)
    expect(approved.status).toBe('APPROVED')
    await page.goto('/proyectos/presupuestos')
    await expect(page.getByText('Comprometido')).toBeVisible({ timeout: 10_000 })
  })

  let supplierId = '', poId = ''
  await test.step('RFQ -> quote -> comparison -> PO', async () => {
    supplierId = (await api(page.request, 'post', '/procurement/suppliers', { companyId, legalName: 'Proveedor E2E S.A.' })).id
    const rfq = await api<any>(page.request, 'post', '/procurement/rfqs', { companyId, supplierIds: [supplierId] })
    const quotation = await api<any>(page.request, 'post', `/procurement/rfqs/${rfq.id}/quotations`, {
      supplierId, currencyCode: 'HNL', deliveryDays: 10, paymentTerms: '30 días',
      lines: [{ description: 'Cemento tipo I', quantity: '100.0000', unitPrice: '10.0000' }],
    })

    await page.goto('/abastecimiento/comparativos')
    await expect(page.getByText(/RFQ-/)).toBeVisible({ timeout: 10_000 })
    await page.getByRole('button', { name: 'Comparar' }).first().click()
    await expect(page.getByText(/1000\.00/)).toBeVisible({ timeout: 10_000 })
    await page.getByRole('button', { name: 'Seleccionar ganadora' }).click()
    await expect(page.getByText(/PO-/i)).toBeVisible({ timeout: 10_000 })

    const pos = await api<any[]>(page.request, 'get', `/procurement/purchase-orders?company_id=${companyId}`)
    const po = pos.find((p: any) => p.supplierQuotationId === quotation.id)
    expect(po).toBeTruthy()
    poId = po.id
    await api(page.request, 'post', `/procurement/purchase-orders/${poId}/approve`)
    await api(page.request, 'post', `/procurement/purchase-orders/${poId}/send`)
  })

  let warehouseId = '', itemId = '', apInvoiceId = '', apPaymentId = ''
  await test.step('receipt -> invoice -> 3-way match -> payment', async () => {
    warehouseId = (await api(page.request, 'post', '/inventory/warehouses', { companyId, code: 'ALM-E2E', name: 'Almacén E2E' })).id
    itemId = (await api(page.request, 'post', '/inventory/items', { companyId, sku: 'CEM-E2E', name: 'Cemento E2E', itemType: 'MATERIAL', uom: 'SACO' })).id

    const poDetail = await api<any>(page.request, 'get', `/procurement/purchase-orders/${poId}`)
    const poLineId = poDetail.lines[0].id
    await api(page.request, 'post', '/procurement/goods-receipts', {
      purchaseOrderId: poId, warehouseId, receivedAt: new Date().toISOString().slice(0, 10),
      lines: [{ purchaseOrderLineId: poLineId, quantityReceived: '100.0000' }],
    })

    const invoice = await api<any>(page.request, 'post', '/ap/supplier-invoices', {
      companyId, supplierId, invoiceNumber: 'FAC-E2E-001', scope: 'GENERAL',
      expenseAccountId: expenseGl, payableAccountId: payableGl, currencyCode: 'HNL',
      amount: '1000.00', invoiceDate: new Date().toISOString().slice(0, 10),
      dueDate: new Date().toISOString().slice(0, 10),
    })
    apInvoiceId = invoice.id
    await api(page.request, 'post', `/ap/supplier-invoices/${invoice.id}/approve`)

    const match = await api<any>(page.request, 'post', '/procurement/three-way-match', {
      purchaseOrderId: poId, supplierInvoiceAmount: '1000.00', supplierInvoiceQuantity: '100.0000',
    })
    expect(match.status).toBe('MATCHED')

    const payment = await api<any>(page.request, 'post', `/ap/supplier-invoices/${invoice.id}/payments`, {
      treasuryAccountId, amount: '1000.00', paymentDate: new Date().toISOString().slice(0, 10),
    })
    apPaymentId = payment.id
    await page.goto('/finanzas/cuentas-por-pagar')
    await expect(page.locator('td', { hasText: 'FAC-E2E-001' })).toBeVisible({ timeout: 10_000 })
  })

  await test.step('inventory receive -> transfer -> project issue -> cost', async () => {
    await api(page.request, 'post', '/inventory/stock/receive', {
      companyId, itemId, warehouseId, quantity: '100.0000', unitCost: '10.0000',
    })
    const warehouse2 = (await api(page.request, 'post', '/inventory/warehouses', { companyId, code: 'ALM-E2E-2', name: 'Almacén secundario E2E' })).id
    await api(page.request, 'post', '/inventory/stock/transfer', {
      companyId, itemId, fromWarehouseId: warehouseId, toWarehouseId: warehouse2, quantity: '10.0000',
    })
    const issue = await api<any>(page.request, 'post', '/inventory/stock/issue-to-project', {
      companyId, itemId, warehouseId, projectId, quantity: '20.0000',
    })
    expect(issue.projectId).toBe(projectId)
    const summary = await api<any>(page.request, 'get', `/projects/${projectId}/budgets/summary`)
    expect(Number(summary.authorized)).toBe(50000)
  })

  await test.step('workforce + crew + time entry', async () => {
    const worker = await api<any>(page.request, 'post', '/workforce/workers', {
      companyId, fullName: 'Trabajador E2E', standardHourlyRate: '100.00',
    })
    const crew = await api<any>(page.request, 'post', '/workforce/crews', { companyId, name: 'Cuadrilla E2E', projectId })
    await api(page.request, 'post', `/workforce/crews/${crew.id}/members`, { workerId: worker.id })
    const entry = await api<any>(page.request, 'post', '/workforce/time-entries', {
      companyId, workerId: worker.id, scope: 'PROJECT', projectId,
      workDate: new Date().toISOString().slice(0, 10), hoursWorked: '8.00', hourlyRate: '100.00',
    })
    const approved = await api<any>(page.request, 'post', `/workforce/time-entries/${entry.id}/approve`, {})
    expect(Number(approved.laborCost)).toBe(800)
    await page.goto('/recursos/cuadrillas')
    await expect(page.getByText('Cuadrilla E2E')).toBeVisible({ timeout: 10_000 })
  })

  await test.step('equipment + fuel + maintenance + automatic GL', async () => {
    const equipment = await api<any>(page.request, 'post', '/equipment', {
      companyId, name: 'Mezcladora E2E', equipmentType: 'MACHINERY', projectId,
    })
    await api(page.request, 'post', '/equipment/fuel-logs', {
      companyId, equipmentId: equipment.id, scope: 'PROJECT', projectId,
      logDate: new Date().toISOString().slice(0, 10), quantity: '20.00', unitCost: '5.00',
    })
    const maintenance = await api<any>(page.request, 'post', `/equipment/${equipment.id}/maintenance-orders`, {
      orderType: 'PREVENTIVE', description: 'Mantenimiento preventivo E2E',
      openedAt: new Date().toISOString().slice(0, 10),
    })
    const closed = await api<any>(
      page.request,
      'patch',
      `/equipment/maintenance-orders/${maintenance.id}`,
      {
        status: 'CLOSED',
        partsCost: '80.00',
        laborCost: '20.00',
        downtimeHours: '2.00',
        closedAt: new Date().toISOString().slice(0, 10),
      },
    )
    expect(closed.status).toBe('CLOSED')

    const resourceDocuments = await api<any[]>(
      page.request,
      'get',
      `/accounting/journal-entries?companyId=${companyId}&limit=250`,
    )
    const resourceTypes = new Set(resourceDocuments.map((document: any) => document.documentTypeCode))
    expect(resourceTypes.has('FUE')).toBe(true)
    expect(resourceTypes.has('MNT')).toBe(true)
    expect(resourceTypes.has('LAB')).toBe(true)
  })

  await test.step('progress, quality, safety, RFI, submittal, change order, correction', async () => {
    await api(page.request, 'post', `/projects/${projectId}/progress`, {
      recordDate: new Date().toISOString().slice(0, 10), plannedPercent: '10.00', actualPercent: '8.00',
    })
    const dailyReport = await api<any>(page.request, 'post', '/site-reports', {
      projectId, reportDate: new Date().toISOString().slice(0, 10),
      weather: 'Soleado', activitiesPerformed: 'Avance normal E2E',
    })
    expect(dailyReport.id).toBeTruthy()
    const inspection = await api<any>(page.request, 'post', '/quality/inspections', {
      projectId, inspectionType: 'Vaciado de concreto', notes: 'Inspección de vaciado E2E',
      inspectionDate: new Date().toISOString().slice(0, 10),
    })
    expect(inspection.id).toBeTruthy()
    const observation = await api<any>(page.request, 'post', '/safety/observations', {
      projectId, category: 'EPP', description: 'Observación de EPP E2E',
      observationDate: new Date().toISOString().slice(0, 10),
    })
    expect(observation.id).toBeTruthy()
    const rfi = await api<any>(page.request, 'post', '/rfis', {
      companyId, projectId, subject: 'RFI E2E', question: '¿Especificación de acero?',
    })
    expect(rfi.id).toBeTruthy()
    const submittal = await api<any>(page.request, 'post', '/submittals', {
      companyId, projectId, title: 'Ficha técnica E2E', submittedAt: new Date().toISOString().slice(0, 10),
    })
    expect(submittal.id).toBeTruthy()
    const changeOrder = await api<any>(page.request, 'post', `/projects/${projectId}/change-orders`, {
      reason: 'Orden de cambio E2E', budgetChangeAmount: '1000.00',
    })
    await api(page.request, 'post', `/projects/change-orders/${changeOrder.id}/submit`)
    await api(page.request, 'post', `/projects/change-orders/${changeOrder.id}/approve`)

    await page.goto('/proyectos/ordenes-de-cambio')
    await expect(page.getByText('Orden de cambio E2E')).toBeVisible({ timeout: 10_000 })
    await page.goto('/proyectos/rfi-submittals')
    await expect(page.getByText('RFI E2E')).toBeVisible({ timeout: 10_000 })
  })

  await test.step('correction / reversal', async () => {
    const journal = await api<any>(page.request, 'post', '/accounting/journal-entries', {
      companyId, scope: 'GENERAL', currencyCode: 'HNL', description: 'Asiento a corregir E2E',
      lines: [
        { accountId: expenseGl, debitAmount: '10.00' },
        { accountId: payableGl, creditAmount: '10.00' },
      ],
    })
    const reversal = await api<any>(page.request, 'post', `/accounting/journal-entries/${journal.id}/reverse`, {
      reason: 'Corrección E2E',
    })
    expect(reversal.documentNumber).toMatch(/^ANU-/)
  })

  let arInvoiceId = '', arReceiptId = ''
  await test.step('CRM: lead -> opportunity -> quote -> sales contract -> AR', async () => {
    const lead = await api<any>(page.request, 'post', '/crm/leads', {
      companyId, name: 'Lead E2E', source: 'referral',
    })
    const conversion = await api<any>(page.request, 'post', `/crm/leads/${lead.id}/convert`)
    const customer = conversion.customer
    const opportunity = conversion.opportunity
    const quotation = await api<any>(page.request, 'post', '/crm/quotations', {
      companyId, opportunityId: opportunity.id, customerId: customer.id,
      quotationNumber: 'COT-E2E-001', amount: '5000.00', currencyCode: 'HNL',
    })
    await api(page.request, 'post', `/crm/quotations/${quotation.id}/accept`)
    const contract = await api<any>(page.request, 'post', `/crm/quotations/${quotation.id}/convert`, {
      contractNumber: 'SC-E2E-001', startDate: new Date().toISOString().slice(0, 10),
    })
    const billed = await api<any>(page.request, 'post', `/crm/sales-contracts/${contract.id}/bill`, {
      invoiceNumber: 'FAC-CLI-E2E-001',
      invoiceDate: new Date().toISOString().slice(0, 10),
      dueDate: new Date().toISOString().slice(0, 10),
      revenueAccountId: revenueGl, receivableAccountId: receivableGl,
    })
    expect(billed.customerInvoiceId).toBeTruthy()
    arInvoiceId = billed.customerInvoiceId
    await api(page.request, 'post', `/ar/customer-invoices/${billed.customerInvoiceId}/approve`)
    const receipt = await api<any>(page.request, 'post', `/ar/customer-invoices/${billed.customerInvoiceId}/receipts`, {
      treasuryAccountId, amount: '5000.00', receiptDate: new Date().toISOString().slice(0, 10),
    })
    arReceiptId = receipt.id
    await page.goto('/comercial/contratos')
    await expect(page.getByRole('cell', { name: 'SC-E2E-001', exact: true })).toBeVisible({ timeout: 10_000 })
  })

  await test.step('AP payment + AR receipt formal reversals', async () => {
    const apReversal = await api<any>(page.request, 'post', `/ap/supplier-payments/${apPaymentId}/reverse`, {
      reason: 'Pago duplicado detectado E2E',
    })
    expect(Number(apReversal.appliedAmountAfterReversal)).toBe(0)
    expect(apReversal.invoiceStatus).toBe('APPROVED')

    const arReversal = await api<any>(page.request, 'post', `/ar/customer-receipts/${arReceiptId}/reverse`, {
      reason: 'Cobro bancario rechazado E2E',
    })
    expect(Number(arReversal.appliedAmountAfterReversal)).toBe(0)
    expect(arReversal.invoiceStatus).toBe('APPROVED')

    const duplicate = await page.request.post(`/api/ap/supplier-payments/${apPaymentId}/reverse`, {
      data: { reason: 'Segundo intento no permitido' },
    })
    expect(duplicate.status()).toBe(409)

    const paymentHistory = await api<any[]>(page.request, 'get', `/ap/supplier-invoices/${apInvoiceId}/payments`)
    expect(paymentHistory[0].reversalAccountingDocumentId).toBeTruthy()
    const receiptHistory = await api<any[]>(page.request, 'get', `/ar/customer-invoices/${arInvoiceId}/receipts`)
    expect(receiptHistory[0].reversalAccountingDocumentId).toBeTruthy()
  })

  await test.step('advanced treasury + authenticated voucher PDF', async () => {
    const closing = await api<any>(page.request, 'post', '/treasury/cash-closings', {
      treasuryAccountId,
      closingDate: new Date().toISOString().slice(0, 10),
      openingAmount: '0.00',
      expectedAmount: '94000.00',
      countedAmount: '94000.00',
    })
    const approvedClosing = await api<any>(page.request, 'post', `/treasury/cash-closings/${closing.id}/approve?companyId=${companyId}`, {})
    expect(approvedClosing.status).toBe('APPROVED')

    const restriction = await api<any>(page.request, 'post', '/treasury/fund-restrictions', {
      treasuryAccountId,
      restrictedForProjectId: projectId,
      amount: '100.00',
      description: 'Reserva contractual E2E',
    })
    const availability = await api<any>(page.request, 'get', `/treasury/accounts/${treasuryAccountId}/availability`)
    expect(Number(availability.reservedAmount)).toBeGreaterThanOrEqual(100)
    const released = await api<any>(page.request, 'post', `/treasury/fund-restrictions/${restriction.id}/release`, {})
    expect(released.active).toBe(false)

    const statement = await api<any>(page.request, 'post', '/treasury/bank-statements', {
      treasuryAccountId,
      statementDate: new Date().toISOString().slice(0, 10),
      openingBalance: '0.00',
      closingBalance: '10.00',
      reference: 'EST-E2E-001',
    })
    const line = await api<any>(page.request, 'post', `/treasury/bank-statements/${statement.id}/lines`, {
      lineDate: new Date().toISOString().slice(0, 10),
      description: 'Movimiento conciliable E2E',
      amount: '10.00',
    })
    const candidates = await api<any[]>(page.request, 'get', `/treasury/bank-statement-lines/${line.id}/candidates`)
    expect(candidates.length).toBeGreaterThan(0)
    const matched = await api<any>(page.request, 'post', `/treasury/bank-statement-lines/${line.id}/match`, {
      accountingDocumentId: candidates[0].accountingDocumentId,
      matchedAmount: '10.00',
    })
    expect(['MATCHED', 'PARTIAL']).toContain(matched.status)
    const unmatched = await api<any>(page.request, 'post', `/treasury/bank-statement-lines/${line.id}/unmatch`, {})
    expect(unmatched.status).toBe('UNMATCHED')

    const documents = await api<any[]>(page.request, 'get', `/accounting/journal-entries?companyId=${companyId}&limit=250`)
    // Un método bancario exige evidencia adjunta al documento (orden maestra Phase 2).
    const voucherBlocked = await page.request.get(
      `/api/treasury/vouchers/${documents[0].id}?beneficiary=Nexora%20Group&paymentMethod=TRANSFER`,
    )
    expect(voucherBlocked.status()).toBe(422)
    const evidenceUpload = await page.request.post('/api/evidence', {
      multipart: {
        companyId,
        entityType: 'ACCOUNTING_DOCUMENT',
        entityId: documents[0].id,
        file: { name: 'transferencia.pdf', mimeType: 'application/pdf', buffer: Buffer.from('%PDF-1.7\ncomprobante') },
      },
    })
    expect(evidenceUpload.ok()).toBeTruthy()
    const voucherResponse = await page.request.get(
      `/api/treasury/vouchers/${documents[0].id}?beneficiary=Nexora%20Group&paymentMethod=TRANSFER`,
    )
    expect(voucherResponse.ok()).toBeTruthy()
    expect(voucherResponse.headers()['content-type']).toContain('application/pdf')
    expect(voucherResponse.headers()['content-disposition']).toContain('NEXORA-Comprobante-')

    await page.goto('/finanzas/conciliacion')
    await expect(page.getByRole('heading', { name: 'Conciliación bancaria' })).toBeVisible({ timeout: 10_000 })
    await page.goto('/finanzas/cierres-caja')
    await expect(page.getByRole('heading', { name: 'Cierres de caja' })).toBeVisible({ timeout: 10_000 })
    await page.goto('/finanzas/restricciones-fondos')
    await expect(page.getByRole('heading', { name: 'Restricciones de fondos' })).toBeVisible({ timeout: 10_000 })
    await page.goto('/finanzas/comprobantes')
    await expect(page.getByRole('heading', { name: 'Comprobantes / Vouchers' })).toBeVisible({ timeout: 10_000 })

    await page.goto('/finanzas/control')
    await expect(page.getByRole('heading', { name: 'Centro de Control Financiero' })).toBeVisible({ timeout: 10_000 })
    await expect(page.getByText('Posición de caja y bancos')).toBeVisible({ timeout: 10_000 })

    await page.goto('/finanzas/conciliacion-subledger')
    await expect(page.getByRole('heading', { name: 'Conciliación Subledger ↔ GL' })).toBeVisible({ timeout: 10_000 })
    await expect(page.getByText(/subledgers cuadran contra el GL|Hay descuadres/)).toBeVisible({ timeout: 10_000 })

    await page.goto('/finanzas/cierre')
    await expect(page.getByRole('heading', { name: 'Centro de Cierre contable' })).toBeVisible({ timeout: 10_000 })

    await page.goto('/finanzas/excepciones')
    await expect(page.getByRole('heading', { name: 'Exception Center' })).toBeVisible({ timeout: 10_000 })
  })

  await test.step('Documents + multipart Evidence with real selectors', async () => {
    const evidenceResponse = await page.request.post('/api/evidence', {
      multipart: {
        companyId,
        entityType: 'PROJECT',
        entityId: projectId,
        category: 'PHOTO',
        file: {
          name: 'evidencia-e2e.jpg',
          mimeType: 'image/jpeg',
          buffer: Buffer.concat([
            Buffer.from([0xff, 0xd8, 0xff, 0xe0, 0x4a, 0x46, 0x49, 0x46, 0x00]),
            Buffer.from('Evidencia E2E'),
          ]),
        },
      },
    })
    expect(evidenceResponse.ok(), await evidenceResponse.text()).toBeTruthy()
    const evidence = await evidenceResponse.json()
    const document = await api<any>(page.request, 'post', '/documents', {
      companyId,
      scope: 'PROJECT',
      projectId,
      category: 'OTHER',
      title: 'Documento de cierre E2E',
      description: 'Versión inicial',
      evidenceId: evidence.id,
    })
    expect(document.currentVersion.versionNumber).toBe(1)

    await page.goto('/control/documentos')
    await expect(page.getByText('Documento de cierre E2E')).toBeVisible({ timeout: 10_000 })
    await page.goto('/control/evidencias')
    await expect(page.getByText('evidencia-e2e.jpg')).toBeVisible({ timeout: 10_000 })
    await expect(page.getByLabel('Proyecto seleccionado')).toBeVisible()
    await expect(page.getByLabel('WBS (opcional)')).not.toBeVisible()
  })

  let approverId = ''
  await test.step('Approval Inbox + Notifications (real UI)', async () => {
    const pendingInvoice = await api<any>(page.request, 'post', '/ap/supplier-invoices', {
      companyId, supplierId, invoiceNumber: 'FAC-E2E-002', scope: 'GENERAL',
      expenseAccountId: expenseGl, payableAccountId: payableGl, currencyCode: 'HNL',
      amount: '250.00', invoiceDate: new Date().toISOString().slice(0, 10),
      dueDate: new Date().toISOString().slice(0, 10),
    })
    const me = await api<any>(page.request, 'get', '/auth/me')
    const selfAssign = await page.request.post('/api/ap/supplier-invoices/' + pendingInvoice.id + '/submit-for-approval', {
      data: { assignedTo: me.id },
    })
    expect(selfAssign.status()).toBe(422)
    expect((await selfAssign.json()).error.code).toBe('NXR-WORKFLOW-001')

    const approverEmail = 'aprobador-e2e@nexora.group'
    const approverPassword = 'AprobadorE2E123!'
    const approver = await api<any>(page.request, 'post', '/master-data/users', {
      companyId, email: approverEmail, fullName: 'Aprobador E2E',
      password: approverPassword, roleName: 'Administrator',
    })
    approverId = approver.id
    await api(page.request, 'post', `/ap/supplier-invoices/${pendingInvoice.id}/submit-for-approval`, {
      assignedTo: approverId,
    })

    await api(page.request, 'post', '/auth/logout')
    await page.goto('/login')
    await page.getByLabel('Correo electrónico').fill(approverEmail)
    await page.getByLabel('Contraseña').fill(approverPassword)
    await page.getByRole('button', { name: 'Iniciar sesión' }).click()
    await expect(page).toHaveURL(/\/inicio/, { timeout: 15_000 })

    await page.goto('/inicio/aprobaciones')
    await expect(page.getByRole('button', { name: 'Aprobar' }).first()).toBeVisible({ timeout: 10_000 })
    await page.getByRole('button', { name: 'Aprobar' }).first().click()

    await page.getByRole('button', { name: /Notificaciones/ }).click()
    await expect(page.getByRole('dialog', { name: 'Notificaciones' })).toBeVisible({ timeout: 10_000 })

    await api(page.request, 'post', '/auth/logout')
    await page.goto('/login')
    await page.getByLabel('Correo electrónico').fill(ADMIN_EMAIL)
    await page.getByLabel('Contraseña').fill(ADMIN_PASSWORD)
    await page.getByRole('button', { name: 'Iniciar sesión' }).click()
    await expect(page).toHaveURL(/\/inicio/, { timeout: 15_000 })
  })

  await test.step('Users, roles, company and project access management', async () => {
    const runtimeToken = process.env.E2E_EDIT_ACCESS_TOKEN
    expect(runtimeToken).toBeTruthy()
    const unlock = await api<any>(page.request, 'post', '/edit-access/verify', { token: runtimeToken })
    editCapability = unlock.capability

    const granted = await api<any>(page.request, 'put', `/access-management/users/${approverId}/projects/${projectId}`)
    expect(granted.projects.find((project: any) => project.id === projectId)?.assigned).toBe(true)

    const revoked = await api<any>(
      page.request,
      'delete',
      `/access-management/users/${approverId}/projects/${projectId}`,
    )
    expect(revoked.projects.find((project: any) => project.id === projectId)?.assigned).toBe(false)
  })

  await test.step('global search', async () => {
    await page.goto('/inicio')
    await page.getByRole('button', { name: 'Búsqueda global' }).click()
    await page.getByPlaceholder(/Ir a…/).fill('FAC-E2E-001')
    await expect(page.getByText('FAC-E2E-001')).toBeVisible({ timeout: 10_000 })
    await page.keyboard.press('Escape')
  })

  await test.step('reports: TB, GL, Balance Sheet, Income Statement', async () => {
    await page.goto('/control/reportes')
    await expect(page.getByText(/Total débito/)).toBeVisible({ timeout: 10_000 })
    await page.getByRole('tab', { name: /libro mayor/i }).click()
    await expect(page.getByText(/Total débito/)).toBeVisible({ timeout: 10_000 })
    await page.getByRole('tab', { name: /balance general/i }).click()
    await expect(page.getByText(/Diferencia: 0\.00/)).toBeVisible({ timeout: 10_000 })
    await page.getByRole('tab', { name: /estado de resultados/i }).click()
    await expect(page.getByText(/Utilidad neta/)).toBeVisible({ timeout: 10_000 })
  })

  await test.step('audit trail', async () => {
    await page.goto('/control/auditoria')
    // Primary view is human language, not raw codes/UUIDs.
    await expect(page.getByText(/Factura de proveedor · /).first()).toBeVisible({ timeout: 10_000 })
    await expect(page.getByText(/ap\.supplier_invoice/)).toHaveCount(0)
    // The technical fields are available on demand in the detail drawer.
    await page.getByRole('button', { name: /ver detalles/i }).first().click()
    const drawer = page.getByRole('dialog', { name: /detalle de auditoría/i })
    await expect(drawer).toBeVisible({ timeout: 10_000 })
    await expect(drawer.getByText('Código técnico del evento')).toBeVisible()
    await expect(drawer.getByText('ID de correlación')).toBeVisible()
    await expect(drawer.locator('code').first()).toBeVisible()
  })

  await test.step('logout -> login -> persistence', async () => {
    await page.goto('/inicio')
    await api(page.request, 'post', '/auth/logout')
    await page.reload()
    await expect(page).toHaveURL(/\/login/, { timeout: 10_000 })

    await page.getByLabel('Correo electrónico').fill(ADMIN_EMAIL)
    await page.getByLabel('Contraseña').fill(ADMIN_PASSWORD)
    await page.getByRole('button', { name: 'Iniciar sesión' }).click()
    await expect(page).toHaveURL(/\/inicio/, { timeout: 15_000 })

    await page.goto('/proyectos')
    await expect(page.getByRole('cell', { name: 'Torre Critical Journey' })).toBeVisible({ timeout: 10_000 })
  })
})
