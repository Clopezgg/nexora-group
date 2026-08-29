export type RoleName =
  | 'Administrator'
  | 'Finance Manager'
  | 'Treasury Manager'
  | 'Accountant'
  | 'Project Manager'
  | 'Project Controller'
  | 'Procurement Manager'
  | 'Buyer'
  | 'Warehouse Manager'
  | 'Operations User'
  | 'Sales Manager'
  | 'Equipment Manager'
  | 'Auditor'
  | 'Viewer'

export interface CurrentUser {
  id: string
  email: string
  fullName: string
  roles: RoleName[]
  permissions: string[]
}

export interface LoginPayload {
  email: string
  password: string
  rememberMe: boolean
}
