import { useState } from 'react'
import type { FormEvent } from 'react'

interface RegisterPageProps {
  onRegister: (
    organizationName: string,
    organizationSlug: string,
    email: string,
    password: string,
  ) => Promise<void>

  onOpenLogin: () => void

  loading: boolean

  error: string | null
}

function RegisterPage({
  onRegister,
  onOpenLogin,
  loading,
  error,
}: RegisterPageProps) {
  const [organizationName, setOrganizationName] =
    useState('')

  const [organizationSlug, setOrganizationSlug] =
    useState('')

  const [email, setEmail] = useState('')

  const [password, setPassword] =
    useState('')

  const [confirmPassword, setConfirmPassword] =
    useState('')

  const [validationError, setValidationError] =
    useState<string | null>(null)

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault()

    setValidationError(null)

    if (
      !organizationName.trim() ||
      !organizationSlug.trim() ||
      !email.trim() ||
      !password ||
      !confirmPassword
    ) {
      setValidationError(
        'Please complete all fields.',
      )

      return
    }

    if (password.length < 8) {
      setValidationError(
        'Password must be at least 8 characters.',
      )

      return
    }

    if (password !== confirmPassword) {
      setValidationError(
        'Passwords do not match.',
      )

      return
    }

    await onRegister(
      organizationName.trim(),
      organizationSlug.trim(),
      email.trim(),
      password,
    )
  }

  function handleSlugChange(
    value: string,
  ) {
    const slug = value
      .toLowerCase()
      .replace(/[^a-z0-9-]/g, '-')
      .replace(/-+/g, '-')

    setOrganizationSlug(slug)
  }

  const displayedError =
    validationError ?? error

  return (
    <div className="organization-empty auth-page">
      <div className="empty-card auth-card auth-card-register">
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
            RIPPLE WORKSPACE
          </span>

          <h1>Create your workspace</h1>

          <p>
            Set up your organization to
            start analyzing business change
            with Ripple.
          </p>
        </div>

        {displayedError && (
          <div className="error-banner auth-error">
            {displayedError}
          </div>
        )}

        <form
          className="auth-form"
          onSubmit={handleSubmit}
        >
          <div className="auth-field">
            <label htmlFor="organization-name">
              Organization name
            </label>

            <input
              id="organization-name"
              type="text"
              placeholder="Acme Corporation"
              value={organizationName}
              onChange={(event) =>
                setOrganizationName(
                  event.target.value,
                )
              }
              disabled={loading}
            />
          </div>

          <div className="auth-field">
            <label htmlFor="organization-slug">
              Organization slug
            </label>

            <input
              id="organization-slug"
              type="text"
              placeholder="acme-corporation"
              value={organizationSlug}
              onChange={(event) =>
                handleSlugChange(
                  event.target.value,
                )
              }
              disabled={loading}
            />

            <span className="auth-help">
              Lowercase letters, numbers and
              hyphens only.
            </span>
          </div>

          <div className="auth-field">
            <label htmlFor="register-email">
              Work email
            </label>

            <input
              id="register-email"
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
            <label htmlFor="register-password">
              Password
            </label>

            <input
              id="register-password"
              type="password"
              placeholder="At least 8 characters"
              value={password}
              onChange={(event) =>
                setPassword(
                  event.target.value,
                )
              }
              autoComplete="new-password"
              disabled={loading}
            />
          </div>

          <div className="auth-field">
            <label htmlFor="confirm-password">
              Confirm password
            </label>

            <input
              id="confirm-password"
              type="password"
              placeholder="Re-enter your password"
              value={confirmPassword}
              onChange={(event) =>
                setConfirmPassword(
                  event.target.value,
                )
              }
              autoComplete="new-password"
              disabled={loading}
            />
          </div>

          <button
            type="submit"
            className="primary-button auth-submit"
            disabled={loading}
          >
            {loading
              ? 'Creating workspace...'
              : 'Create workspace'}
          </button>
        </form>

        <div className="auth-switch">
          <span>
            Already have an account?
          </span>

          <button
            type="button"
            onClick={onOpenLogin}
            disabled={loading}
          >
            Sign in
          </button>
        </div>
      </div>
    </div>
  )
}

export default RegisterPage