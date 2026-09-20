import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'

import {
  getCurrentUser,
  login as loginRequest,
  register as registerRequest,
  type AuthOrganization,
  type AuthUser,
} from '../api/auth'
import { AUTH_EXPIRED_EVENT } from '../api/client'
import { AuthContext } from './auth-context'

const TOKEN_KEY = 'ripple_access_token'
const ORGANIZATION_KEY = 'ripple_organization'

interface AuthProviderProps {
  children: ReactNode
}

function getStoredOrganization(): AuthOrganization | null {
  const storedOrganization = localStorage.getItem(ORGANIZATION_KEY)

  if (!storedOrganization) {
    return null
  }

  try {
    return JSON.parse(storedOrganization) as AuthOrganization
  } catch {
    localStorage.removeItem(ORGANIZATION_KEY)
    return null
  }
}

export default function AuthProvider({
  children,
}: AuthProviderProps) {
  const [token, setToken] = useState<string | null>(() =>
    localStorage.getItem(TOKEN_KEY),
  )

  const [user, setUser] = useState<AuthUser | null>(null)

  const [organization, setOrganization] =
    useState<AuthOrganization | null>(() =>
      getStoredOrganization(),
    )

  const [loading, setLoading] = useState(true)

  /*
   * Restore an existing session when the application starts.
   */
  useEffect(() => {
    let cancelled = false

    async function restoreSession() {
      const storedToken = localStorage.getItem(TOKEN_KEY)

      if (!storedToken) {
        if (!cancelled) {
          setLoading(false)
        }

        return
      }

      try {
        const currentUser = await getCurrentUser(storedToken)

        if (cancelled) {
          return
        }

        setToken(storedToken)
        setUser(currentUser)
        setOrganization(getStoredOrganization())
      } catch {
        if (cancelled) {
          return
        }

        localStorage.removeItem(TOKEN_KEY)
        localStorage.removeItem(ORGANIZATION_KEY)

        setToken(null)
        setUser(null)
        setOrganization(null)
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    void restoreSession()

    return () => {
      cancelled = true
    }
  }, [])

  /*
   * Handle an expired or invalid JWT returned by the API.
   */
  useEffect(() => {
    function handleAuthExpired() {
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(ORGANIZATION_KEY)

      setToken(null)
      setUser(null)
      setOrganization(null)
    }

    window.addEventListener(
      AUTH_EXPIRED_EVENT,
      handleAuthExpired,
    )

    return () => {
      window.removeEventListener(
        AUTH_EXPIRED_EVENT,
        handleAuthExpired,
      )
    }
  }, [])

  async function login(
    email: string,
    password: string,
  ): Promise<void> {
    const response = await loginRequest({
      email,
      password,
    })

    localStorage.setItem(
      TOKEN_KEY,
      response.access_token,
    )

    localStorage.setItem(
      ORGANIZATION_KEY,
      JSON.stringify(response.organization),
    )

    setToken(response.access_token)
    setUser(response.user)
    setOrganization(response.organization)
  }

  async function register(
    organizationName: string,
    organizationSlug: string,
    email: string,
    password: string,
  ): Promise<void> {
    const response = await registerRequest({
      organization_name: organizationName,
      organization_slug: organizationSlug,
      email,
      password,
    })

    localStorage.setItem(
      TOKEN_KEY,
      response.access_token,
    )

    localStorage.setItem(
      ORGANIZATION_KEY,
      JSON.stringify(response.organization),
    )

    setToken(response.access_token)
    setUser(response.user)
    setOrganization(response.organization)
  }

  function logout() {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(ORGANIZATION_KEY)

    setToken(null)
    setUser(null)
    setOrganization(null)
  }

  const value = {
    user,
    organization,
    token,
    loading,
    isAuthenticated:
      Boolean(token) &&
      Boolean(user) &&
      Boolean(organization),
    login,
    register,
    logout,
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}