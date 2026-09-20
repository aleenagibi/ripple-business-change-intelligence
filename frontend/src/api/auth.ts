const API_BASE_URL = 'http://localhost:8000/api'

export interface AuthUser {
  id: string
  email: string
  role: string
  organization_id: string
}

export interface AuthOrganization {
  id: string
  name: string
  slug: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: AuthUser
  organization: AuthOrganization
}

export interface RegisterRequest {
  organization_name: string
  organization_slug: string
  email: string
  password: string
}

export interface LoginRequest {
  email: string
  password: string
}

async function getErrorMessage(
  response: Response,
  fallback: string,
): Promise<string> {
  const body = await response
    .json()
    .catch(() => null)

  if (typeof body?.detail === 'string') {
    return body.detail
  }

  if (Array.isArray(body?.detail)) {
    return body.detail
      .map(
        (item: {
          msg?: string
        }) => item.msg ?? 'Invalid request.',
      )
      .join(', ')
  }

  return fallback
}

export async function register(
  data: RegisterRequest,
): Promise<AuthResponse> {
  const response = await fetch(
    `${API_BASE_URL}/auth/register`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    },
  )

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        'Registration failed.',
      ),
    )
  }

  return response.json()
}

export async function login(
  data: LoginRequest,
): Promise<AuthResponse> {
  const response = await fetch(
    `${API_BASE_URL}/auth/login`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    },
  )

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        'Login failed.',
      ),
    )
  }

  return response.json()
}

export async function getCurrentUser(
  token: string,
): Promise<AuthUser> {
  const response = await fetch(
    `${API_BASE_URL}/auth/me`,
    {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${token}`,
      },
    },
  )

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        'Authentication failed.',
      ),
    )
  }

  return response.json()
}