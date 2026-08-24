export type RoleName =
  | 'Administrator'
  | 'Treasury Manager'
  | 'Finance Manager'
  | 'Project Manager'
  | 'Operations User'
  | 'Auditor'
  | 'Viewer'

export interface CurrentUser {
  id: string
  email: string
  fullName: string
  roles: RoleName[]
}

export interface LoginPayload {
  email: string
  password: string
  rememberMe: boolean
}
