import { afterEach, describe, expect, it, vi } from 'vitest'
import { assetService } from './assetService'

describe('assetService', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('capitalizes an approved supplier invoice through the dedicated API contract', async () => {
    const responseAsset = {
      id: 'asset-1',
      supplierInvoiceId: 'invoice-1',
      capitalizationDocumentId: 'cap-1',
    }
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(responseAsset), {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const result = await assetService.createFromSupplierInvoice('invoice-1', {
      category: 'Maquinaria',
      name: 'Excavadora',
      usefulLifeMonths: 120,
      salvageValue: '100.00',
      assetAccountId: 'account-asset',
      depreciationExpenseAccountId: 'account-expense',
      accumulatedDepreciationAccountId: 'account-accumulated',
    })

    expect(result).toEqual(responseAsset)
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/assets/from-supplier-invoice/invoice-1',
      expect.objectContaining({
        method: 'POST',
        credentials: 'include',
        body: expect.stringContaining('account-asset'),
      }),
    )
  })
})
