import { createContext } from 'react'
import type { AuthOrganization, AuthUser } from '../api/auth'

export interface AuthContextValue {
  user: AuthUser | null
  organization: AuthOrganization | null
  token: string | null
  loading: boolean
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  register: (
    organizationName: string,
    organizationSlug: string,
    email: string,
    password: string,
  ) => Promise<void>
  logout: () => void
}

export const AuthContext = createContext<AuthContextValue | undefined>(
  undefined,
)