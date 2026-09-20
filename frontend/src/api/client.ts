const API_BASE_URL = 'http://localhost:8000/api'
const TOKEN_KEY = 'ripple_access_token'

export const AUTH_EXPIRED_EVENT = 'ripple-auth-expired'

export class ApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function getErrorMessage(
  response: Response,
  fallback: string,
): Promise<string> {
  const body = await response.json().catch(() => null)

  if (typeof body?.detail === 'string') {
    return body.detail
  }

  if (Array.isArray(body?.detail)) {
    return body.detail
      .map((item: { msg?: string }) => item.msg ?? 'Invalid request.')
      .join(', ')
  }

  return fallback
}

export async function apiFetch(
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  const headers = new Headers(init.headers)
  const token = localStorage.getItem(TOKEN_KEY)

  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
  })

  if (response.status === 401) {
    window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT))
  }

  if (!response.ok) {
    const message = await getErrorMessage(
      response,
      `Request failed with status ${response.status}.`,
    )

    throw new ApiError(message, response.status)
  }

  return response
}