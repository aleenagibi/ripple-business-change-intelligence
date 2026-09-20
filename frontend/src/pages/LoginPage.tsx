import { useState } from 'react'
import type { FormEvent } from 'react'

const DEMO_EMAIL = 'admin@ripple-demo.com'
const DEMO_PASSWORD = 'RippleTest123!'

interface LoginPageProps {
  onLogin: (
    email: string,
    password: string,
  ) => Promise<void>

  onOpenRegister: () => void

  loading: boolean

  error: string | null
}

function LoginPage({
  onLogin,
  onOpenRegister,
  loading,
  error,
}: LoginPageProps) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault()

    if (!email.trim() || !password) {
      return
    }

    await onLogin(email.trim(), password)
  }

  return (
    <div className="organization-empty auth-page">
      <div className="empty-card auth-card">
        <div className="auth-brand">
          <div className="brand-mark">
            <img
              src="/logo.png"
              alt="Ripple"
            />
          </div>
        </div>

        <div className="auth-heading">
          <span className="auth-eyebrow">
            BUSINESS CHANGE INTELLIGENCE
          </span>

          <h1>Welcome back</h1>

          <p>
            Sign in to your Ripple
            organization workspace.
          </p>
        </div>

        {error && (
          <div className="error-banner auth-error">
            {error}
          </div>
        )}

        <form
          className="auth-form"
          onSubmit={handleSubmit}
        >
          <div className="auth-field">
            <label htmlFor="login-email">
              Work email
            </label>

            <input
              id="login-email"
              type="email"
              placeholder="you@company.com"
              value={email}
              onChange={(event) =>
                setEmail(event.target.value)
              }
              autoComplete="email"
              disabled={loading}
            />
          </div>

          <div className="auth-field">
            <label htmlFor="login-password">
              Password
            </label>

            <input
              id="login-password"
              type="password"
              placeholder="Enter your password"
              value={password}
              onChange={(event) =>
                setPassword(event.target.value)
              }
              autoComplete="current-password"
              disabled={loading}
            />
          </div>

          <button
            type="submit"
            className="primary-button auth-submit"
            disabled={
              loading ||
              !email.trim() ||
              !password
            }
          >
            {loading
              ? 'Signing in...'
              : 'Sign in'}
          </button>
        </form>
<div className="demo-access">
  <div className="demo-access-header">
    <div>
      <span className="demo-access-eyebrow">
        DEMO ACCESS
      </span>

      <strong>
        Try Ripple instantly
      </strong>
    </div>

    <span className="demo-access-badge">
      Demo
    </span>
  </div>

  <div className="demo-credential">
    <div>
      <span>Email</span>
      <strong>{DEMO_EMAIL}</strong>
    </div>

    <button
      type="button"
      onClick={() =>
        navigator.clipboard.writeText(
          DEMO_EMAIL,
        )
      }
    >
      Copy
    </button>
  </div>

  <div className="demo-credential">
    <div>
      <span>Password</span>
      <strong>{DEMO_PASSWORD}</strong>
    </div>

    <button
      type="button"
      onClick={() =>
        navigator.clipboard.writeText(
          DEMO_PASSWORD,
        )
      }
    >
      Copy
    </button>
  </div>

  <button
    type="button"
    className="demo-use-button"
    disabled={loading}
    onClick={() => {
      setEmail(DEMO_EMAIL)
      setPassword(DEMO_PASSWORD)
    }}
  >
    Use demo account
  </button>
</div>
        <div className="auth-switch">
          <span>
            Don't have an account?
          </span>

          <button
            type="button"
            onClick={onOpenRegister}
            disabled={loading}
          >
            Create organization
          </button>
        </div>
      </div>
    </div>
  )
}

export default LoginPage