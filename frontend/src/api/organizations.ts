// const API_BASE_URL = 'http://localhost:8000/api'
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api'
export interface Organization {
  id: string
  name: string
  slug: string
}

export async function getOrganizations(): Promise<Organization[]> {
  const response = await fetch(`${API_BASE_URL}/organizations`)

  if (!response.ok) {
    throw new Error('Failed to load organizations.')
  }

  return response.json()
}

export async function createOrganization(
  name: string,
  slug: string,
): Promise<Organization> {
  const response = await fetch(`${API_BASE_URL}/organizations`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      name,
      slug,
    }),
  })

  if (!response.ok) {
    const body = await response.json().catch(() => null)

    throw new Error(
      body?.detail ?? 'Failed to create organization.',
    )
  }

  return response.json()
}