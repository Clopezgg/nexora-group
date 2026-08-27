import { AccountCatalogPage } from './AccountCatalogPage'
import { ReportsPage } from '../reports/ReportsPage'

export function AccountingPage() {
  return <ReportsPage accountCatalog={<AccountCatalogPage />} />
}
