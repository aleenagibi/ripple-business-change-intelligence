import { useState } from 'react'

import './App.css'

import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import AuthenticatedApp from './components/AuthenticatedApp'

import { useAuth } from './context/useAuth'

type AuthMode =
  | 'login'
  | 'register'

function GitHubBadge() {
  return (
    <a
      className="github-badge"
      href="https://github.com/aleenagibi"
      target="_blank"
      rel="noreferrer"
      aria-label="Visit Aleena Gibi on GitHub"
    >
      <svg
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <path
          fill="currentColor"
          d="M12 .297c-6.63 0-12 5.373-12 12
          0 5.303 3.438 9.8 8.205 11.385
          .6.113.82-.258.82-.577
          0-.285-.01-1.04-.015-2.04
          -3.338.724-4.042-1.61-4.042-1.61
          -.546-1.387-1.333-1.756-1.333-1.756
          -1.089-.745.084-.729.084-.729
          1.205.084 1.84 1.237 1.84 1.237
          1.07 1.835 2.809 1.305 3.495.998
          .108-.776.418-1.305.762-1.605
          -2.665-.3-5.466-1.332-5.466-5.93
          0-1.31.465-2.38 1.235-3.22
          -.135-.303-.54-1.523.105-3.176
          0 0 1.005-.322 3.3 1.23
          .96-.267 1.98-.399 3-.405
          1.02.006 2.04.138 3 .405
          2.28-1.552 3.285-1.23 3.285-1.23
          .645 1.653.24 2.873.12 3.176
          .765.84 1.23 1.91 1.23 3.22
          0 4.61-2.805 5.625-5.475 5.92
          .42.36.81 1.096.81 2.22
          0 1.606-.015 2.896-.015 3.286
          0 .315.21.69.825.57
          C20.565 22.092 24 17.592 24 12.297
          c0-6.624-5.373-12-12-12"
        />
      </svg>

      <span>GitHub · Aleena Gibi</span>
    </a>
  )
}

function App() {
  const {
    user,
    organization,
    loading: authLoading,
    isAuthenticated,
    login,
    register,
    logout,
  } = useAuth()

  const [authMode, setAuthMode] =
    useState<AuthMode>('login')

  const [authSubmitting, setAuthSubmitting] =
    useState(false)

  const [authError, setAuthError] =
    useState<string | null>(null)

  async function handleLogin(
    email: string,
    password: string,
  ) {
    setAuthSubmitting(true)
    setAuthError(null)

    try {
      await login(email, password)
    } catch (err) {
      setAuthError(
        err instanceof Error
          ? err.message
          : 'Unable to sign in.',
      )
    } finally {
      setAuthSubmitting(false)
    }
  }

  async function handleRegister(
    organizationName: string,
    organizationSlug: string,
    email: string,
    password: string,
  ) {
    setAuthSubmitting(true)
    setAuthError(null)

    try {
      await register(
        organizationName,
        organizationSlug,
        email,
        password,
      )
    } catch (err) {
      setAuthError(
        err instanceof Error
          ? err.message
          : 'Unable to create the organization.',
      )
    } finally {
      setAuthSubmitting(false)
    }
  }

  if (authLoading) {
    return (
      <div className="app-loading">
        <div className="loading-mark">
          <img src="/logo.png" alt="Ripple" />
        </div>

        <p>Loading Ripple...</p>
      </div>
    )
  }

  if (
    !isAuthenticated ||
    !user ||
    !organization
  ) {
    if (authMode === 'login') {
      return (
        <>
          <LoginPage
            onLogin={handleLogin}
            onOpenRegister={() => {
              setAuthError(null)
              setAuthMode('register')
            }}
            loading={authSubmitting}
            error={authError}
          />

          <GitHubBadge />
        </>
      )
    }

    return (
      <>
        <RegisterPage
          onRegister={handleRegister}
          onOpenLogin={() => {
            setAuthError(null)
            setAuthMode('login')
          }}
          loading={authSubmitting}
          error={authError}
        />

        <GitHubBadge />
      </>
    )
  }

  return (
    <>
      <AuthenticatedApp
        user={user}
        organization={organization}
        onLogout={logout}
      />

      <GitHubBadge />
    </>
  )
}

export default App