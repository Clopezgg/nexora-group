import { CompanySettingsPage } from './CompanySettingsPage'
import { AccessManagementSettings } from './AccessManagementSettings'

export function CompanySettingsWorkspace() {
  return (
    <div className="nx-page">
      <CompanySettingsPage />
      <AccessManagementSettings />
    </div>
  )
}